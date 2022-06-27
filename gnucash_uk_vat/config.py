
import json
import uuid
import os
import getpass
import socket
import sys
from datetime import datetime

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
def initialise_config(config_file):

    # This gets hold of the MAC address, which the uuid module knows.
    # FIXME: Hacky.
    try:
        mac = uuid.getnode()
        mac = [
            '{:02x}'.format((mac >> ele) & 0xff)
            for ele in range(0,8*6,8)
        ][::-1]
        mac = ':'.join(mac)
    except:
        # Fallback.
        mac = '00:00:00:00:00:00'

    di = get_device_config()

    config = {
        "accounts": {
            "kind": "piecash",
	    "file": "accounts/accounts.gnucash",
            "vatDueSales": "VAT:Output:Sales",
            "vatDueAcquisitions": "VAT:Output:EU",
            "totalVatDue": "VAT:Output",
            "vatReclaimedCurrPeriod": "VAT:Input",
            "netVatDue": "VAT",
            "totalValueSalesExVAT": "Income:Sales",
            "totalValuePurchasesExVAT": "Expenses:VAT Purchases",
            "totalValueGoodsSuppliedExVAT": "Income:Sales:EU:Goods",
            "totalAcquisitionsExVAT": "Expenses:VAT Purchases:EU Reverse VAT",
            "liabilities": "VAT:Liabilities",
            "bills": "Accounts Payable"
        },
        "application": {
            "profile": "prod",
            "client-id": "<CLIENT ID>",
            "client-secret": "<SECRET>"
        },
        "identity": {
            "vrn": "<VRN>",
            "device": di,
            "user": getpass.getuser(),
            "local-ip": socket.gethostbyname(socket.gethostname()),
            "mac-address": mac,
            "time": datetime.utcnow().isoformat()[:-3] + "Z"
        }
    }

    with open(config_file, "w") as cfg_file:
        cfg_file.write(json.dumps(config, indent=4))

    sys.stderr.write("Wrote %s.\n" % config_file)

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

