
# `gnucash-uk-vat`

## Introduction

This is a utility which manages HMRC (UK) VAT returns in accordance with
HMRC MTD directives for users of the GnuCash accounting system.  It can
study your GnuCash accounts, compare this with your HMRC VAT obligations,
and produce the VAT return to meet your obligations.  As an optional step,
once the VAT return is filed, a bill can be created describing the VAT
owing, and posted to an Accounts Payable account.

## Status

This is a command-line utility.  At the time of writing, this code is
immature - it has been tested against the Sandbox APIs.  You may be the
first person to submit a production VAT return. :)  Email me,
mark AT cyberapocalypse DOT co DOT uk, and I'll support you through the
process.

It has only been tested with Linux. In theory, it should work with GnuCash
Python modules on any platform, but Python modules aren't included with Windows
or MacOS builds.

If you're an HMRC VAT user, and you use GnuCash, here are some ways
you can help:

- Try the `gnucash-uk-vat` options `--show-obligations`,
  `--show-open-obligations`, `--show-payments`, `--show-liabilities` and
  `--show-vat-return` options.
  Feedback on their successful operation would be appreciated.
- Try the `--show-account-data` mode.  Again, this is read-only, but interacts
  with the VAT API and your GnuCash accounts.  For all open VAT obligations, the
  output shows the 9 VAT return totals for the time period, along with
  individual account records   that combine to make these values.
  Feedback that the right data is returned.   I am not a VAT accountant.
- If you have been using GnuCash to keep VAT accounts, you can provide feedback
  on good ways to do this.

## Installing

```
pip3 install git+https://github.com/cybermaggedon/gnucash-uk-vat
```

This installs dependencies.  If you want to use `--assist` mode, you need
to install `pygtk2` also, which is not included in the dependency list.

There is a dependency on the `gnucash` Python module, which cannot be installed
from PyPI.  See <https://wiki.gnucash.org/wiki/Python_Bindings> for
installation.  On Linux (Debian, Ubuntu, Fedora), the Python modules are
available on package repositories.

There are instructions for MacOS installation which I have not tested on the
wiki page.

## Usage

There are two modes:
- [Assist mode](README.assist.md), which is a GTK-based dialog-driven.
  This automates everything including configuration file setup.
- [CLI mode](README.cli.md), which is purely CLI-based and has no
  dependency on PyGTK.

## GnuCash accounts structure

The default configuration file broadly maps to the Accounts structures generated
by UK VAT, but I had to tweak some things.  For VAT accounting transactions are
counted against a number of boxes, the 'trick' is to nest the accounts so
that this works.  For instance, box 

The 'trick' is to nest the accounts appropriately so that this works.  For
instance, box 3 is the sum of box 1 and box 2.  Hence box 3 should be associated
with an account which is a parent of the accounts providing the numbers for
box 1 and 2.  Box 5 is the delta between box 4 and box 3, which is achieved by
having the account associated with box 5 being the parent of box 3 and box 4
accounts.  Here are the default mappings:

- Box 1 (`vatDueSales`): "VAT:Output:Sales",
- Box 2 (`vatDueAcquisitions`): "VAT:Output:EU"
- Box 3 (`totalVatDue`): "VAT:Output"
- Box 4 (`vatReclaimedCurrPeriod`): "VAT:Input"
- Box 5 (`netVatDue`): "VAT"
- Box 6 (`totalValueSalesExVAT`): "Income:Sales:EU"
- Box 7 (`totalValuePurchasesExVAT`): "Expenses:VAT Purchases"
- Box 8 (`totalValueGoodsSuppliedExVAT`): "Income:Sales:EU:Goods"
- Box 9 (`totalAcquisitionsExVAT`): "Expenses:VAT Purchases:EU Reverse VAT"

If you have experience with VAT accounting feel free to offer me a rewrite this
section :)

I have included a sample file `accounts/accounts.gnucash` which contains some
sample transactions and works with the default configuration.

## Test VAT service

There is a test service which serves test data.  (See
`vat-data.json` in the source tree for an example.  The test service (roughly)
conforms to the HMRC VAT API.  The VRN is `vat-data.json` is `1234567890`.

You would run it thus:

```
./test-vat-service -d vat-data.json
```

To invoke the test service, change the configuration file:

```
{
    ...
    "application": {
        ...
	"profile": "local"
	...
    },
    "identity": {
        "vrn": "1234567890",
	...
    }
```

This will cause the adaptor to use `http://localhost:8080` for the VAT service.

You should then use the service as above, including authenticating.
The authentication mechanism is there, but dummy credentials are issued, and
nothing is verified.

## Sample accounts

A sample account file is included at `accounts/accounts.gnucash`.  This
account file contains some transactions dated in the 1Q17 quarter which match
the test data in HMRC's Sandbox.  There are also some transactions in 2020
which match the obligations in the `dummy-vat-service` data.

# Licences, Compliance, etc.

## Privacy

`gnucash-uk-vat` is hosted by you.  It runs on your computer, accesses
information from your accounts, and forwards data using the HMRC APIs.
Everything is within your control.  No other network systems are used, and no
information is transmitted to other parties.

Additional data (configuration and credentials) is stored on your
filesystem under your control and you should manage the credential
files as you would any password or other secret.

## Licence

Copyright (C) 2020, Cyberapocalypse Limited

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

