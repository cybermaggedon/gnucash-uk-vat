#!/usr/bin/env python3

import gnucash
import json
import math
from decimal import Decimal
import hmrc

class Accounts:

    def __init__(self, config):
        self.config = config
        self.session = self.open_session(config.get("accounts.file"))
        self.book = self.session.book
        self.root = self.book.get_root_account()

    @staticmethod
    def open_session(file):
        mode = gnucash.SessionOpenMode.SESSION_READ_ONLY
        session = gnucash.Session(file, mode)
        return session

    def get_splits(self, acct, start, end):

        splits = []

        childs = acct.get_children()
        if childs != None:
            for v in acct.get_children():
                splits.extend(self.get_splits(v, start, end))

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

    def get_account(self, par, locator):
        acct = par
        for v in locator.split(":"):
            acct = acct.lookup_by_name(v)
            if acct == None:
                raise RuntimeError("Can't locate account '%s'" % locator)
        return acct

    def get_vat(self, start, end):

        vat = {}

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

            # Some boxes are pounds only, no pence.
            if v in [5, 6, 7, 8]:
                vat[valueName]["total"] = round(vat[valueName]["total"])

        return vat

