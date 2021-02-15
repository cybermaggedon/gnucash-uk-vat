
# `gnucash-uk-vat`

## Introduction

This is a utility which manages HMRC (UK) VAT returns in accordance with
HMRC MTD directives for users of the GnuCash accounting system.  It can
study your GnuCash accounts, compare this with your HMRC VAT obligations,
and produce the VAT return to meet your obligations.  As an optional step,
once the VAT return is filed, a bill can be created describing the VAT
owing, and posted to an Accounts Payable account.

## Status

This is a command-line utility, with a GTK-based dialog mode which removes
the need to know about configuration files or command-line options.  At the
time of writing, this code is immature - it has been tested against the
Sandbox APIs.  You may be the first person to submit a production VAT
return. :) Email me, mark AT cyberapocalypse DOT co DOT uk, and I'll support
you through the process.

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

See [Installing](docs/installation.md).

## Usage

There are two modes:
- [Assist mode](docs/assist.md), which is a GTK-based dialog-driven.
  This automates everything including configuration file setup.
- [CLI mode](docs/cli.md), which is purely CLI-based and has no
  dependency on PyGTK.

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

