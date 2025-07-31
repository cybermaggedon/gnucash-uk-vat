#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GObject, Pango

import gnucash_uk_vat.hmrc as hmrc
from gnucash_uk_vat.auth import Auth
from gnucash_uk_vat.config import Config, initialise_config
import gnucash_uk_vat.accounts as accounts

import asyncio
import threading
import gnucash_uk_vat.model as model
from datetime import timedelta
import io
import gnucash_uk_vat.vat as vat
import time
from pathlib import Path

class EventLoop(threading.Thread):

    def __init__(self, loop=None, name="loop"):

        super().__init__()
        self.running = True
        self.name = name

        if loop:
            self.loop = loop
        else:
            self.loop = asyncio.new_event_loop()

    async def collect(self):
        
        while self.running:

            await asyncio.sleep(0.2)

    def run(self):
        self.loop.run_until_complete(self.collect())

    def stop(self):
        self.running = False

evloop = asyncio.new_event_loop()

# This widget presents an introduction to the dialog process
class Intro:
    def __init__(self, ui):

        widget = Gtk.ScrolledWindow()
        widget.set_hexpand(True)
        widget.set_vexpand(True)
        widget.set_min_content_width(480)
        widget.set_min_content_height(320)

        textview = Gtk.TextView()
        textbuffer = textview.get_buffer()
        textview.set_top_margin(10)
        textview.set_left_margin(10)
        textview.set_right_margin(10)
        textview.set_bottom_margin(10)
        textbuffer.set_text(
            "gnucash-uk-vat\n\n" +
            "This dialogue will guide you through a VAT return submission. " +
            "You will begin by authenticating with the HMRC VAT API using " +
            "your account details. After entering your VAT Registration " +
            "Number (VRN) you will be shown your relevant VAT Obligations. " +
            "You will then be able to select an open obligation (if " +
            "applicable) extract VAT records from GnuCash accounts, " +
            "and submit a VAT return.\n\n" +
            "When you submit this VAT information you are making a legal " +
            "declaration that the information is true and complete. A false " +
            "declaration can result in prosecution."
        )
        textview.set_wrap_mode(Gtk.WrapMode.WORD)
        textview.set_editable(False)
        textview.set_can_focus(False)
        widget.add(textview)

        s = textbuffer.get_iter_at_line(0)
        e = textbuffer.get_iter_at_line(1)

        tag = textbuffer.create_tag("title", foreground="green",
                                    weight=Pango.Weight.BOLD,
                                    size_points=15)
        textbuffer.apply_tag(tag, s, e)

        self.ui = ui
        self.widget = widget

# Widget supports selection of accounts file
class FileSelection:
    def __init__(self, ui):

        self.ui = ui

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)

        lbl = Gtk.Label()
        lbl.set_text("Select the GnuCash file used for accounts")
        lbl.set_halign(Gtk.Align.START)
        box.pack_start(lbl, False, False, 0)

        btn = Gtk.FileChooserButton()
        btn.set_current_folder(".")

        def select(w):
            self.filename = w.get_filename()
            self.check()

        btn.connect("file-set", select)
        box.pack_start(btn, False, False, 0)

        self.label = Gtk.Label()
        box.pack_start(self.label, False, False, 0)

        try:
            acct_file = self.ui.vat.config.get("accounts.file")
            btn.set_filename(acct_file)
            self.filename = acct_file
        except Exception as e:
            self.filename = None
            pass

        label2 = Gtk.Label()
        label2.set_text("GnuCash accounts module to use")
        box.pack_start(label2, False, False, 0)

        def toggled(w, k):
            if w.get_active():
                self.kind = k
                self.check()
                
        rb1 = Gtk.RadioButton.new_from_widget(None)
        self.ui.select_kind("gnucash")
        rb1.set_label("gnucash")
        rb1.connect("toggled", toggled, "gnucash")
        box.pack_start(rb1, False, False, 0)
 
        rb2 = Gtk.RadioButton.new_from_widget(rb1)
        rb2.set_label("piecash")
        rb2.connect("toggled", toggled, "piecash")
        box.pack_start(rb2, False, False, 0)

        try:
            acct_kind = self.ui.vat.config.get("accounts.kind")
            if acct_kind == "gnucash":
                rb1.set_active(True)
            else:
                rb2.set_active(True)
            btn.set_filename(acct_file)
        except Exception as e:
            print(e)
            pass
        
        self.widget = box

    def check(self):
        f = self.filename
        k = self.kind
        self.ui.vat.config.set("accounts.file", f)
        self.ui.vat.config.set("accounts.kind", k)
        self.ui.vat.config.write()
        try:
            self.ui.check_file()
            self.label.set_text("File OK.")
        except Exception as e:
            self.label.set_text(str(e))

# Widget supports selection of the 9 VAT accounts
class AccountsSetup:
    def __init__(self, ui):

        self.ui = ui

        grid = Gtk.Grid()
        grid.set_column_spacing(6)
        grid.set_row_spacing(2)

        lbl = Gtk.Label()
        lbl.set_text("Select the GnuCash accounts used for 9 VAT boxes")
        lbl.set_halign(Gtk.Align.START)
        grid.attach(lbl, 0, 0, 2, 1)

        tps: list[type[object]] = [str]
        tps.extend([bool] * 9)
        self.store = Gtk.ListStore(*tps)

        self.scrollable = Gtk.ScrolledWindow()
        self.scrollable.set_vexpand(True)
        self.scrollable.set_min_content_width(680)

        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.NONE)

        renderer_acct = Gtk.CellRendererText()
        column_acct = Gtk.TreeViewColumn("Account", renderer_acct, text=0)
        self.treeview.append_column(column_acct)

        self.toggle_map = {}

        for i in range(0, 9):
            renderer_box = Gtk.CellRendererToggle()
            renderer_box.connect("toggled", self.changed)
            column_box = Gtk.TreeViewColumn(str(i + 1), renderer_box,
                                            active=(i + 1))
            self.treeview.append_column(column_box)
            self.toggle_map[renderer_box] = i

        self.scrollable.add(self.treeview)
        grid.attach(self.scrollable, 0, 1, 1, 1)

        self.widget = grid

    def changed(self, w, row):

        box = self.toggle_map[w]
        fld = model.vat_fields[box]
        acct = self.store[row][0]

        val = not self.store[row][box+1]
        self.store[row][box+1] = val

        sel = self.ui.vat.config.get("accounts." + fld)
        if isinstance(sel, str):
            sel = set([sel])
        else:
            sel = set(sel)

        if val:
            sel.add(acct)
        else:
            try:
                sel.remove(acct)
            except:
                pass

        self.ui.vat.config.set("accounts." + fld, list(sel))

        self.ui.vat.config.write()
        self.ui.check_accounts()

    def configure(self):

        ac_file = self.ui.vat.config.get("accounts.file")
        ac_kind = self.ui.vat.config.get("accounts.kind")
        cls = accounts.get_class(ac_kind)
        accts = cls(ac_file)

        acct_list = accts.get_accounts()
        del accts

        acct_sel = []
        for i in range(0, 9):
            try:
                fld = model.vat_fields[i]
                sel = self.ui.vat.config.get("accounts." + fld)
                if isinstance(sel, str):
                    acct_sel.append(set([sel]))
                else:
                    acct_sel.append(set(sel))
            except:
                acct_sel.append(set())

        self.store.clear()
        for acct in acct_list:

            row = [acct]

            for i in range(0, 9):
                if acct in acct_sel[i]:
                    row.append(True)
                else:
                    row.append(False)

            self.store.append(row)

# Drives the authentication process, presents a link which launches a
# browser, and then catches the auth token on successful authentication.
class Authentication:
    def __init__(self, ui):

        widget = Gtk.ScrolledWindow()
        widget.set_hexpand(True)
        widget.set_vexpand(True)
        widget.set_min_content_width(480)
        widget.set_min_content_height(320)

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)

        self.label = Gtk.Label()
        self.label.set_text(
            "Follow the link below to authenticate with the VAT service. " +
            "This will open a browser window.  Once you are authenticated, " +
            "return to this application to continue."
        )
        self.label.set_max_width_chars(30)
        self.label.set_line_wrap(True)
        box.add(self.label)

        self.button = Gtk.LinkButton.new_with_label("", "Authenticate")
        box.add(self.button)

        self.status = Gtk.Label()
        box.add(self.status)

        widget.add(box)

        self.ui = ui
        self.widget = widget

    def configure(self, url):
        self.button.set_uri(url)

    def got_auth(self):
        self.status.set_text("Got authentication token.")

# Dialogue which allows for VRN entry
class VrnEntry:
    def __init__(self, ui):

        self.ui = ui

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)

        label = Gtk.Label()
        label.set_text(
            "Enter your VRN"
        )
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.set_halign(Gtk.Align.START)
        box.pack_start(self.entry, False, False, 0)

        def pressed(x):
            self.check()

        test = Gtk.Button.new_with_label("Check")
        test.set_halign(Gtk.Align.START)
        box.pack_start(test, False, False, 0)

        self.status = Gtk.Label()
        self.status.set_halign(Gtk.Align.START)
        box.pack_start(self.status, False, False, 0)

        try:
            vrn = self.ui.vat.config.get("identity.vrn")
            self.entry.set_text(vrn)
        except Exception as e:
            pass

        test.connect("pressed", pressed)

        self.widget = box

    def check(self):
        vrn = self.entry.get_text()
        try:
            self.ui.select_vrn(vrn)
            self.status.set_text("VRN is valid.")
        except Exception as e:
            print(e)
            self.status.set_text("VRN " + vrn + " is not valid.")

# Widget supports selection of VAT obligation period
class SelectObligation:
    def __init__(self, ui):
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)
        self.ui = ui
        self.widget = box

    def configure(self, obls):

        for child in self.widget.get_children():
            self.widget.remove(child)

        if len(obls) == 0:
            label = Gtk.Label()
            label.set_text("You have no open obligations.")
            self.ui.select_obligation(None)
            self.widget.pack_start(label, False, False, 0)
            self.widget.show_all()
            return

        label = Gtk.Label()
        label.set_text("Please select a VAT obligation period")
        self.widget.pack_start(label, False, False, 0)

        grp = None

        def toggled(w, ob):
            if w.get_active():
                self.ui.select_obligation(ob)

        for v in obls:
            rb = Gtk.RadioButton.new_from_widget(grp)
            if grp == None:
                grp = rb
                self.ui.select_obligation(v)
            rb.set_label("%s -  %s (due %s)" % (
                v.start, v.end, v.due
            ))
            rb.connect("toggled", toggled, v)
            self.widget.pack_start(rb, False, False, 0)

        self.widget.show_all()

# Widget supports the VAT return submission step
class VatReturnSubmission:
    def __init__(self, ui):

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)

        self.textview = Gtk.TextView()
        textbuffer = self.textview.get_buffer()
        self.textview.set_top_margin(10)
        self.textview.set_left_margin(10)
        self.textview.set_right_margin(10)
        self.textview.set_bottom_margin(10)
        self.textview.set_editable(False)
        self.textview.set_can_focus(False)
        box.pack_start(self.textview, False, False, 0)

        label = Gtk.Label()
        label.set_text(
            "When you submit this VAT information you are making a legal " +
            "declaration that the information is true and complete. A false " +
            "declaration can result in prosecution."
        )
        label.set_max_width_chars(30)
        label.set_line_wrap(True)
        box.pack_start(label, False, False, 0)

        def submitted(x):
            try:
                self.ui.submit_return()
                self.button.set_sensitive(False)
                self.label.set_text("Submission successful.")
            except Exception as e:
                self.label.set_text(str(e))

        self.button = Gtk.Button.new_with_label("Submit VAT return")
        box.pack_start(self.button, False, False, 0)

        self.label = Gtk.Label()
        box.pack_start(self.label, False, False, 0)

        self.button.connect("pressed", submitted)

        self.mono_tag = textbuffer.create_tag("monospace", font="Monospace",
                                              size_points=10)
        self.red_tag = textbuffer.create_tag("monospace_red", font="Monospace",
                                             foreground="red", size_points=10)

        self.ui = ui
        self.widget = box

    def show(self, rtn):

        # FIXME: State is dependendent on holding an open obligation?
        self.button.set_sensitive(True)

        report = rtn.to_string()

        textbuffer = self.textview.get_buffer()
        textbuffer.set_text(report)

        s = textbuffer.get_start_iter()
        e = textbuffer.get_end_iter()

        textbuffer.apply_tag(self.mono_tag, s, e)

        s = textbuffer.get_iter_at_line(4)
        e = textbuffer.get_iter_at_line(5)

        textbuffer.apply_tag(self.red_tag, s, e)

# Widget supports the submission of VAT bill
# FIXME: This doesn't work with piecash, so I'm taking it out.
class BillPosting:
    def __init__(self, ui):

        self.ui = ui
        print("SET ui to", self.ui)

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)

        self.textview = Gtk.TextView()
        textbuffer = self.textview.get_buffer()
        self.textview.set_top_margin(10)
        self.textview.set_left_margin(10)
        self.textview.set_right_margin(10)
        self.textview.set_bottom_margin(10)
        self.textview.set_editable(False)
        self.textview.set_can_focus(False)
        box.pack_start(self.textview, False, False, 0)

        self.mono_tag = textbuffer.create_tag("monospace", font="Monospace",
                                              size_points=10)
        self.red_tag = textbuffer.create_tag("monospace_red", font="Monospace",
                                             foreground="red", size_points=10)

        label = Gtk.Label()
        label.set_text("Press button to create a VAT bill")
        box.pack_start(label, False, False, 0)

        def submitted(x):
            try:
                print("GET")
                print("GET ui to", self.ui)
                self.ui.post_bill()
                self.button.set_sensitive(False)
                self.label.set_text("Bill post successful.")
            except Exception as e:
                self.label.set_text(str(e))

        self.button = Gtk.Button.new_with_label("Post VAT bill")
        box.pack_start(self.button, False, False, 0)
        self.button.connect("pressed", submitted)

        self.label = Gtk.Label()
        box.pack_start(self.label, False, False, 0)

        self.widget = box

    def configure(self, rtn):

        # FIXME: State is dependendent on holding an open obligation?
        self.button.set_sensitive(True)

        report = rtn.to_string()

        textbuffer = self.textview.get_buffer()
        textbuffer.set_text(report)

        s = textbuffer.get_start_iter()
        e = textbuffer.get_end_iter()

        textbuffer.apply_tag(self.mono_tag, s, e)

        s = textbuffer.get_iter_at_line(4)
        e = textbuffer.get_iter_at_line(5)

        textbuffer.apply_tag(self.red_tag, s, e)

# Widget supports final step, display of a summary
class Summary:
    def __init__(self, ui):

        self.ui = ui

        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 10)

        self.textview = Gtk.TextView()
        textbuffer = self.textview.get_buffer()
        self.textview.set_top_margin(10)
        self.textview.set_left_margin(10)
        self.textview.set_right_margin(10)
        self.textview.set_bottom_margin(10)
        self.textview.set_editable(False)
        self.textview.set_can_focus(False)
        box.pack_start(self.textview, False, False, 0)

        self.mono_tag = textbuffer.create_tag("monospace", font="Monospace",
                                              size_points=10)

        self.widget = box

    def show(self, summary):

        textbuffer = self.textview.get_buffer()
        textbuffer.set_text(summary)

        s = textbuffer.get_start_iter()
        e = textbuffer.get_end_iter()

        textbuffer.apply_tag(self.mono_tag, s, e)

# Overarching UI class, runs the assist dialogue
class UI:
    def __init__(self, config: Path, auth):
        try:
            self.cfg = Config(config)
        except:
            initialise_config(config, None)
            self.cfg = Config(config)
        self.authz = Auth(auth)

        self.vat = hmrc.create(self.cfg, self.authz, None)
        self.summary = io.StringIO()

    def select_vrn(self, vrn):

        self.summary.write("Selected VRN: %s\n\n" % vrn)

        self.vat.config.set("identity.vrn", vrn)
        self.vat.config.write()

        try:

            task = asyncio.run_coroutine_threadsafe(
                self.vat.get_open_obligations(vrn),
                loop=evloop
            )

            obs = task.result(timeout=10)

            self.assistant.set_page_complete(self.vrn.widget, True)

        except Exception as e:
            print(e)
            self.assistant.set_page_complete(self.vrn.widget,
                                             False)
            raise e
            
    def submit_return(self):
        vrn = self.vat.config.get("identity.vrn")

        task = asyncio.run_coroutine_threadsafe(
            self.vat.submit_vat_return(vrn, self.vat_return),
            loop=evloop
        )

        resp = task.result(timeout=10)

        self.assistant.set_page_complete(self.vat_return_w.widget, True)

        self.summary.write("Submitted return for period %s - %s:\n%s\n" % (
            self.selected_obligation.start,
            self.selected_obligation.end,
            self.vat_return.to_string()
        ))

    def post_bill(self):

        # Open GnuCash accounts, and get VAT records for the period
        ac_file = self.vat.config.get("accounts.file")
        ac_kind = self.vat.config.get("accounts.kind")
        cls = accounts.get_class(ac_kind)
        accts = cls(ac_file)

        # FIXME: How to work out due date?  Online says 1 cal month plus 7 days
        # from end of accounting period
        end = self.selected_obligation.end
        due = self.selected_obligation.due
        accts.post_bill(
            str(due),
            end,
            end + timedelta(days=28) + timedelta(days=7),
            self.vat_return,
            self.vat_return.to_string(indent=False),
            "VAT payment for due date " + str(due)
        )

        # self.assistant.set_page_complete(self.post_bill_w.widget, True)

        self.summary.write("Posted bill for period, due %s\n\n" % str(due))
        
    def got_auth(self):
        self.vat.auth.write()
        self.auth.got_auth()
        self.assistant.set_page_complete(self.auth.widget, True)

    def select_obligation(self, ob):
        self.selected_obligation = ob
        if ob != None:
            self.assistant.set_page_complete(self.obligations.widget, True)
        else:
            self.assistant.set_page_complete(self.obligations.widget, False)

    def select_kind(self, k):
        self.selected_accounts_kind = k

    def configure_obligations(self):
        try:
            vrn = self.vat.config.get("identity.vrn")

            task = asyncio.run_coroutine_threadsafe(
                self.vat.get_open_obligations(vrn),
                loop=evloop
            )

            obls = task.result(timeout=10)

            self.obligations.configure(obls)

            if len(obls) == 0:
                self.assistant.set_page_complete(self.obligations.widget, False)
            else:
                self.assistant.set_page_complete(self.obligations.widget, True)

        except Exception as e:
            print(e)
            self.assistant.set_page_complete(self.obligations.widget, False)

    def configure_vat_return(self):
        s = self.selected_obligation.start
        e = self.selected_obligation.end

        ac_file = self.vat.config.get("accounts.file")
        ac_kind = self.vat.config.get("accounts.kind")
        cls = accounts.get_class(ac_kind)
        acc = cls(ac_file)
        vals = vat.get_vat(acc, self.vat.config, s, e)

        # Build base of the VAT return
        rtn = model.Return()
        rtn.periodKey = self.selected_obligation.periodKey
        rtn.finalised = True

        # Add VAT values
        for k in range(0, 9):
            valueName = model.vat_fields[k]
            setattr(rtn, valueName, vals[valueName]["total"])

        self.vat_return = rtn

        self.vat_return_w.show(rtn)

    def check_file(self):

        try:
            ac_file = self.vat.config.get("accounts.file")
            ac_kind = self.vat.config.get("accounts.kind")
            cls = accounts.get_class(ac_kind)
            accts = cls(ac_file)
            self.assistant.set_page_complete(self.file_sel.widget, True)
        except Exception as e:
            self.assistant.set_page_complete(self.file_sel.widget, False)
            raise e

    def check_accounts(self):

        # No checking done
        try:
            self.assistant.set_page_complete(self.acc_setup.widget, True)
        except Exception as e:
            self.assistant.set_page_complete(self.acc_setup.widget, False)
        
    def create_assistant(self):

        self.assistant = Gtk.Assistant()

        intro = Intro(self)
        self.assistant.append_page(intro.widget)
        self.assistant.set_page_type(intro.widget, Gtk.AssistantPageType.INTRO)
        self.assistant.set_page_title(intro.widget, "Introduction")
        self.assistant.set_page_complete(intro.widget, True)

        self.file_sel = FileSelection(self)
        self.assistant.append_page(self.file_sel.widget)
        self.assistant.set_page_type(self.file_sel.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.file_sel.widget, "GnuCash file")

        self.acc_setup = AccountsSetup(self)
        self.assistant.append_page(self.acc_setup.widget)
        self.assistant.set_page_type(self.acc_setup.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.acc_setup.widget, "GnuCash accounts")

        self.auth = Authentication(self)
        self.assistant.append_page(self.auth.widget)
        self.assistant.set_page_type(self.auth.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.auth.widget, "Authentication")

        self.vrn = VrnEntry(self)
        self.assistant.append_page(self.vrn.widget)
        self.assistant.set_page_type(self.vrn.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.vrn.widget, "VRN")

        self.obligations = SelectObligation(self)
        self.assistant.append_page(self.obligations.widget)
        self.assistant.set_page_type(self.obligations.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.obligations.widget, "Obligations")

        self.vat_return_w = VatReturnSubmission(self)
        self.assistant.append_page(self.vat_return_w.widget)
        self.assistant.set_page_type(self.vat_return_w.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.vat_return_w.widget, "VAT return")

#        self.post_bill_w = BillPosting(self)
#        self.assistant.append_page(self.post_bill_w.widget)
#        self.assistant.set_page_type(self.post_bill_w.widget,
#                                     Gtk.AssistantPageType.CONTENT)
#        self.assistant.set_page_title(self.post_bill_w.widget, "Post VAT bill")

        self.summary_w = Summary(self)
        self.assistant.append_page(self.summary_w.widget)
        self.assistant.set_page_type(self.summary_w.widget,
                                     Gtk.AssistantPageType.SUMMARY)
        self.assistant.set_page_title(self.summary_w.widget, "Summary")

        self.assistant.connect("destroy", Gtk.main_quit)
        self.assistant.connect("cancel", Gtk.main_quit)
        self.assistant.connect("close", Gtk.main_quit)

        def prepare(ass, page):

            if page == self.auth.widget:

                try:
                    vrn = self.vat.config.get("identity.vrn")

                    task = asyncio.run_coroutine_threadsafe(
                        self.vat.get_open_obligations(vrn),
                        loop=evloop
                    )

                    obs = task.result(timeout=10)

                    # Auth worked.  No need to auth
                    self.auth.label.set_text(
                        "You are already authenticated. " +
                        "You do not need to re-authenticate."
                    )
                    self.assistant.set_page_complete(self.auth.widget, True)

                except Exception as e:
                    print(e)
                    pass

                url = self.vat.get_auth_url()
                self.auth.configure(url)

            if page == self.obligations.widget:
                self.configure_obligations()

            if page == self.file_sel.widget:
                self.check_file()

            if page == self.vrn.widget:
                self.vrn.check()
                
            if page == self.acc_setup.widget:
                self.acc_setup.configure()

                # Maybe enables next button.
                self.check_accounts()

            if page == self.vat_return_w.widget:
                self.configure_vat_return()

#            if page == self.post_bill_w.widget:
#                self.post_bill_w.configure(self.vat_return)

            if page == self.summary_w.widget:
                self.summary_w.show(self.summary.getvalue())

        self.assistant.connect("prepare", prepare)

        self.assistant.show_all()

# Class, provides an embedded web server to catch OAUTH2 token acquisition
class Collector(threading.Thread):

    def __init__(self, ui, port=9876):
        super().__init__()
        self.ui = ui
        self.daemon = True
        self.coll = hmrc.AuthCollector("localhost", port)
        self.running = True

    async def collect(self):
        
        await self.coll.start()
        while True:

            if not self.running: return

            if self.coll.result != None:
                break

            await asyncio.sleep(0.2)

            # asd

        await self.ui.vat.get_auth(self.coll.result["code"])

        GLib.idle_add(self.ui.got_auth)
        await self.coll.stop()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.collect())

    def stop(self):
        self.running = False

# Entry point, runs the assist
def run(config: str, auth):
    ui = UI(Path(config), auth)
    coll = Collector(ui)
    coll.start()

    el = EventLoop(loop=evloop)
    el.start()

    ui.create_assistant()

    Gtk.main()
    coll.stop()
    el.stop()

