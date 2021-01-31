#!/usr/bin/env python3

#
# Wrapper for GnuCash Python API, extracts account structure, splits, and
# also VAT return information from the accounts.
#
# Usage:
#     s = Accounts("file.gnucash")
#     rtn = s.get_vat()
#     print(rtn["totalVatDue"]["total"])
#     for v in rtn["totalVatDue"]["splits"]:
#         print(v["date"], v["amount"])

import gnucash
import json
import math

from . import model

# Wrapper for GnuCash accounts.
class Accounts:

    # Opens a GnuCash book.  Config object provides configuration, needs
    # to support config.get("key.name") method.
    def __init__(self, config, rw=False):
        self.config = config
        self.session = None
        file = config.get("accounts.file")
        if rw:
            self.session = self.open_session(file)
        else:
            self.session = self.open_session_rw(file)
        self.book = self.session.book
        self.root = self.book.get_root_account()

    def __del__(self):
        if self.session != None:
            self.session.destroy()

    def save(self):
        self.session.save()

    # Creates a read-only session associated with a GnuCash file
    @staticmethod
    def open_session(file):
        mode = gnucash.SessionOpenMode.SESSION_READ_ONLY
        session = gnucash.Session(file, mode)
        return session

    @staticmethod
    def open_session_rw(file):
        mode = gnucash.SessionOpenMode.SESSION_NORMAL_OPEN
        session = gnucash.Session(file, mode)
        return session

    # Given a root account and start/end points return all matching splits
    # recorded against that account and any child accounts.
    def get_splits(self, acct, start, end):

        splits = []

        # Recurse into children
        childs = acct.get_children()
        if childs != None:
            for v in acct.get_children():
                splits.extend(self.get_splits(v, start, end))

        # Iterate over split list
        for spl in acct.GetSplitList():
            tx = spl.parent
            dt = tx.GetDate().date()

            if dt >= start and dt < end:
                splits.append(
                    {
                        "date": dt,
                        "amount": spl.GetAmount().to_double(),
                        "description": tx.GetDescription()
                    }
                )

        return splits

    # Return an account given an account locator.  Navigates through
    # hierarchy, account parts are colon separated.
    def get_account(self, par, locator):
        acct = par
        for v in locator.split(":"):
            acct = acct.lookup_by_name(v)
            if acct == None:
                raise RuntimeError("Can't locate account '%s'" % locator)
        return acct

    def get_accounts(self, acct=None, pfx=""):

        if acct == None: acct = self.root

        ch = acct.get_children()
        if ch == None:
            return []
        
        res = []

        for v in acct.get_children():
            res.append(pfx + v.name)
            res.extend(
                self.get_accounts(v, pfx + v.name + ":")
            )
        return res

    # Return VAT return for the defined period.  Makes use of the
    # configuration object to describe which accounts to analyse.
    def get_vat(self, start, end):

        vat = {}

        # Boxes 1 to 9, are referred to as 0 to 8 in this loop.
        for v in range(0, 9):

            valueName = model.vat_fields[v]

            locator = self.config.get("accounts").get(valueName)
            acct = self.get_account(self.root, locator)

            splits = self.get_splits(acct, start, end)

            vat[valueName] = {
                "splits": splits,
                "total": sum([v["amount"] for v in splits])
            }

            # Some boxes need sign reversal, I think this is mapping whether
            # the account is asset or liability type.
            # FIXME: Should be user-configurable?
            # FIXME: Should be able to work this out from account type?
            if v in [0, 1, 2, 4, 5, 7]:
                vat[valueName]["total"] *= -1
                for w in vat[valueName]["splits"]:
                    w["amount"] *= -1

            # Some boxes are pounds only, round off the pence.
            if v in [5, 6, 7, 8]:
                vat[valueName]["total"] = round(vat[valueName]["total"])

        return vat

    # Get vendor by vendor ID, returns Vendor object
    def get_vendor(self, id):
        return self.book.VendorLookupByID(id)

    # Get list of all vendors, list of Vendor objects
    def get_vendors(self):

        query = gnucash.Query()
        query.search_for('gncVendor')
        query.set_book(self.book)
        vendors = []

        vnds = [
            gnucash.gnucash_business.Vendor(instance=result)
            for result in query.run()
        ]

        query.destroy()

        return vnds

    # Create a vendor
    def create_vendor(self, id, currency, name):
        return gnucash.gnucash_business.Vendor(self.book, id, currency, name)

    # Get a currency given the mnemonic.  Returns a Commodity object.
    def get_currency(self, mn):
        return self.book.get_table().lookup("CURRENCY", mn)

    # Get next bill ID given vendor
    def next_bill_id(self, vendor):
        return self.book.BillNextID(vendor)

    # Createa a bill
    def create_bill(self, id, currency, vendor, date_opened):
        return gnucash.gnucash_business.Bill(self.book, id, currency, vendor,
                                             date_opened)

    # Add a bill entry to a bill
    def create_bill_entry(self, bill, date_opened):
        entry = gnucash.gnucash_business.Entry(self.book, bill, date_opened)
        return entry

    # Get our 'special' predefined vendor for VAT returns.
    def get_vat_vendor(self):

        id = "hmrc-vat"

        # If vendor does not exist, create it
        vendor = self.get_vendor(id)
        if vendor == None:

            gbp = self.get_currency("GBP")
            name = "HM Revenue and Customs - VAT"
            vendor = self.create_vendor(id, gbp, name)

            address = vendor.GetAddr()
            address.SetName("VAT Written Enquiries")
            address.SetAddr1("123 St Vincent Street")
            address.SetAddr2("Glasgow City")
            address.SetAddr3("Glasgow G2 5EA")
            address.SetAddr4("UK")

            self.save()

        return vendor

    # Post the VAT bill to a liability account.
    def post_vat_bill(self, billing_id, bill_date, due_date, vat, notes, memo):

        # Get the VAT vendor (HMRC)
        vendor = self.get_vat_vendor()

        bill_id  = self.next_bill_id(vendor)
        bill = self.create_bill(bill_id, vendor.GetCurrency(), vendor,
                                bill_date)

        vat_due = vat.totalVatDue
        vat_rebate = vat.vatReclaimedCurrPeriod
        bill.SetNotes(notes)
        bill.SetBillingID(billing_id)

        liability_account_name = self.config.get("accounts.liabilities")
        liability_acct = self.get_account(self.root, liability_account_name)

        bill_account_name = self.config.get("accounts.bills")
        bill_acct = self.get_account(self.root, bill_account_name)

        description = "VAT from sales and acquisitions"
        ent = self.create_bill_entry(bill, bill_date)
        ent.SetDescription(description)
        ent.SetBillAccount(liability_acct)
        ent.SetQuantity(gnucash.GncNumeric(1.0))
        ent.SetBillPrice(gnucash.GncNumeric(round(100 * vat_due), 100))

        description = "VAT rebate on acquisitions"
        ent = self.create_bill_entry(bill, bill_date)
        ent.SetDescription(description)
        ent.SetBillAccount(liability_acct)
        ent.SetQuantity(gnucash.GncNumeric(1.0))
        ent.SetBillPrice(gnucash.GncNumeric(-round(100 * vat_rebate), 100))

        bill.PostToAccount(bill_acct, bill_date, due_date, memo, False, False)

        self.save()

