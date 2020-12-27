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
import hmrc

# Wrapper for GnuCash accounts.
class Accounts:

    # Opens a GnuCash book.  Config object provides configuration, needs
    # to support config.get("key.name") method.
    def __init__(self, config, rw=False):
        self.config = config
        file = config.get("accounts.file")
        if rw:
            self.session = self.open_session(file)
        else:
            self.session = self.open_session_rw(file)
        self.book = self.session.book
        self.root = self.book.get_root_account()

    def __del__(self):
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

    # Return VAT return for the defined period.  Makes use of the
    # configuration object to describe which accounts to analyse.
    def get_vat(self, start, end):

        vat = {}

        # Boxes 1 to 9, are referred to as 0 to 8 in this loop.
        for v in range(0, 9):

            valueName = hmrc.vat_box[v]

            locator = self.config.get("accounts").get(valueName)
            acct = self.get_account(self.root, locator)

            splits = self.get_splits(acct, start, end)

            vat[valueName] = {
                "splits": splits,
                "total": sum([v["amount"] for v in splits])
            }

            # Some boxes need sign reversal, I think this is mapping whether
            # the account is credit or debit type.
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

    def get_vendor(self, id):
        return self.book.VendorLookupByID(id)

    def get_vendors(self):

        query = gnc.Query()
        query.search_for('gncVendor')
        query.set_book(self.book)
        vendors = []

        vnds = [
            biz.Vendor(instance=result)
            for result in query.run()
        ]

        query.destroy()

        return vnds

    def create_vendor(self, id, currency, name):
        return gnucash.gnucash_business.Vendor(self.book, id, currency, name)

    def get_currency(self, mn):

        return self.book.get_table().lookup("CURRENCY", mn)

    def next_bill_id(self,  vendor):
        return self.book.BillNextID(vendor)

    def create_bill(self, id, currency, vendor, date_opened):
        return gnucash.gnucash_business.Bill(self.book, id, currency, vendor,
                                             date_opened)

    def create_bill_entry(self, bill, date_opened):
        entry = gnucash.gnucash_business.Entry(self.book, bill, date_opened)
        return entry

