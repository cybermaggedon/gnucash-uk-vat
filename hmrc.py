
from urllib.parse import urlencode, quote_plus
import aiohttp
import aiohttp.web
import time
import asyncio
from datetime import datetime, timedelta, date
import requests
import json

vat_box = [
    
    # VAT due on sales and other outputs. This corresponds to box 1 on the VAT
    # Return form.
    "vatDueSales",
    
    # VAT due on acquisitions from other EC Member States. This corresponds
    # to box 2 on the VAT Return form.
    "vatDueAcquisitions",
    
    # Total VAT due (the sum of vatDueSales and vatDueAcquisitions). This
    # corresponds to box 3 on the VAT Return form.
    "totalVatDue",
    
    # VAT reclaimed on purchases and other inputs (including acquisitions
    # from the EC). This corresponds to box 4 on the VAT Return form.
    "vatReclaimedCurrPeriod",
    
    # The difference between totalVatDue and vatReclaimedCurrPeriod. This
    # corresponds to box 5 on the VAT Return form.
    "netVatDue",
    
    # Total value of sales and all other outputs excluding any VAT. This
    # corresponds to box 6 on the VAT Return form. The value must be in pounds
    # (no pence)
    "totalValueSalesExVAT",
    
    # Total value of purchases and all other inputs excluding any VAT
    # (including exempt purchases). This corresponds to box 7 on the VAT
    # Return form. The value must be in pounds (no pence)
    "totalValuePurchasesExVAT",

    # Total value of all supplies of goods and related costs, excluding any
    # VAT, to other EC member states. This corresponds to box 8 on the VAT
    # Return form.
    "totalValueGoodsSuppliedExVAT",

    # Total value of acquisitions of goods and related costs excluding any
    # VAT, from other EC member states. This corresponds to box 9 on the VAT
    # Return form.
    "totalAcquisitionsExVAT"

]

# AuthCollector is a class which provides a temporary web service in order to
# receive OAUTH credential tokens
class AuthCollector:

    # Constructor
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = True
        self.result = None

    # Main body coroutine
    async def run(self):

        # Handler, there is only one endpoint, it receives credential tokens
        async def handler(req):

            # Store result.  Debounce subsequent calls (shouldn't happen).
            if self.result == None:
                self.result = {
                    v: req.query[v]
                    for v in req.query
                }

            # Stops the web server
            self.running = False

            # Send response, which appears in the browser.
            return aiohttp.web.Response(
                body='Token received.',
                content_type="text/html"
            )

        # Start web server
        server = aiohttp.web.Server(handler)
        runner = aiohttp.web.ServerRunner(server)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, self.host, self.port)
        await site.start()

        # Sleep until we have a result
        while self.running:
            await asyncio.sleep(0.2)

        # Close web server
        await site.stop()
        await runner.cleanup()

        # Return the response we received (or an error)
        return self.result

# VAT API client implementation
class Vat:

    # Constructor
    def __init__(self, config, auth):
        self.config = config
        self.auth = auth

        # Production API endpoints
        self.oauth_base = 'https://www.tax.service.gov.uk'
        self.api_base = 'https://api.service.hmrc.gov.uk'

    # Get an auth code
    def get_code(self):
        return asyncio.run(self.get_code_coro())

    # Co-routine implementation
    async def get_code_coro(self):

        # Build request to OAUTH endpoint
        url = self.oauth_base + '/oauth/authorize'

        params = urlencode(
            {
                'response_type': 'code',
	        'client_id': self.config.get("application.client-id"),
                'scope': 'read:vat+write:vat',
                'redirect_uri': 'http://localhost:9876/auth',
            }
        )

        url = url + "?" + params

        # Send user to the URL
        print("Please visit the following URL and authenticate:")
        print(url)

        # Start auth code collector, and wait for it to finish
        a = AuthCollector("localhost", 9876)
        res = await a.run()

        # If error, raise as RuntimeError
        if "error" in res:
            raise RuntimeError(str(res))

        # Return the code
        code = res["code"]
        return code

    # Convert code to an auth credential
    def get_auth(self, code):
        auth = asyncio.run(self.get_auth_coro(code))
        self.auth.auth = auth

    # Co-routine implementation
    async def get_auth_coro(self, code):

        # Construct auth request
        url = self.api_base + "/oauth/token"

        cid = self.config.get("application.client-id")
        csecret = self.config.get("application.client-secret")

        params = urlencode(
                 {
                     'client_id': cid,
                     'client_secret': csecret,
                     'grant_type': 'authorization_code',
                     'redirect_uri': 'http://localhost:9876/auth',
                     'code': code
                 }
        )

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        now = datetime.utcnow()

        # Issue request
        async with aiohttp.ClientSession() as client:
            async with client.post(url, headers=headers, data=params) as resp:
                res = await resp.json()

        # Turn expiry period into a datetime
        expiry = now + timedelta(seconds=int(res["expires_in"]))
        expiry = expiry.replace(microsecond=0)

        # Return credentials
        return {
            "access_token": res["access_token"],
            "refresh_token": res["refresh_token"],
            "token_type": res["token_type"],
            "expires": expiry.isoformat()
        }

    # Called to refresh credentials, re-issue auth request from refresh token
    def refresh_token(self, refresh):
        return asyncio.run(self.refresh_token_coro(refresh))

    # Co-routine implementation of refresh
    async def refresh_token_coro(self, refresh):

        url = self.api_base + "/oauth/token"

        cid = self.config.get("application.client-id")
        csecret = self.config.get("application.client-secret")

        params = urlencode(
                 {
                     'client_id': cid,
                     'client_secret': csecret,
                     'grant_type': 'refresh_token',
                     'refresh_token': refresh
                 }
        )

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        now = datetime.utcnow()

        async with aiohttp.ClientSession() as client:
            async with client.post(url, headers=headers, data=params) as resp:
                res = await resp.json()

        expiry = now + timedelta(seconds=int(res["expires_in"]))
        expiry = expiry.replace(microsecond=0)

        return {
            "access_token": res["access_token"],
            "refresh_token": res["refresh_token"],
            "token_type": res["token_type"],
            "expires": expiry.isoformat()
        }

    # Constructs HTTP headers which meet the Fraud API.  Most of this comes from
    # config
    def get_fraud_headers(self):

        mac = self.config.get("identity.mac-address").replace(":", "%3A")

        # This is a script, no multi-factor authentication to call on
        mfa = 'type=%s&timestamp=%sZ&unique-reference=%s' % (
            "OTHER", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            self.config.get("identity.user")
        )

        # Return headers
        return {
            'Gov-Client-Connection-Method': 'OTHER_DIRECT',
            'Gov-Client-Device-ID': self.config.get("identity.device"),
            'Gov-Client-User-Ids': 'os=%s' % self.config.get("identity.user"),
            'Gov-Client-Timezone': 'UTC+00:00',
            'Gov-Client-Local-IPs': self.config.get("identity.hostname"),
            'Gov-Client-MAC-Addresses': mac,
            'Gov-Client-User-Agent': self.config.get("identity.user-agent"),
            'Gov-Client-Multi-Factor': mfa,
            'Gov-Vendor-Version': 'gnucash-uk-vat=0.0.1',
            'Gov-Vendor-License-IDs': 'gnu=eccbc87e4b5ce2fe28308fd9f2a7baf3',
            'Authorization': 'Bearer %s' % self.auth.get("access_token"),
        }

    # API request, fetch obligations which are in state O.
    def get_open_obligations(self, vrn):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "status": "O"
        }

        url = self.api_base + '/organisations/vat/%s/obligations?%s' % (
            vrn,
            urlencode(params)
        )

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError("HTTP error %d" % resp.status_code)

        obj = resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        for v in obj["obligations"]:
            v["start"] = date.fromisoformat(v["start"])
            v["end"] = date.fromisoformat(v["end"])
            v["due"] = date.fromisoformat(v["due"])

        return obj["obligations"]

    # API request, fetch obligations which are in a time period.
    def get_obligations(self, vrn, start, end):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }

        url = self.api_base + '/organisations/vat/%s/obligations?%s' % (
            vrn,
            urlencode(params)
        )

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError("HTTP error %d" % resp.status_code)

        obj = resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        for v in obj["obligations"]:
            v["start"] = date.fromisoformat(v["start"])
            v["end"] = date.fromisoformat(v["end"])
            v["due"] = date.fromisoformat(v["due"])
            if "received" in v:
                v["received"] = date.fromisoformat(v["received"])
            else:
                v["received"] = None

        return obj["obligations"]

    # API request, fetch a VAT return instance.
    def get_vat_return(self, vrn, period):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "periodKey": period
        }

        url = self.api_base + '/organisations/vat/%s/returns/%s' % (
            vrn, quote_plus(period)
        )

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError("HTTP error %d" % resp.status_code)

        obj = resp.json()

        if "code" in obj:
            raise RuntimeError(obj["message"])

        return obj

    # API request, submit a VAT return.
    def submit_vat_return(self, vrn, rtn):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        url = self.api_base + '/organisations/vat/%s/returns' % (
            vrn
        )

        resp = requests.post(url, headers=headers, data=json.dumps(rtn))
        if resp.status_code != 201:
            raise RuntimeError("HTTP error %d" % resp.status_code)

        obj = resp.json()

        if "code" in obj:
            raise RuntimeError(obj["message"])

        return obj

    # Get liabilities in time period
    def get_vat_liabilities(self, vrn, start, end):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }

        url = self.api_base + '/organisations/vat/%s/liabilities?%s' % (
            vrn,
            urlencode(params)
        )

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError("HTTP error %d" % resp.status_code)

        obj = resp.json()

        if "liabilities" not in obj:
            raise RuntimeError(obj["message"])

        for v in obj["liabilities"]:
            if "taxPeriod" in v:
                v["taxPeriod"]["from"] = date.fromisoformat(v["taxPeriod"]["from"])
                v["taxPeriod"]["to"] = date.fromisoformat(v["taxPeriod"]["to"])
            if "due" in v:
                v["due"] = date.fromisoformat(v["due"])

        return obj["liabilities"]

    # Get payments in time period
    def get_vat_payments(self, vrn, start, end):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }

        url = self.api_base + '/organisations/vat/%s/payments?%s' % (
            vrn,
            urlencode(params)
        )

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError("HTTP error %d" % resp.status_code)

        obj = resp.json()

        if "payments" not in obj:
            raise RuntimeError(obj["message"])

        for v in obj["payments"]:
            if "received" in v:
                v["received"] = date.fromisoformat(v["received"])

        return obj["payments"]

# Like VAT, but talks to test API endpoints.
class VatTest(Vat):
    def __init__(self, config, auth):
        super().__init__(config, auth)
        self.oauth_base = 'https://test-www.tax.service.gov.uk'
        self.api_base = 'https://test-api.service.hmrc.gov.uk'

# Like VAT, but talks to an API endpoints on localhost:8080.
class VatLocalTest(Vat):
    def __init__(self, config, auth):
        super().__init__(config, auth)
        self.oauth_base = 'http://localhost:8080'
        self.api_base = 'http://localhost:8080'

