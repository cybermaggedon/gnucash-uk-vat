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

        widget.add(box)

        self.ui = ui
        self.widget = widget

    def configure(self, url):
        self.button.set_uri(url)

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
            print(e)
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
            self.check(w)

        btn.connect("file-set", select)
        box.pack_start(btn, False, False, 0)

        self.label = Gtk.Label()
        box.pack_start(self.label, False, False, 0)

        try:
            acct_file = self.ui.vat.config.get("accounts.file")
            btn.set_filename(acct_file)
        except Exception as e:
            print(e)
            pass

        self.widget = box

    def check(self, w):
        f = w.get_filename()
        self.ui.vat.config.set("accounts.file", f)
        self.ui.vat.config.write()
        try:
            self.ui.check_file()
            self.label.set_text("File OK.")
        except Exception as e:
            self.label.set_text(str(e))
        

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

        self.store = Gtk.ListStore(str)

        self.accts = [
            Gtk.ComboBox.new_with_model(self.store)
            for v in range(0, 11)
        ]

        self.handlers = []

        for i in range(0, 9):

            fld = model.vat_fields[i]
            desc = model.vat_descriptions[fld]
            
            lbl = Gtk.Label()
            lbl.set_text(desc + ":")
            lbl.set_halign(Gtk.Align.END)
            grid.attach(lbl, 0, i + 1, 1, 1)

#            self.handlers.append(self.accts[i].connect("changed", changed))
            cell = Gtk.CellRendererText()
            self.accts[i].pack_start(cell, False)
            self.accts[i].add_attribute(cell, 'text', 0)
            grid.attach_next_to(self.accts[i], lbl, Gtk.PositionType.RIGHT,
                                1, 1)

        self.widget = grid

    def changed(self, w):

        for i in range(0, 9):
            fld = model.vat_fields[i]

            iter = self.accts[i].get_active_iter()
            if iter is not None:
                val = self.store[iter][0]
            else:
                val = ""

            self.ui.vat.config.set("accounts." + fld, val)
        self.ui.vat.config.write()
        self.ui.check_accounts()

    def configure(self):

        if len(self.handlers) > 0:
            for i in range(0, 9):
                self.accts[i].disconnect(self.handlers[i])
            self.handlers = []

        ac_file = self.ui.vat.config.get("accounts.file")
        accts = accounts.Accounts(self.ui.vat.config)

        acct_list = accts.get_accounts()
        del accts

        acct_sel = []
        for i in range(0, 9):
            try:
                fld = model.vat_fields[i]
                sel = self.ui.vat.config.get("accounts." + fld)
                acct_sel.append(sel)
            except:
                acct_sel.append("")

        self.store.clear()
        pos = 0
        for acct in acct_list:
            self.store.append([acct])
            for i in range(0, 9):
                if acct == acct_sel[i]:
                    self.accts[i].set_active(pos)
            pos += 1

        for i in range(0, 9):
            self.handlers.append(self.accts[i].connect("changed", self.changed))

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

class BillPosting:
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
        self.red_tag = textbuffer.create_tag("monospace_red", font="Monospace",
                                             foreground="red", size_points=10)

        label = Gtk.Label()
        label.set_text("Press button to create a VAT bill")
        box.pack_start(label, False, False, 0)

        def submitted(x):
            try:
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
        
class UI:
    def __init__(self):
        try:
            self.cfg = Config()
        except:
            initialise_config("config.json")
            self.cfg = Config()
        self.authz = Auth()

        self.vat = hmrc.create(self.cfg, self.authz)
        self.summary = io.StringIO()

    def select_vrn(self, vrn):

        self.summary.write("Selected VRN: %s\n\n" % vrn)

        self.vat.config.set("identity.vrn", vrn)
        self.vat.config.write()

        try:
            obs = self.vat.get_open_obligations(vrn)
            self.assistant.set_page_complete(self.vrn.widget, True)
        except Exception as e:
            self.assistant.set_page_complete(self.vrn.widget,
                                             False)
            raise e
            
    def submit_return(self):
        vrn = self.vat.config.get("identity.vrn")
        resp = self.vat.submit_vat_return(vrn, self.vat_return)
        self.assistant.set_page_complete(self.vat_return_w.widget, True)

        self.summary.write("Submitted return for period %s - %s:\n%s\n" % (
            self.selected_obligation.start,
            self.selected_obligation.end,
            self.vat_return.to_string()
        ))

    def post_bill(self):

        # Open GnuCash accounts, and get VAT records for the period
        accts = accounts.Accounts(self.vat.config)

        # FIXME: How to work out due date?  Online says 1 cal month plus 7 days
        # from end of accounting period
        end = self.selected_obligation.end
        due = self.selected_obligation.due
        accts.post_vat_bill(
            str(due),
            end,
            end + timedelta(days=28) + timedelta(days=7),
            self.vat_return,
            self.vat_return.to_string(indent=False),
            "VAT payment for due date " + str(due)
        )

        self.assistant.set_page_complete(self.post_bill_w.widget, True)

        self.summary.write("Posted bill for period, due %s\n\n" % str(due))
        
    def collect_auth(self, code):
        self.vat.get_auth(code)
        self.vat.auth.write()
        self.assistant.set_page_complete(self.auth.widget, True)
#        self.assistant.set_current_page(2)

    def select_obligation(self, ob):
        self.selected_obligation = ob
        if ob != None:
            self.assistant.set_page_complete(self.obligations.widget, True)
        else:
            self.assistant.set_page_complete(self.obligations.widget, False)

    def configure_obligations(self):
        try:
            vrn = self.vat.config.get("identity.vrn")
            obls = self.vat.get_open_obligations(vrn)
            self.obligations.configure(obls)
            self.assistant.set_page_complete(self.obligations.widget, True)
        except Exception as e:
            self.assistant.set_page_complete(self.obligations.widget, False)

    def configure_vat_return(self):
        s = self.selected_obligation.start
        e = self.selected_obligation.end

        acc = accounts.Accounts(self.vat.config)
        vals = acc.get_vat(s, e)

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
            accts =  accounts.Accounts(self.vat.config)
            self.assistant.set_page_complete(self.file_sel.widget, True)

        except Exception as e:
            self.assistant.set_page_complete(self.file_sel.widget, False)
            raise e

    def check_accounts(self):

        try:
            ac_file = self.vat.config.get("accounts.file")

            accts = accounts.Accounts(self.vat.config)

            acct_list = set(accts.get_accounts())

            conf = [
                self.vat.config.get("accounts.vatDueSales"),
                self.vat.config.get("accounts.vatDueAcquisitions"),
                self.vat.config.get("accounts.totalVatDue"),
                self.vat.config.get("accounts.vatReclaimedCurrPeriod"),
                self.vat.config.get("accounts.netVatDue"),
                self.vat.config.get("accounts.totalValueSalesExVAT"),
                self.vat.config.get("accounts.totalValuePurchasesExVAT"),
                self.vat.config.get("accounts.totalValueGoodsSuppliedExVAT"),
                self.vat.config.get("accounts.totalAcquisitionsExVAT"),
                self.vat.config.get("accounts.liabilities"),
                self.vat.config.get("accounts.bills"),
            ]

            for c in conf:
                if c not in acct_list:
                    raise RuntimeError("Account %s not valid" % c)

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

        self.post_bill_w = BillPosting(self)
        self.assistant.append_page(self.post_bill_w.widget)
        self.assistant.set_page_type(self.post_bill_w.widget,
                                     Gtk.AssistantPageType.CONTENT)
        self.assistant.set_page_title(self.post_bill_w.widget, "Post VAT bill")

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
                    obs = self.vat.get_open_obligations(vrn)
                    # Auth worked.  No need to auth
                    self.auth.label.set_text(
                        "You are already authenticated. " +
                        "You do not need to re-authenticate."
                    )
                    self.assistant.set_page_complete(self.auth.widget, True)
                except:
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

            if page == self.post_bill_w.widget:
                self.post_bill_w.configure(self.vat_return)

            if page == self.summary_w.widget:
                self.summary_w.show(self.summary.getvalue())

        self.assistant.connect("prepare", prepare)

        self.assistant.show_all()

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

        GLib.idle_add(self.ui.collect_auth, self.coll.result["code"])
        await self.coll.stop()

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.collect())

    def stop(self):
        self.running = False

def run():
    ui = UI()
    coll = Collector(ui)
    coll.start()

    ui.create_assistant()

    Gtk.main()
    coll.stop()

