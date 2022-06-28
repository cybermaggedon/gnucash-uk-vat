
Here are a couple of tools used for testing against the HMRC VAT MTD
sandbox.  There are client ID / secrets hard-coded into the scripts, you
need to set them to your sandbox values.  This is not for use in the live
environment or with production credentials.

- get-fraud-feedback: This code connects to the HMRC sandbox Fraud API and
  fetches feedback on compliance with Fraud API requirements.
- get-test-user: Connects to the Test User API and creates a new user for
  VAT MTD testing.

