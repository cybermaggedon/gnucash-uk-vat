#!/usr/bin/env python3

# This calls the Fraud API test endpoint on sandbox.  Only useful for developers.
import argparse
import asyncio
import json
import sys
from pathlib import Path

import gnucash_uk_vat.hmrc as hmrc
from gnucash_uk_vat.config import Config
from gnucash_uk_vat.auth import Auth

parser = argparse.ArgumentParser(description="Gnucash to HMRC VAT API")
parser.add_argument('--config', '-c',
                    default=Path('config.json'), type=Path,
                    help='Configuration file (default: ./config.json)')
args = parser.parse_args()

# Use the sandbox service
svc = hmrc.VatTest(Config(args.config), Auth(), None)

# Call fraud API and dump out results.
# This is expected to fail on lack of gov-client-multi-factor headers.
resp = asyncio.run(svc.test_fraud_headers())
print(json.dumps(resp, indent=4))
