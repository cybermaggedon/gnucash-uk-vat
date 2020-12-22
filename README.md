
# `gnucash-uk-vat`

## Introduction

This code manages HMRC (UK) VAT returns in accordance with HMRC MTD directives
for users of the GnuCash accounting system.  It can study your GnuCash accounts,
compare this with your HMRC VAT obligations, and craft the VAT return to meet
your obligations.

This is command-line Python code.  At the time of writing, this code is
immature - it has only been tested against the test APIs.  It's possible
this code will not work at all.  It is not known whether an open source
project can achieve signoff to use production HMRC APIs.

In order to get this to work, you will need to be able to register the application
with HMRC for yourself as I am not in a position to share a client ID/secret with
you.  You will need an HMRC developer's account.

If you're an HMRC VAT user, and you use GnuCash, here are some ways
you can help:

- Try the `gnucash-uk-vat` in read-only mode.  Options `--show-obligations`,
  `--show-open-obligations`, `--show-payments`, `--show-liabilities` and
  `--show-vat-return` interact with the VAT API, but do not modify your VAT data.
  Feedback on their successful operation would be appreciated.
- Try the `--show-account-data` mode.  Again, this is read-only, but interacts
  with the VAT API and your GnuCash accounts.  For all open VAT obligations, the
  output shows the 9 VAT return totals for the time period, along with individual
  account records   that combine to make these values.  Feedback that the right
  data is returned.   I am not a VAT accountant.
- The option to submit a VAT return is totally untested, and not recommended
  at the moment.  If you are a developer, and familiar with techniques to
  capture outbound data and study it before it is sent to the production API,
  you may be able to help testing.

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
    },
    "application": {
        "name": "gnucash-uk-vat",
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
- The `accounts` block describes your GnuCash setup.  The `file` element
  has the filename of your accounts.  The rest of the elements map the
  9 VAT return boxes to GnuCash account names.  The default names map to common
  ways of setting up GnuCash to manage VAT returns.
- The `application` block provides information authenticating
  `gnucash-uk-vat` to the HMRC APIs.  The `client-id` and `client-secret` values
  can only be obtained by registering the application with HMRC using a developer
  account.  The `profile` element can be `test` or `production` to determine
  which API to talk to.
- The `identity` block contains information about you.  The `vrn` elements contains
  your VAT registration number.  The other elements are *legally required* by
  HMRC's fraud API, but are difficult to gather.  So, you should ensure the
  information is correct and accurate because you are *legally required* to do so
  in order to use the HMRC VAT APIs.
 
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

If all is successful, file `auth.json` is created containing security credentials.
You should treat the contents of that file as a password as it will permit
access to your VAT records by anyone who acquires that file.

## Using `gnucash-uk-vat`

### Obligations

You can list your recent obligation history:
```
[user@machine]$ gnucash-uk-vat --show-obligations
+--------+------------+------------+------------+------------+--------+
| Period |   Start    |    End     |    Due     |  Received  | Status |
+--------+------------+------------+------------+------------+--------+
|  18A1  | 2017-01-01 | 2017-03-31 | 2017-05-07 | 2017-05-06 |   F    |
|  18A2  | 2017-04-01 | 2017-06-30 | 2017-08-07 |            |   O    |
+--------+------------+------------+------------+------------+--------+
```

The output shows VAT return periods defined by start and end dates, along
with a due date and received date if submitted.  The Period column shows a
short-hand id for the time period.  The status column shows status F=fulfilled,
O=Open.

You can narrow the list to a time window by specifying the start and end
point as number of days in the past.

```
[user@machine mtd]$ gnucash-uk-vat --show-obligations --start 1500 --end 1200
```

You can also show just open obligations, ignoring obligations which are fulfilled.

```
[user@machine mtd]$ gnucash-uk-vat --show-open-obligations 
+--------+------------+------------+------------+--------+
| Period |   Start    |    End     |    Due     | Status |
+--------+------------+------------+------------+--------+
|  18A1  | 2017-01-01 | 2017-03-31 | 2017-05-07 |   O    |
+--------+------------+------------+------------+--------+
```

### Studying account data

This is really a debug / verification step at the moment.  The output below
shows what happens when HMRC's test interface meets the sample GnuCash file
which is bundled with the code:

```
[user@machine mtd]$ gnucash-uk-vat --show-account-data
Period: 18A1          Start: 2017-01-01     End: 2017-03-31

    vatDueSales:    1914.60

        +------------+---------+-----------------------+
        | 2017-01-10 |  248.00 | Widget 1              |
        | 2017-02-10 | 1666.60 | Sale 100 to Acme Ltd. |
        +------------+---------+-----------------------+

    vatDueAcquisitions:      40.00

        +------------+-------+-----------------------------+
        | 2017-01-03 | 40.00 | £220 service from Acme GmBH |
        +------------+-------+-----------------------------+

    totalVatDue:    1954.60

        +------------+---------+-----------------------------+
        | 2017-01-03 |   40.00 | £220 service from Acme GmBH |
        | 2017-01-10 |  248.00 | Widget 1                    |
        | 2017-02-10 | 1666.60 | Sale 100 to Acme Ltd.       |
        +------------+---------+-----------------------------+

    vatReclaimedCurrPeriod:      78.00

        +------------+-------+-----------------------------+
        | 2017-01-03 | 40.00 | £220 service from Acme GmBH |
        | 2017-01-05 | 38.00 | Micropants Windows          |
        +------------+-------+-----------------------------+

    netVatDue:    1876.60

        +------------+---------+-----------------------------+
        | 2017-01-03 |  -40.00 | £220 service from Acme GmBH |
        | 2017-01-05 |  -38.00 | Micropants Windows          |
        | 2017-01-03 |   40.00 | £220 service from Acme GmBH |
        | 2017-01-10 |  248.00 | Widget 1                    |
        | 2017-02-10 | 1666.60 | Sale 100 to Acme Ltd.       |
        +------------+---------+-----------------------------+

    totalValueSalesExVAT:    9573.00

        +------------+---------+-----------------------+
        | 2017-01-10 | 1240.00 | Widget 1              |
        | 2017-02-10 | 8333.00 | Sale 100 to Acme Ltd. |
        +------------+---------+-----------------------+

    totalValuePurchasesExVAT:     352.00

        +------------+--------+-----------------------------+
        | 2017-01-03 | 200.00 | £220 service from Acme GmBH |
        | 2017-01-05 | 152.00 | Micropants Windows          |
        +------------+--------+-----------------------------+

    totalValueGoodsSuppliedExVAT:    1240.00

        +------------+---------+----------+
        | 2017-01-10 | 1240.00 | Widget 1 |
        +------------+---------+----------+

    totalAcquisitionsExVAT:     200.00

        +------------+--------+-----------------------------+
        | 2017-01-03 | 200.00 | £220 service from Acme GmBH |
        +------------+--------+-----------------------------+
```

The output shows a section for each obligation period which is opened.  The
obligation period is shown with a header indented hard-left on output.
Then, for each of the 9 values which must be reported (referred to as 9 boxes
in VAT documentation), the summary line is shown, and a table of individual
transactions which contribute to that total.

### Submit VAT return

If you were happy with the data that would be submitted from the previous
step, you can go ahead and submit the data.  However, this is not recommended
at the moment.  You need to specify the Period key visible in the obligations
list, or the output from `--show-account-data`.  Once submitted, you cannot
recall the VAT return.  Given the limited testing, it really is not recommended
you perform this step.

```
[user@machine mtd]$ gnucash-uk-vat --submit-vat-return --period 18A1
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

