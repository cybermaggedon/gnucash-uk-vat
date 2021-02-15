
# GnuCash accounts structure

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

