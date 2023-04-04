# Test Suite to run tests against HMRC sandbox.
Open a console (Git Bash for Windows) in the 'test' directory.

# Help
Display the help using:

    ./gnucash-uk-vat.sh help

# Overview
Script to launch various commands required to unit-test the gnucash-uk-vat bridging application.

# Requirements
This script assumes that the setup.sh has been run for the gnucash-uk-vat bridging application.

See ../README.md for instruction on how to run the setup.sh.

# Initial setup
The first time the './gnucash-uk-vat.sh config' command is run, it checks for:
1. gnucash-uk-vat script

   If this is missing, the 'setup.sh' hasn't been run yet.
   See 'Requirements' section above.
2. User configuration file

   The 'gnucash-uk-vat --init-config' command will use the default values
   stored in a private User/Profile specific configuration file:

       /c/Users/awltux/.gnucash-uk-vat-test.json

   If this file doesnt exist, it creates a new copy from a template.

   IMPORTANT:

   Update this config file with your private credentials and common configuration:

     a) 'application' section: Add the client credentials for your sandbox application
        defined on the MTD developer site.

     b) 'accounts' section: Add GnuCash accounts for the test gnucash data
        file: hmrc-test.sqlite3.gnucash

        See the config.example.json for the accounts that should be used
        to test with the hmrc-test.sqlite3.gnucash data file.

     c) 'identity' section: can be removed, as it is not used to initialise a config.json.

# Create gnucash-uk-vat-test.json
The test config file can be created or updated using the command:

    './gnucash-uk-vat.sh config'

This will create a local config file: gnucash-uk-vat-test.json

NOTE: The 'identity.vrn' field can't be populated until there is an
      application.client-[id|secret]
      See 'Create HMRC User' section below.

# Create Test User
When using the test (sandbox) profile, you will need to create a test user (Don't use your HMRC production credentials!)

    './gnucash-uk-vat.sh user'

This creates a user in the MTD system and downloads the users details into user.json

NOTE: This command assumes the application associated with the client-id in
          gnucash-uk-vat-test.json
      has been configured to access the 'Create Test User' endpoint
      in 'API Subscriptions' when viewin application details from here:
      https://developer.service.hmrc.gov.uk/developer/applications

# Update gnucash-uk-vat-test.json with VRN
After updating the user.json file, update the config file to use the new test VRN.

    './gnucash-uk-vat.sh config'

# Authenticate with HMRC
Run this command to authenticate with HMRC MTD sandbox application.:

    './gnucash-uk-vat.sh auth'

Open the printed authentication URL in a browser and enter the test MTD account credentials printed in the console.
Once authenticated, the file 'test/auth.json' will be populated with a short lived authentication token.

# Test Fraud Prevention Headers
Run this command to verify that the fraud headers submitted by gnucash-uk-vat
complies with the HMRC MTD requirements.

    './gnucash-uk-vat.sh test-fraud'

A report will be printed to the screen showing any issues it encountered.

NOTE #1: Missing header 'gov-client-multi-factor': A bridge system doesnt generally use MFA.

NOTE #2: This command assumes the application associated with the client-id in
            gnucash-uk-vat-test.json
         has been configured to access the 'Test Fraud Prevention Headers' endpoint
         in 'API Subscriptions' when viewin application details from here:
         https://developer.service.hmrc.gov.uk/developer/applications

# show-obligations
Show all obligations in MTD for the test year

    './gnucash-uk-vat.sh show-obligations'

This should show both Finished and Open VAT obligations.

# show-open-obligations
Show all open obligations in MTD for the test year

    './gnucash-uk-vat.sh show-open-obligations'

This should only show Open VAT obligations.

# show-account-summary
Show GnuCash account summary for a particular due_date

    './gnucash-uk-vat.sh show-account-summary [0|1]'

This will report the account summary for the Obligation matching the due_date_index.

# show-account-detail
Show GnuCash account details for a particular due_date

    './gnucash-uk-vat.sh show-account-detail [0|1]'

This will report the account details for the Obligation matching the due_date_index.

# show-liabilities
Show VAT liabilities for start and end dates

    './gnucash-uk-vat.sh show-liabilities'

This will report the current liabilities matching the due_date_index.

# show-payments
Show VAT payments for start and end dates

    './gnucash-uk-vat.sh show-payments'

This will report the VAT payments matching the due_date_index.

# show-vat-return
Show VAT return for due dates

    './gnucash-uk-vat.sh show-payments [0|1]'

This will report the VAT returns matching the due_date_index.

# submit-vat-return
Show VAT payments for due dates

    './gnucash-uk-vat.sh show-payments [0|1]'

This will submit VAT return matching the due_date_index.


