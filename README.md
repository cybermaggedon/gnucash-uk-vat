
# `gnucash-uk-vat`

## Introduction

This is a utility which manages HMRC (UK) VAT returns in accordance with
HMRC MTD directives for users of the GnuCash accounting system.  It can
study your GnuCash accounts, compare this with your HMRC VAT obligations,
and produce the VAT return to meet your obligations.  As an optional step,
once the VAT return is filed, a bill can be posted describing the VAT
owing, and posted to an Accounts Payable account.

## Discuss

There's a #gnucash-uk-vat channel on our Discord server if you want
to discuss... https://discord.gg/3cAvPASS6p

## A word from our sponsors :)

If you need low cost, automated accounts filing for small businesses,
Accounts Machine has a commercial offering which incorporates the
functionality you see here in a web service.

The proposition is simple.  Accounts Machine does not offer an
accounting system.  You manage your accounts using GnuCash or anything
which produces CSV output.  You manage your accounts, manage your
invoices, manage receipts, and record everything in your application
under your control.  When it comes to filing returns, you upload your
accounts to accountsmachine.io and use the system to file VAT returns,
corporation tax returns, and company accounts with Companies House.
The production of returns is as automated as possible.  Accounts
production conforms to iXBRL specifications, and HMRC VAT MTD.

This service is able to simplify accounts filing for simple businesses.
Your company should be a Limited Company, conform to micro-entity
requirements, and have a single trade.  This service is aimed at making
life easier for startups and small businesses.

The roadmap is for launch in 2Q2022.  VAT filing is complete, just going
through the final validation process with HMRC.
[Demo is here](https://drive.google.com/file/d/1hMIPaSKxuWNScTD_0-tdmwexLYWCzTAv/view?usp=sharing)

Visit https://accountsmachine.io.  Accounts Machine is registered with HMRC
and Companies House for filing purposes and have successfully filed VAT,
corp tax and company accounts.

Join our discord service to keep on top of latest progress:
https://discord.gg/3cAvPASS6p

Enthusiastic early adopters will find free deal links on the Discord
server.  Looking forward to filing for you. :)

## GnuCash backends

Two ways of interacting with your GnuCash accounts are supported:
- The `gnucash` module is bundled only with Linux GnuCash packages, and can
  only by used on Linux.
- The `piecash` module is pure Python and can be obtained from package
  repositories.  This module only supports GnuCash files saved in
  Sqlite files or a Postgres database.  You can convert a GnuCash XML file into
  Sqlite by using the "Save As..." option in GnuCash.

## Status

This is a command-line utility, with a GTK-based dialog mode which removes
the need to know about configuration files or command-line options.
I have used this to submit my own VAT returns.  If you want to join the
party come to the #gnucash-uk-vat channel on Discord server 
https://discord.gg/3cAvPASS6p and I'll try to help you through the process.

## Credentials

In order to use this, you need production credentials (client ID and secret)
for the VAT submission API.  HMRC does not permit these credentials to be
shared publicly:

> We have checked with our colleagues who look after HMRC’s API
> Platform. They have advised that this is not allowed and would be likely
> to result in your Developer Hub application being blocked. We recommend
> that instead of sharing these credentials that you inform your users how
> they can register for their own Developer Hub application and use its
> credentials with your code.

In order to get credentials you would need to go through the full process to
register as a VAT MTD provider, which is not a simple process.

You would need to apply for production credentials using the HMRC developer
portal (you need to register).

Developer hub: 
https://developer.service.hmrc.gov.uk/api-documentation/docs/using-the-hub

### Testing

To use the staging API to test your integration, after registering you'll
need to change some settings in `config.json` under the `application` section:

  - Set `profile` to `test`.
  - Change `product-name` to the name you registered your project under.
  - Change `client-id` and `client-secret` matching what HMRC creates for you.

In the HMRC hub, under your application, you need to go to the redirect URIs
section and add `http://localhost:9876/auth`.

When following the auth link, just follow the links to get credentials and
a VRN for a test user from HMRC.

#### Fraud headers

Before requesting production access, you'll need to test the fraud headers.

To do this, run `test/test_fraud_api.py` (it accepts `--config` if not using the default).

If your auth credentials have expired from the previous test, you can recreate
them with `gnucash-uk-vat --authenticate` (again, accepts `--config`).

The response is expected to include a warning due to `gov-client-multi-factor`
being empty. But, no other errors should appear.

### Production

Once tested, you can click 'Get production credentials' and enter details about the
application.  When you apply for credentials, HMRC will contact
you to fill in an application.  As I understand it, this involves going
through a full acceptance test which involves testing against the
sandbox (which is what I have done).

You'll then need to change the config again using your production credentials and
`profile` set to `prod`.

## Installing

To install directly from a git repository:

```
pip3 install git+https://github.com/cybermaggedon/gnucash-uk-vat
```

To install/update from the local checkout, a wrapper script can be used:

```
[git-bash-prompt]> ./setup.sh
```

See [Installing](docs/installation.md).

## Usage

There are two modes:
- [Assist mode](docs/assist.md), which is a GTK-based dialog-driven.
  This automates everything including configuration file setup.
- [CLI mode](docs/cli.md), which is purely CLI-based and has no
  dependency on PyGTK.

## GnuCash accounts structure

See [Accounts](docs/accounts.md).

## Local test service

There is a local test service which allows you to emulate the HMRC VAT
service with test data under your control.

See [local test](docs/local-test.md).

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

Copyright (c) 2020-2021, Cyberapocalypse Limited
Copyright (c) 2021-2024, Accounts Machine Limited

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

# Tests

Run `pytest` or `make test`

