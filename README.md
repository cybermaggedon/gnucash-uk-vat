
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

There are two ways to authenticate with HMRC.

### Proxy mode (recommended)

The simplest approach is to use the hosted OAuth proxy.  The proxy holds
the HMRC application credentials on your behalf, so you do not need to
register as an HMRC developer.  Add a `proxy` section to your
configuration file:

```json
{
  "proxy": {
    "email": "you@example.com"
  }
}
```

Setting `proxy.email` activates proxy mode.  Authentication, token
exchange, and token refresh are handled through the proxy; all other
HMRC API calls (obligations, returns, etc.) go directly to HMRC using
your bearer token.

### Direct mode

If you prefer to authenticate directly with HMRC, you will need your own
production credentials (client ID and secret).  HMRC does not permit
these credentials to be shared publicly, so you must register for your
own.

Developer hub:
https://developer.service.hmrc.gov.uk/api-documentation/docs/using-the-hub

#### Testing

To use the staging API to test your integration, after registering you’ll
need to change some settings in `config.json` under the `application` section:

  - Set `profile` to `test`.
  - Change `product-name` to the name you registered your project under.
  - Change `client-id` and `client-secret` matching what HMRC creates for you.

In the HMRC hub, under your application, you need to go to the redirect URIs
section and add `http://localhost:9876/auth`.

When following the auth link, just follow the links to get credentials and
a VRN for a test user from HMRC.

##### Fraud headers

Before requesting production access, you’ll need to test the fraud headers.

To do this, run `test/test_fraud_api.py` (it accepts `--config` if not using the default).

If your auth credentials have expired from the previous test, you can recreate
them with `gnucash-uk-vat --authenticate` (again, accepts `--config`).

The response is expected to include a warning due to `gov-client-multi-factor`
being empty. But, no other errors should appear.

#### Production

Once tested, you can click ‘Get production credentials’ and enter details about the
application.  When you apply for credentials, HMRC will contact
you to fill in an application.

The list of endpoints supported at any point in time can be found by looking through
the features at: https://github.com/cybermaggedon/gnucash-uk-vat/blob/master/docs/cli.md#using-gnucash-uk-vat

As the software doesn’t handle user data, you shouldn’t need to include ToS, but you
can always point to the simple license and notice at:
https://github.com/cybermaggedon/gnucash-uk-vat#licences-compliance-etc

You will likely be asked to test all supported features, so probably best to run
through each example command listed in the CLI docs when submitting.

After approval (can take months), you’ll then need to change the config again
using your production ID and secret, plus change `profile` to `prod`.

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

`gnucash-uk-vat` is hosted by you.  It runs on your computer and accesses
information from your accounts.

In **direct mode**, all data flows directly between your software and
HMRC services.  No other network systems are involved.

In **proxy mode**, all data also flows directly between you and HMRC,
with the sole exception of credential provisioning.  A proxy operated
by this project acts as a mediator so that HMRC application credentials
are provisioned to you using our security credentials, without revealing
those credentials to anyone else.  No information is stored by us in
this process.  The proxy source code is included in this repository
and can be inspected.  All other interactions -- VAT submissions, API
access, and so on -- are done directly between your software and HMRC
services.

Configuration and credentials are stored on your filesystem under your
control and you should manage the credential files as you would any
password or other secret.

## Licence

Copyright (c) 2021-2026, Cybermaggedon

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

