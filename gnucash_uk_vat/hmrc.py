
from urllib.parse import urlencode, quote_plus
import aiohttp
import aiohttp.web
import time
import asyncio
from datetime import datetime, timedelta, date
import requests
import json

from . model import *

# AuthCollector is a class which provides a temporary web service in order
# to receive OAUTH credential tokens
class AuthCollector:

    # Constructor
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = True
        self.result = None

    # Main body coroutine
    async def run(self):

        # Handler, there is only one endpoint, it receives credential
        # tokens
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

    # Called to refresh credentials, re-issue auth request from refresh
    # token
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

    # Constructs HTTP headers which meet the Fraud API.  Most of this
    # comes from config
    def build_fraud_headers(self):

        mac = quote_plus(self.config.get("identity.mac-address"))

        # There is no authentication for which an MFA header would make sense
#        mfa = urlencode({
#            "type": "OTHER",
#            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
#            "unique-reference": self.config.get("identity.user")
#        })

        identity_time = self.config.get("identity.time")

        # Return headers
        return {
            'Gov-Client-Connection-Method': 'OTHER_DIRECT',
            'Gov-Client-Device-ID': self.config.get("identity.device"),
            'Gov-Client-User-Ids': 'os=%s' % self.config.get("identity.user"),
            # Batch code, we're doing everything in UTC
            'Gov-Client-Timezone': 'UTC+00:00',
            'Gov-Client-Local-IPs': self.config.get("identity.hostname"),
            'Gov-Client-Local-IPs-Timestamp': identity_time,
            'Gov-Client-MAC-Addresses': mac,
            'Gov-Client-User-Agent': self.config.get("identity.user-agent"),
            # No MFA header
#            'Gov-Client-Multi-Factor': mfa,
            'Gov-Vendor-Version': 'gnucash-uk-vat=1.0',
            'Gov-Vendor-Product-Name': 'gnucash-uk-vat',
            # No licence, hence no licence ID.
#            'Gov-Vendor-License-IDs': 'gnu=eccbc87e4b5ce2fe28308fd9f2a7baf3',
            'Authorization': 'Bearer %s' % self.auth.get("access_token"),
        }

    # Test fraud headers.  Only available in Sandbox, not production
    def test_fraud_headers(self):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        url = self.api_base + '/test/fraud-prevention-headers/validate'

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        if resp.status_code != 200:
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        return obj

    # API request, fetch obligations which are in state O.
    def get_open_obligations(self, vrn):

        headers = self.build_fraud_headers()
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
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        obligations = [
            Obligation.from_dict(v) for v in  obj["obligations"]
        ]

        return obligations

    # API request, fetch obligations which are in a time period.
    def get_obligations(self, vrn, start, end):

        headers = self.build_fraud_headers()
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
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        return [
            Obligation.from_dict(v) for v in obj["obligations"]
        ]

    # API request, fetch a VAT return instance.
    def get_vat_return(self, vrn, period):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "periodKey": period
        }

        url = self.api_base + '/organisations/vat/%s/returns/%s' % (
            vrn, quote_plus(period)
        )

        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        return Return.from_dict(obj)

    # API request, submit a VAT return.
    def submit_vat_return(self, vrn, rtn):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        url = self.api_base + '/organisations/vat/%s/returns' % (
            vrn
        )

        resp = requests.post(url, headers=headers,
                             data=json.dumps(rtn.to_dict()))
        if resp.status_code != 201:
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        if "code" in obj:
            raise RuntimeError(obj["message"])

        return obj

    # Get liabilities in time period
    def get_vat_liabilities(self, vrn, start, end):

        headers = self.build_fraud_headers()
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
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        return [Liability.from_dict(v) for v in obj["liabilities"]]

    # Get payments in time period
    def get_vat_payments(self, vrn, start, end):

        headers = self.build_fraud_headers()
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
            try:
                msg = resp.json()["message"]
            except:
                msg = "HTTP error %d" % resp.status_code
            raise RuntimeError(msg)

        obj = resp.json()

        return [
            Payment.from_dict(v) for v in obj["payments"]
        ]

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

