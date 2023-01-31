
import json
import uuid
import os
import getpass
import socket
import sys
from datetime import datetime
from pathlib import Path

from . device import get_device

# Configuration object, loads configuration from a JSON file, and then
# supports path navigate with config.get("part1.part2.part3")
class Config:
    def __init__(self, file="config.json"):
        self.file = file
        self.config = json.loads(open(file).read())
    def get(self, key):
        cfg = self.config
        for v in key.split("."):
            cfg = cfg[v]
        return cfg
    def set(self, key, value):
        cfg = self.config
        keys = key.split(".")
        for v in keys[:-1]:
            cfg = cfg[v]
        cfg[keys[-1]] = value
    # Write back to file
    def write(self):
        with open(self.file, "w") as config_file:
            config_file.write(json.dumps(self.config, indent=4))

# Initialise configuration file with some (mainly) static values.  Also,
# collate personal information for the Fraud API.
def initialise_config(config_file, profile_name, gnucashFile, user):

    # User static config is stored in the HOME directory mashes gnucash_filename and the profile_name
    gnucash_filename = Path(gnucashFile).name
    gnucash_userfile = os.path.join(os.environ.get('HOME'),".%s.%s.json" % (gnucash_filename,profile_name))

    gnucash_user = None
    if  os.path.exists(gnucash_userfile):
      gnucash_user = Config(gnucash_userfile)
    else:
      print("Test userfile is missing so VRN cannot be set at the moment", end="\n")

    # This gets hold of the MAC address, which the uuid module knows.
    # FIXME: Hacky.
    try:
        mac = uuid.getnode()
        print("raw-mac-address: %s" % mac)
        mac = [
            '{:02x}'.format((mac >> ele) & 0xff)
            for ele in range(0,8*6,8)
        ][::-1]
        mac = ':'.join(mac)
        print("mac-address: %s" % mac)
    except:
        # Fallback.
        mac = '00:00:00:00:00:00'

    di = get_device_config()

    vatDueSales = "VAT:Output:Sales" 
    vatDueAcquisitions = "VAT:Output:EU"
    totalVatDue = "VAT:Output"
    vatReclaimedCurrPeriod = "VAT:Input"
    netVatDue = "VAT"
    totalValueSalesExVAT = "Income:Sales"
    totalValuePurchasesExVAT = "Expenses:VAT Purchases"
    totalValueGoodsSuppliedExVAT = "Income:Sales:EU:Goods"
    totalAcquisitionsExVAT = "Expenses:VAT Purchases:EU Reverse VAT"
    liabilities = "VAT:Liabilities"
    bills = "Accounts Payable"
    product_name = "gnucash-uk-vat"
    client_id = "<CLIENT ID>"
    client_secret = "<SECRET>"
    terms_and_conditions_url = "http://example.com/terms_and_conditions/"
    vrn = "<VRN>"

    # If default file exists and it's not initialising the gnucash_user 
    if gnucash_user:
        # use the defaults to create the new config file
        vatDueSales = gnucash_user.get("accounts.vatDueSales") if gnucash_user.get("accounts.vatDueSales") else vatDueSales 
        vatDueAcquisitions = gnucash_user.get("accounts.vatDueAcquisitions") if gnucash_user.get("accounts.vatDueAcquisitions") else vatDueAcquisitions
        totalVatDue = gnucash_user.get("accounts.totalVatDue") if gnucash_user.get("accounts.totalVatDue") else totalVatDue
        vatReclaimedCurrPeriod = gnucash_user.get("accounts.vatReclaimedCurrPeriod") if gnucash_user.get("accounts.vatReclaimedCurrPeriod") else vatReclaimedCurrPeriod
        netVatDue = gnucash_user.get("accounts.netVatDue") if gnucash_user.get("accounts.netVatDue") else netVatDue
        totalValueSalesExVAT = gnucash_user.get("accounts.totalValueSalesExVAT") if gnucash_user.get("accounts.totalValueSalesExVAT") else totalValueSalesExVAT
        totalValuePurchasesExVAT = gnucash_user.get("accounts.totalValuePurchasesExVAT") if gnucash_user.get("accounts.totalValuePurchasesExVAT") else totalValuePurchasesExVAT
        totalValueGoodsSuppliedExVAT = gnucash_user.get("accounts.totalValueGoodsSuppliedExVAT") if gnucash_user.get("accounts.totalValueGoodsSuppliedExVAT") else totalValueGoodsSuppliedExVAT
        totalAcquisitionsExVAT = gnucash_user.get("accounts.totalAcquisitionsExVAT") if gnucash_user.get("accounts.totalAcquisitionsExVAT") else totalAcquisitionsExVAT
        liabilities = gnucash_user.get("accounts.liabilities") if gnucash_user.get("accounts.liabilities") else liabilities
        bills = gnucash_user.get("accounts.bills") if gnucash_user.get("accounts.bills") else bills
        client_id = gnucash_user.get("application.client-id") if gnucash_user.get("application.client-id") else client_id
        client_secret = gnucash_user.get("application.client-secret") if gnucash_user.get("application.client-secret") else client_secret
        terms_and_conditions_url = gnucash_user.get("application.terms-and-conditions-url") if gnucash_user.get("application.terms-and-conditions-url") else terms_and_conditions_url

    if user:
        vrn = user.get("vrn") if user.get("vrn") else vrn

    config = {
        "accounts": {
            "kind": "piecash",
            "file": gnucashFile,
            "vatDueSales": vatDueSales,
            "vatDueAcquisitions": vatDueAcquisitions,
            "totalVatDue": totalVatDue,
            "vatReclaimedCurrPeriod": vatReclaimedCurrPeriod,
            "netVatDue": netVatDue,
            "totalValueSalesExVAT": totalValueSalesExVAT,
            "totalValuePurchasesExVAT": totalValuePurchasesExVAT,
            "totalValueGoodsSuppliedExVAT": totalValueGoodsSuppliedExVAT,
            "totalAcquisitionsExVAT": totalAcquisitionsExVAT,
            "liabilities": liabilities,
            "bills": bills
        },
        "application": {
            "profile": profile_name,
            "product-name": product_name,
            "client-id": client_id,
            "client-secret": client_secret,
            "terms-and-conditions-url": terms_and_conditions_url
        },
        "identity": {
            "vrn": vrn,
            "device": di,
            "user": getpass.getuser(),
            "local-ip": socket.gethostbyname(socket.gethostname()),
            "mac-address": mac,
            "time": datetime.utcnow().isoformat()[:-3] + "Z"
        }
    }

    # Special case when initialising the users static config in the HOME dir
    if Path(gnucash_userfile).name == Path(config_file).name:
        del config["identity"]

    with open(config_file, "w") as cfg_file:
        cfg_file.write(json.dumps(config, indent=4))

    print("Wrote %s.\n" % config_file, end="\n")

def get_device_config():

    dmi = get_device()
    if dmi == None:
        err = "Couldn't fetch device information, install dmidecode?"
        raise RuntimeError(err)

    import platform
    uname = platform.uname()

    return {
        'os-family': uname.system,
	'os-version': uname.release,
        'device-manufacturer': dmi["manufacturer"],
        'device-model': dmi["model"],
        'id': str(uuid.uuid1()),
    }

