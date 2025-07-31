
import sys
import json

from tabulate import tabulate
from datetime import timedelta

from . import accounts
from . import model
from . import vat

# Perform authentication operation
async def authenticate(h, auth):

    code = await h.get_code()

    sys.stderr.write("Got one-time code.\n")
    await h.get_auth(code)
    sys.stderr.write("Got authentication key.\n")
    auth.write()
    sys.stderr.write("Wrote %s.\n" % auth.file)

# Show obligations with the O state
async def show_open_obligations(h, config, print_json):

    obs = await h.get_open_obligations(config.get("identity.vrn"))

    if len(obs) == 0:
        print("No obligations matched.")
        return

    if print_json:
        json_tbl = [
            { 
               "start": v.start.strftime("%Y-%m-%d") if v.start else "", 
               "end": v.end.strftime("%Y-%m-%d") if v.end else "", 
               "due": v.due.strftime("%Y-%m-%d") if v.due else "", 
               "status": v.status if v.status else "" 
            }
            for v in obs
        ]
        print(json.dumps(json_tbl, indent=4))
    else:
        list_tbl = [
            [v.start, v.end, v.due, v.status]
            for v in obs
        ]

        print(tabulate(list_tbl,
                   ["Start", "End", "Due", "Status"],
                   tablefmt="pretty"))

# Show obligations in a time period
async def show_obligations(start, end, h, config, print_json):

    obs = await h.get_obligations(config.get("identity.vrn"), start, end)

    if len(obs) == 0:
        print("No obligations matched.")
        return

    if print_json:
        json_tbl = [
            { 
               "start": v.start.strftime("%Y-%m-%d") if v.start else "", 
               "end": v.end.strftime("%Y-%m-%d") if v.end else "", 
               "due": v.due.strftime("%Y-%m-%d") if v.due else "", 
               "received": v.received.strftime("%Y-%m-%d") if v.received else "", 
               "status": v.status if v.status else "" 
            }
            for v in obs
        ]
        print(json.dumps(json_tbl, indent=4))
    else:
        list_tbl = [
            [v.start, v.end, v.due, v.received, v.status]
            for v in obs
        ]

        print(tabulate(list_tbl,
                   ["Start", "End", "Due", "Received", "Status"],
                   tablefmt="pretty"))

# Submit a VAT return
async def submit_vat_return(due, h, config):

    # We need start/end information, but only have a due date.
    # Load the obligations to get the mapping
    obs = await h.get_open_obligations(config.get("identity.vrn"))

    # Iterate over obligations to find the period
    obl = None
    for v in obs:
        if v.due == due:
            obl = v

    # Not found
    if obl == None:
        raise RuntimeError("Due date '%s' does not match any obligations" % due)

    # Get start/end date
    start = obl.start
    end = obl.end

    # Open GnuCash accounts, and get VAT records for the period
    cls = accounts.get_class(config.get("accounts.kind"))
    accts = cls(config.get("accounts.file"))
    vals = vat.get_vat(accts, config, start, end)

    # Build base of the VAT return
    rtn = model.Return()
    rtn.periodKey = obl.periodKey
    rtn.finalised = True

    # Add VAT values
    for k in range(0, 9):
        valueName = model.vat_fields[k]
        setattr(rtn, valueName, vals[valueName]["total"])

    # Dump output.  Too late to fix anything anyway.
    # FIXME: Are you sure? etc.
    sys.stdout.write(rtn.to_string())

    while True:
        print("""
When you submit this VAT information you are making a legal
declaration that the information is true and complete. A false
declaration can result in prosecution.
""")
        reply = input("OK to submit? (yes/no) ")
        if reply == "no":
            raise RuntimeError("Submission was not accepted.")
        if reply == "yes":
            break
        print("Answer not recognised.")

    # Call the API
    resp = await h.submit_vat_return(config.get("identity.vrn"), rtn)

    # Dump out the response
    print()
    print("Submitted.")
    if "processingDate" in resp:
        print("%-30s: %s" % ("Processing date", resp["processingDate"]))
    if "paymentIndicator" in resp:
        print("%-30s: %s" % ("Payment indicator", resp["paymentIndicator"]))
    if "formBundleNumber" in resp:
        print("%-30s: %s" % ("Form bundle", resp["formBundleNumber"]))
    if "chargeRefNumber" in resp:
        print("%-30s: %s" % ("Charge ref", resp["chargeRefNumber"]))

# Submit a VAT return
async def post_vat_bill(start, end, due, h, config):

    # We need start/end information, but only have a period key first.
    # Load the obligations to get the mapping
    obs = await h.get_obligations(config.get("identity.vrn"), start, end)

    # Iterate over obligations to find the period
    obl = None
    for v in obs:
        if v.due == due:
            obl = v

    # Not found
    if obl == None:
        raise RuntimeError("Due date '%s' does not match any obligation" % due)

    # Get start/end date
    start = obl.start
    end = obl.end

    # Open GnuCash accounts, and get VAT records for the period
    cls = accounts.get_class(config.get("accounts.kind"))
    accts = cls(config.get("accounts.file"))
    vals = vat.get_vat(accts, config, start, end)

    # Build base of the VAT return
    rtn = model.Return()
    rtn.periodKey = obl.periodKey
    rtn.finalised = True

    # Add VAT values
    for k in range(0, 9):
        valueName = model.vat_fields[k]
        setattr(rtn, valueName, vals[valueName]["total"])

    # Dump output.
    sys.stdout.write(rtn.to_string())

    # FIXME: How to work out due date?  Online says 1 cal month plus 7 days
    # from end of accounting period
    vat.post_vat_bill(
        accts, config,
        str(due),
        end,
        end + timedelta(days=28) + timedelta(days=7),
        rtn,
        rtn.to_string(indent=False),
        "VAT payment for due date " + str(due)
    )

    print("Bill posted.")

# Show GnuCash information relating to open VAT obligations
async def show_account_data(h, config, due, detail=False):

    # Get open obligations
    obs = await h.get_open_obligations(config.get("identity.vrn"))

    # Iterate over obligations to find the period
    obl = None
    for v in obs:
        if v.due == due:
            obl = v

    # Not found
    if obl == None:
        raise RuntimeError("Due date '%s' does not match any obligations" % due)

    print("Found Obligation that is due on '%s'" % due)
    # Get accounts
    cls = accounts.get_class(config.get("accounts.kind"))
    accts = cls(config.get("accounts.file"))

    # Write out obligation header
    print()
    print("Search for account data in '%s' from '%-10s' to '%-10s'" % (
        config.get("accounts.file"), obl.start, obl.end
    ))
    print()

    # Get VAT values for this period from accounts
    vals = vat.get_vat(accts, config, obl.start, obl.end)

    # Loop over 9 boxes (0 .. 8 in this loop)
    for k in range(0, 9):

        # Get the name of the VAT value
        valueName = model.vat_fields[k]

        valueDesc = model.vat_descriptions.get(valueName, valueName)

        # Output the value
        print("    %s: %.2f" % (valueDesc, vals[valueName]["total"]))

        # In detail mode, transactions are shown, otherwise skip that part
        if not detail: continue

        print()

        # Dump out all contributing transactions
        if len(vals[valueName]["splits"]) > 0:

            # Construct a transaction table
            tbl = []

            # Add transactions to table
            for w in vals[valueName]["splits"]:
                tbl.append([
                    w["date"], "%.2f" % w["amount"], w["description"][0:60]
                ])

            # Create table
            output = tabulate(tbl, tablefmt="pretty",
                              colalign=("left", "right","left"))

            # Indent table by 8 characters
            output = "        " + output.replace("\n", "\n        ")
            print(output)

            print()

# Dump out a VAT return
async def show_vat_return(start, end, due, h, config):

    # We need start/end information, but only have a period key first.
    # Load the obligations to get the mapping
    obs = await h.get_obligations(config.get("identity.vrn"), start, end)

    # Iterate over obligations to find the period
    obl = None
    for v in obs:
        if v.due == due:
            obl = v

    if obl == None:
        raise RuntimeError("Due date '%s' does not match any obligation" % due)

    # Fetch VAT return data
    rtn = await h.get_vat_return(config.get("identity.vrn"), obl.periodKey)
    sys.stdout.write(rtn.to_string())

# Show liabilities
async def show_liabilities(start, end, h, config):

    # Fetch values from liabilities endpoint
    rtn = await h.get_vat_liabilities(config.get("identity.vrn"), start, end)

    # Initialise empty table
    tbl = []

    # Iterate over liabilities, build table
    for v in rtn:
        ent = []
        ent.append(v.end)
        ent.append(v.typ[0:20])
        ent.append(v.original)
        ent.append(v.outstanding)
        ent.append(v.due)
        tbl.append(ent)

    # Dump out table
    print(tabulate(tbl, ["Period End", "Type", "Amount", "Outstanding", "Due"],
                   tablefmt="pretty"))

async def show_payments(start, end, h, config):

    # Fetch values from payments endpoint
    rtn = await h.get_vat_payments(config.get("identity.vrn"), start, end)

    # Initialise empty table
    tbl = []

    # Iterate over payments, build table
    for v in rtn:
        ent = []
        ent.append(v.amount)
        ent.append(v.received)
        tbl.append(ent)

    # Dump out table
    print(tabulate(tbl, ["Amount", "Received"],
                   tablefmt="pretty"))

