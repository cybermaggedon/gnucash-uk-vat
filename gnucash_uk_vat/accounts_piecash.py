
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

#import gnucash
import piecash
import json
import math

# Wrapper for GnuCash accounts.
class Accounts:

    # Opens a GnuCash book.  Config object provides configuration, needs
    # to support config.get("key.name") method.
    def __init__(self, file, rw=False):
        self.book = piecash.open_book(file, readonly=not rw)

    def __del__(self):
        pass

    def save(self):
        pass
        # self.session.save()

    # Given a root account and start/end points return all matching splits
    # recorded against that account and any child accounts.
    def get_splits(self, acct, start, end, endinclusive=True):

        splits = []

        # Recurse into children
        childs = acct.children
        if childs != []:
            for v in childs:
                splits.extend(self.get_splits(v, start, end))

        # Iterate over split list
        for spl in acct.splits:
            tx = spl.transaction
            dt = tx.post_date

            inperiod = False

            if endinclusive and dt >= start and dt <= end:
                inperiod = True

            if (not endinclusive) and dt >= start and dt < end:
                inperiod = True

            if inperiod:
                splits.append(
                    {
                        "date": dt,
                        "amount": float(spl.value),
                        "description": tx.description
                    }
                )

        return splits

    # Return an account given an account locator.  Navigates through
    # hierarchy, account parts are colon separated.
    def get_account(self, par, locator):

        if par == None: par = self.book.root_account

        acct = par

        for v in locator.split(":"):
            acct = acct.children(name=v)
            if acct == None:
                raise RuntimeError("Can't locate account '%s'" % locator)
        return acct

    def get_accounts(self, acct=None, pfx=""):

        if acct == None: acct = self.book.root_account

        ch = acct.children
        if ch == None:
            return []
        
        res = []

        for v in acct.children:
            res.append(pfx + v.name)
            res.extend(
                self.get_accounts(v, pfx + v.name + ":")
            )
        return res

    def is_debit(self, acct):
        if acct.type == "INCOME": return True
        if acct.type == "EQUITY": return True
        if acct.type == "LIABILITY": return True
        return False

    # Get vendor by vendor ID, returns Vendor object
    def get_vendor(self, id):
        try:
            return self.book.get(piecash.Vendor, id=id)
        except:
            return None

    # Get list of all vendors, list of Vendor objects
    def get_vendors(self):

        query = piecash.Query()
        query.search_for('gncVendor')
        query.set_book(self.book)
        vendors = []

        vnds = [
            piecash.gnucash_business.Vendor(instance=result)
            for result in query.run()
        ]

        query.destroy()

        return vnds

    def set_address(self, vendor, name, addr1, addr2, addr3, addr4):
        vendor.address = piecash.Address(
            name=name,
            addr1=addr1,
            addr2=addr2,
            addr3=addr3,
            addr4=addr4
        )

    # Create a vendor
    def create_vendor(self, id, currency, name):
        print("WARTS")
        return piecash.Vendor(
            id=id,
            name=name,
            currency=currency,
        )

    # Get a currency given the mnemonic.  Returns a Commodity object.
    def get_currency(self, mn):
#        return self.book.get_table().lookup("CURRENCY", mn)
        return self.book.get(piecash.Commodity, mnemonic=mn)

    # Get next bill ID given vendor
    def next_bill_id(self, vendor):
        print(1/0)
        return self.book.BillNextID(vendor)

    # Createa a bill
    def create_bill(self, id, vendor, date_opened, notes):
        raise RuntimeError("Not implemented for the piecash backend.")

    # Add a bill entry to a bill
    def create_bill_entry(self, bill, date_opened):
        raise RuntimeError("Not implemented for the piecash backend.")
