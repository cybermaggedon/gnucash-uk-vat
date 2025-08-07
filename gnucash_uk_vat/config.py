
import json
import uuid
import getpass
import socket
import sys
import netifaces

import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Union

from . device import get_device
from . version import version as product_version

def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)
    
# Configuration object, loads configuration from a JSON file, and then
# supports path navigate with config.get("part1.part2.part3")
class Config:
    def __init__(self, file: Path = Path("config.json"), config: Optional[Dict[str, Any]] = None) -> None:
        self.file = file.expanduser()
        if config:
            # Used to populate default values when creating new config
            self.config = config
        else:
            self.config = json.loads(self.file.read_text())
    def get(self, key: str) -> Any:
        cfg: Any = self.config
        for v in key.split("."):
            if isinstance(cfg, dict) and v in cfg.keys():
                cfg = cfg[v]
            else:
                cfg = None
                break
        return cfg
    def set(self, key: str, value: Any, applyNone: bool = True) -> None:
        # Should 'set' ignore value==None
        if value or ( not value and applyNone ):
            cfg = self.config
            keys = key.split(".")
            for v in keys[:-1]:
                cfg = cfg[v]
            cfg[keys[-1]] = value
    # Write back to file
    def write(self, fileOverride: Optional[Path] = None) -> None:
        file_path = fileOverride if fileOverride else self.file
        file_path.write_text(json.dumps(self.config, indent=4))

def get_default_gateway_if() -> Any:
    gateways = netifaces.gateways()
    default_gateway_if = gateways['default'][netifaces.AF_INET][1]
    ifaddresses = netifaces.ifaddresses(default_gateway_if)
    return ifaddresses

def get_gateway_ip() -> Any:
    default_gateway_if = get_default_gateway_if()
    ip_addr = default_gateway_if[netifaces.AF_INET][0]['addr']
    return ip_addr

def get_gateway_mac() -> Any:
    default_gateway_if = get_default_gateway_if()
    mac_addr = default_gateway_if[netifaces.AF_LINK][0]['addr']
    return mac_addr



# Initialise/update configuration file.
# Order of precedence:
#    1. private user config, if exists
#    2. current config, if exists
#    3. static config defaults from this function
# Also, collate personal information for the Fraud API.
def initialise_config(config_path: Path, user: Optional['Config']) -> None:

    # Strip away the path if present
    config_filename = config_path.name
    config_private_filename = Path.home() / f".{config_filename}"
    config_private = None
    config_current = None

    try:
        mac = get_gateway_mac()
    except:
        # Fallback.
        mac = '00:00:00:00:00:00'

    local_ip = get_gateway_ip()
    di = get_device_config()

#    vatDueSales = "VAT:Output:Sales" 
#    vatDueAcquisitions = "VAT:Output:EU"
#    totalVatDue = "VAT:Output"
#    vatReclaimedCurrPeriod = "VAT:Input"
#    netVatDue = "VAT"
#    totalValueSalesExVAT = "Income:Sales"
#    totalValuePurchasesExVAT = "Expenses:VAT Purchases"
#    totalValueGoodsSuppliedExVAT = "Income:Sales:EU:Goods"
#    totalAcquisitionsExVAT = "Expenses:VAT Purchases:EU Reverse VAT"
#    liabilities = "VAT:Liabilities"
#    bills = "Accounts Payable"
#    product_name = "gnucash-uk-vat"
#    client_id = "<CLIENT ID>"
#    client_secret = "<CLIENT_SECRET>"
    terms_and_conditions_url = None
#    vrn = "<VRN>"

    configDefaults = {
        "accounts": {
            "kind": "piecash",
            "file": "<ACCOUNTS_FILE>",
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
            "profile": "<APPLICATION_PROFILE>",
            "product-name": "gnucash-uk-vat",
            "product-version": "gnucash-uk-vat-%s" % product_version,
            "client-id": "<CLIENT ID>",
            "client-secret": "<CLIENT_SECRET>"
        },
        "identity": {
            "vrn": "<VRN>",
            "device": di,
            "user": getpass.getuser(),
            "local-ip": local_ip,
            "mac-address": mac,
            # https://developer.service.hmrc.gov.uk/guides/fraud-prevention/connection-method/other-direct/#gov-client-local-ips-timestamp
            "time": now().strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        }
    }


    creating_config_private_filename = ( Path.home() == config_path.parent and config_filename.startswith('.') and not config_path.exists() )
    if creating_config_private_filename:
        # Create new config_private_filename from configDefaults
        print("Creating private config from defaults", end="\n")
        config_private = Config(config_private_filename, configDefaults)

        # Populate the private user config with default
        config_private.set("application.terms-and-conditions-url", "http://example.com/terms_and_conditions/")
        config_private.write()

        return

    else:
        # load existing config_private_filename
        if config_private_filename.exists():
            config_private = Config(config_private_filename)
        else:
            print("Private config file is not present: %s" % config_private_filename, end="\n")


    # LOAD CURRENT CONFIG
    if config_path.exists():
        usingDefaults = False
        config_current = Config(config_path)
    else:
        print("Create missing config file using defaults: %s" % config_path, end="\n")
        usingDefaults = True
        config_current = Config(config_path, configDefaults)

    if config_private:
        # config_private_filename has been loaded
        if config_private.get("accounts"):
            # Don't override 'accounts.file' from config_private_filename. Must be defined in the config template.
            
            config_current.set("accounts.vatDueSales", config_private.get("accounts.vatDueSales"), applyNone=False)
            config_current.set("accounts.vatDueAcquisitions", config_private.get("accounts.vatDueAcquisitions"), applyNone=False)
            config_current.set("accounts.totalVatDue", config_private.get("accounts.totalVatDue"), applyNone=False)
            config_current.set("accounts.vatReclaimedCurrPeriod", config_private.get("accounts.vatReclaimedCurrPeriod"), applyNone=False)
            config_current.set("accounts.netVatDue", config_private.get("accounts.netVatDue"), applyNone=False)
            config_current.set("accounts.totalValueSalesExVAT", config_private.get("accounts.totalValueSalesExVAT"), applyNone=False)
            config_current.set("accounts.totalValuePurchasesExVAT", config_private.get("accounts.totalValuePurchasesExVAT"), applyNone=False)
            config_current.set("accounts.totalValueGoodsSuppliedExVAT", config_private.get("accounts.totalValueGoodsSuppliedExVAT"), applyNone=False)
            config_current.set("accounts.totalAcquisitionsExVAT", config_private.get("accounts.totalAcquisitionsExVAT"), applyNone=False)
            config_current.set("accounts.liabilities", config_private.get("accounts.liabilities"), applyNone=False)
            config_current.set("accounts.bills", config_private.get("accounts.bills"), applyNone=False)
        if config_private.get("application"):
            # Don't override 'application.profile' from config_private_filename. Must be defined in the config template.
            
            config_current.set("application.product-name", config_private.get("application.product-name"), applyNone=False)
            config_current.set("application.product-version", product_version, applyNone=False)
            config_current.set("application.client-id", config_private.get("application.client-id"), applyNone=False)
            config_current.set("application.client-secret", config_private.get("application.client-secret"), applyNone=False)
            config_current.set("application.terms-and-conditions-url", config_private.get("application.terms-and-conditions-url"), applyNone=False)
        if config_private.get("identity") and config_current.get("application") and config_current.get("application.profile") == "prod":
            config_current.set("identity.vrn", config_private.get("identity.vrn"), applyNone=False)

    # ONLY FOR TEST ENVIRONMENTS
    if config_current.get("application") and config_current.get("application.profile") != "prod" and user:
        # Use the test-user VRN
        config_current.set("identity.vrn", user.get("vrn"), applyNone=False)

    if usingDefaults:
        config_current.write()
        print("    Wrote '%s'" % config_path, end="\n")
        print("    The newly created config file may require some changes to suit your specific environment!", end="\n")
    else:
        config_current.write(config_path)
        print("    Wrote '%s'" % config_path, end="\n")
    

def get_device_config() -> Dict[str, str]:

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

