
# `gnucash-uk-vat` assist mode

## Introduction

This page describes assist mode which completes a full VAT submission
process, including configuration setup and authentication.  Configuration
and authentication information are cached in the same files that the
CLI uses.

## Usage

```
gnucash-uk-vat --assist
```

The dialog is an assist dialog.  Complete the step, then press Next to continue.

The first screen shows an introduction.

![alt text](screen1.png)

The second screen allows you to select the filename of your GnuCash accounts.

![alt text](screen2.png)

The third screen allows you to select the particular GnuCash accounts
containing VAT records.  See [GnuCash accounts structure](README.md#gnucash-accounts-structure).

![alt text](screen3.png)

The next screen allows you to authenticate with HMRC and store a
credential in `auth.json`.

![alt text](screen4.png)

The next screen allows you to enter your VRN.

![alt text](screen5.png)

The next screen allows you to select a VAT obligation period to submit the
VAT return for.

![alt text](screen6.png)

The next screen shows you the VAT return, and allows you to verify before
submitting.

![alt text](screen7.png)

Optionally, the next screen allows you to post a VAT bill.

![alt text](screen8.png)

The final screen shows a summary of actions taken.

![alt text](screen9.png)

