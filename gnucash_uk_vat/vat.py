from . import model

# Return VAT return for the defined period.  Makes use of the
# configuration object to describe which accounts to analyse.
def get_vat(accounts, config, start, end):

    vat = {}

    # Boxes 1 to 9, are referred to as 0 to 8 in this loop.
    for v in range(0, 9):

        valueName = model.vat_fields[v]

        locator = config.get("accounts").get(valueName)

        if isinstance(locator, str):
            acct = accounts.get_account(None, locator)
            all_splits = accounts.get_splits(acct, start, end)
            if accounts.is_debit(acct):
                for spl in all_splits:
                    spl["amount"] *= -1
        elif isinstance(locator, list):
            all_splits = []
            for elt in locator:
                acct = accounts.get_account(None, elt)
                splits = accounts.get_splits(acct, start, end)
                if accounts.is_debit(acct):
                    for spl in splits:
                        spl["amount"] *= -1
                all_splits.extend(splits)
        else:
            raise RuntimeError("Accounts should be strings or lists")

        vat[valueName] = {
            "splits": all_splits,
            "total": sum([v["amount"] for v in all_splits])
        }

        # These boxes accept pence.  Numbers do need to be 2
        # decimal places, though.
        if v in [0, 1, 2, 3, 4]:
            vat[valueName]["total"] = round(vat[valueName]["total"], 2)

        # Some boxes are pounds only, round off the pence.
        if v in [5, 6, 7, 8]:
            vat[valueName]["total"] = round(vat[valueName]["total"])

        # VAT value is always positive, boxes 3 and 4 are studied to
        # determine refund vs payment
        if v == 4:
            vat[valueName]["total"] = abs(vat[valueName]["total"])

    return vat

# Post the VAT bill to a liability account.
def post_vat_bill(accounts, config, billing_id, bill_date, due_date, vat,
                  notes, memo):

    # Get the VAT vendor (HMRC)
    vendor = get_vat_vendor(accounts)

    bill = accounts.create_bill(None, vendor,
                                bill_date, notes)

    vat_due = vat.totalVatDue
    vat_rebate = vat.vatReclaimedCurrPeriod

    liability_account_name = config.get("accounts.liabilities")
    liability_acct = accounts.get_account(accounts.root, liability_account_name)

    bill_account_name = config.get("accounts.bills")
    bill_acct = accounts.get_account(accounts.root, bill_account_name)

    description = "VAT from sales and acquisitions"
    ent = accounts.create_bill_entry(bill, bill_date, description,
                                     liability_acct, 1.0, vat_due)

    description = "VAT rebate on acquisitions"
    ent = accounts.create_bill_entry(bill, bill_date, description,
                                     liability_acct, 1.0, -vat_rebate)

    accounts.post_bill(bill, bill_acct, bill_date, due_date, memo)

    accounts.save()


# Get our 'special' predefined vendor for VAT returns.
def get_vat_vendor(accounts):

    id = "hmrc-vat"

    # If vendor does not exist, create it
    vendor = accounts.get_vendor(id)
    if vendor == None:

        gbp = accounts.get_currency("GBP")
        name = "HM Revenue and Customs - VAT"
        vendor = accounts.create_vendor(id, gbp, name)

        accounts.set_address(
            vendor,
            "VAT Written Enquiries",
            "123 St Vincent Street",
            "Glasgow City",
            "Glasgow G2 5EA",
            "UK"
        )

        accounts.save()

    return vendor
