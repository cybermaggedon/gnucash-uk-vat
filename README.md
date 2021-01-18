
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
immature - it has only been tested against the Sandbox APIs.  It is not known
whether this open source project will be able achieve signoff to use
production HMRC APIs.   I am in the process submitting for production
credentials.

Anyone can register an HMRC developer test/sandbox account and run this code
against the sandbox.

If you're an HMRC VAT user, and you use GnuCash, here are some ways
you can help:

- Try the `gnucash-uk-vat` in read-only mode.  Options `--show-obligations`,
  `--show-open-obligations`, `--show-payments`, `--show-liabilities` and
  `--show-vat-return` interact with the VAT API.
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

There is a dependency on the `gnucash` Python module, which cannot be installed
from PyPI.  See <https://wiki.gnucash.org/wiki/Python_Bindings> for
installation.  On Linux (Debian, Ubuntu, Fedora), the Python modules are
available on package repositories.

There are instructions for MacOS installation which I have not tested on the
wiki page.

## Setting things up

### Create a configuration file

You need a configuration file.  Run this to create `config.json`:

```
gnucash-uk-vat --init-config
```

No interaction with HMRC takes place.  This simply gathers some information
about your machine and writes the configuration file.

The configuration file looks something like this:

```
{
    "accounts": {
        "file": "accounts/accounts.gnucash",
        "vatDueSales": "VAT:Output:Sales",
	...
        "liabilities": "VAT:Liabilities",
        "bills": "Accounts Payable"
    },
    "application": {
        "profile": "test",
        "client-id": "<CLIENTID>",
        "client-secret": "<CLIENTSECRET>"
    },
    "identity": {
        "vrn": "<VRN>",
	...
    }
}
```

To continue you need to edit some things:
- The `accounts` block describes your GnuCash setup.  The `file` element has
  the filename of your accounts.  The next 9 elements map the 9 VAT return
  boxes to GnuCash account names.  The default names map to common ways of
  setting up GnuCash to manage VAT returns.  The `liabilities` and `bills`
  describe accounts to debit/credit the VAT bill to if you want to use the
  `--post-vat-bill` option.
- The `application` block provides information authenticating
  `gnucash-uk-vat` to the HMRC APIs.  The `client-id` and `client-secret`
  values can only be obtained by registering the application with HMRC using
  a developer account.  The `profile` element can be `test` or `production`
  to determine which API to talk to.  Or `local` to talk to my test VAT
  service (see below).
- The `identity` block contains information about you.  The `vrn` elements
  contains your VAT registration number.  The other elements are *legally
  required* by HMRC's fraud API, but are difficult to gather.  So, you
  should ensure the information is correct and accurate because you are
  *legally required* to do so in order to use the HMRC VAT APIs.
 
### Authentication

Once you have the configuration set up, you can proceed to authenticate using
a web browser.

```
gnucash-uk-vat --authenticate
```

This initiates an OAUTH2 authentication process.  You should see output:
```
Please visit the following URL and authenticate:
https://....gov.uk/oauth/authorize?response_type=code&client_id=...
```

Your next steps are:
- To protect yourself, satisfy yourself that the provided URL lives within the
  `gov.uk` domain.
- Copy and paste the URL to a web browser.
- Check the padlock on your browser to ensure the transfer is secure, and
  again, check for the `gov.uk` domain.
- Once you are happy, authenticate with HMRC, and grant permission for the
  client API to access your HMRC data.

If all is successful, file `auth.json` is created containing security
credentials.  You should treat the contents of that file as a password as it
will permit access to your VAT records by anyone who acquires that file.

## Using `gnucash-uk-vat`

### Obligations

You can list your recent obligation history:
```
[user@machine]$ gnucash-uk-vat --show-obligations
+------------+------------+------------+------------+--------+
|   Start    |    End     |    Due     |  Received  | Status |
+------------+------------+------------+------------+--------+
| 2017-01-01 | 2017-03-31 | 2017-05-07 | 2017-05-06 |   F    |
| 2017-04-01 | 2017-06-30 | 2017-08-07 |            |   O    |
+------------+------------+------------+------------+--------+
```

The output shows VAT return periods defined by start and end dates, along
with a due date and received date if submitted.
The status column shows status F=fulfilled, O=Open.
`gnucash-uk-vat` uses the due date to refer to obligation periods.

You can narrow the list to a time window by specifying the start and end
date.  The default is to cover the previous year.

```
[user@machine mtd]$ gnucash-uk-vat --show-obligations --start 2019-06-01 --end 2019-12-31
```

You can also show just open obligations, ignoring obligations which are
fulfilled.

```
[user@machine mtd]$ gnucash-uk-vat --show-open-obligations 
+------------+------------+------------+--------+
|   Start    |    End     |    Due     | Status |
+------------+------------+------------+--------+
| 2017-01-01 | 2017-03-31 | 2017-05-07 |   O    |
+------------+------------+------------+--------+
```

### Studying account data

Prior to submitting a VAT return, you will want to study  the return figures.
The output below shows what happens when HMRC's test interface meets the
sample GnuCash file which is bundled with the code:

```
[user@machine mtd]$ gnucash-uk-vat --show-account-detail
VAT due: 2017-05-07    Start: 2017-01-01     End: 2017-03-31

    VAT due on sales: 1914.60

        +------------+---------+-----------------------+
        | 2017-01-10 |  248.00 | Widget 1              |
        | 2017-02-10 | 1666.60 | Sale 100 to Acme Ltd. |
        +------------+---------+-----------------------+

    VAT due on acquisitions: 40.00

        +------------+-------+-----------------------------+
        | 2017-01-03 | 40.00 | £220 service from Acme GmBH |
        +------------+-------+-----------------------------+

    Total VAT due: 1954.60

        +------------+---------+-----------------------------+
        | 2017-01-03 |   40.00 | £220 service from Acme GmBH |
        | 2017-01-10 |  248.00 | Widget 1                    |
        | 2017-02-10 | 1666.60 | Sale 100 to Acme Ltd.       |
        +------------+---------+-----------------------------+

    VAT reclaimed: 78.00

        +------------+-------+-----------------------------+
        | 2017-01-03 | 40.00 | £220 service from Acme GmBH |
        | 2017-01-05 | 38.00 | Micropants Windows          |
        +------------+-------+-----------------------------+

    VAT due: 1876.60

        +------------+---------+-----------------------------+
        | 2017-01-03 |  -40.00 | £220 service from Acme GmBH |
        | 2017-01-05 |  -38.00 | Micropants Windows          |
        | 2017-01-03 |   40.00 | £220 service from Acme GmBH |
        | 2017-01-10 |  248.00 | Widget 1                    |
        | 2017-02-10 | 1666.60 | Sale 100 to Acme Ltd.       |
        +------------+---------+-----------------------------+

    Sales before VAT: 9573.00

        +------------+---------+-----------------------+
        | 2017-01-10 | 1240.00 | Widget 1              |
        | 2017-02-10 | 8333.00 | Sale 100 to Acme Ltd. |
        +------------+---------+-----------------------+

    Purchases ex. VAT: 352.00

        +------------+--------+-----------------------------+
        | 2017-01-03 | 200.00 | £220 service from Acme GmBH |
        | 2017-01-05 | 152.00 | Micropants Windows          |
        +------------+--------+-----------------------------+

    Goods supplied ex. VAT: 1240.00

        +------------+---------+----------+
        | 2017-01-10 | 1240.00 | Widget 1 |
        +------------+---------+----------+

    Total acquisitions ex. VAT: 200.00

        +------------+--------+-----------------------------+
        | 2017-01-03 | 200.00 | £220 service from Acme GmBH |
        +------------+--------+-----------------------------+
```

The output shows a section for each obligation period which is opened.  The
obligation period due date is shown with a header indented hard-left on output.
Then, for each of the 9 values which must be reported (referred to as 9 boxes
in VAT documentation), the summary line is shown, and a table of individual
transactions which contribute to that total.

There is a `--show-account-summary` operation which just shows the 9 VAT
box values without transaction data.

### Submit VAT return

If you were happy with the data that would be submitted from the previous
step, you can go ahead and submit the data.  
You need to specify the obligation using the due date as shown in
Period key visible in the obligations
list, or the output from `--show-account-detail`.  Once submitted, you cannot
recall the VAT return.

```
[user@machine mtd]$ gnucash-uk-vat --submit-vat-return --due-date 2017-05-07
VAT due on sales              :         1914.60
VAT due on acquisitions       :           40.00
Total VAT due                 :         1954.60
VAT reclaimed                 :           78.00
VAT due                       :         1876.60
Sales before VAT              :         9573.00
Purchases ex. VAT             :          352.00
Goods supplied ex. VAT        :         1240.00
Total acquisitions ex. VAT    :          200.00
```

Before submission, you are shown the return summary, and are offered a final
yes/no prompt to confirm submission.

### Create VAT bill

This is an optional step which you would use after submitting a VAT return.
This operation posts a bill for the VAT owed.  The bill debits a VAT Liability
account and credits an Accounts Payable account.  An HMRC VAT vendor is
created with the `hmrc-vat` ID if such a vendor does not already exist.

```
[user@machine mtd]$ gnucash-uk-vat --post-vat-bill --due-date 2017-05-07
```

The bill records the amount of VAT due on sales and goods, and shows a
negative line for VAT rebate.

### View VAT return

Views a previously submitted return by due date.

```
[user@machine mtd]$ gnucash-uk-vat --show-vat-return --due-date 2017-05-07
VAT due on sales              :          100.00
VAT due on acquisitions       :          120.00
Total VAT due                 :          220.00
VAT reclaimed                 :           30.00
VAT due                       :          180.00
Sales before VAT              :         1000.00
Purchases ex. VAT             :         1200.00
Goods supplied ex. VAT        :           50.00
Total acquisitions ex. VAT    :           30.00
```

### Show liabilities

This is what you owe HMRC for VAT returns.

```
[user@machine mtd]$ gnucash-uk-vat --show-liabilities
+------------+----------------------+---------+-------------+------------+
|   Period   |         Type         | Amount  | Outstanding |    Due     |
+------------+----------------------+---------+-------------+------------+
| 2017-01-01 | VAT Return Debit Cha | 463872  |   463872    | 2017-05-12 |
| 2017-04-01 | VAT Return Debit Cha |   15    |      0      | 2017-06-09 |
| 2017-08-01 |    VAT CA Charge     | 8493.38 |   7493.38   | 2017-10-07 |
| 2017-10-01 | VAT OA Debit Charge  |  3000   |    2845     | 2017-12-31 |
+------------+----------------------+---------+-------------+------------+
```

By default, records from the previous year are shown, this can be altered with
the `--start` and `--end` options.

### Show payments

This is what you have paid HMRC for VAT.

```
[user@machine mtd]$ gnucash-uk-vat --show-payments
+--------+------------+
| Amount |  Received  |
+--------+------------+
|   5    | 2017-02-11 |
|   50   | 2017-03-11 |
|  1000  | 2017-03-12 |
|  321   | 2017-08-05 |
|   91   |            |
|   5    | 2017-09-12 |
+--------+------------+
```

By default, records from the previous year are shown, this can be altered with
the `--start` and `--end` options.

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

