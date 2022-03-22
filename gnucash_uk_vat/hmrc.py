
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
    async def start(self):

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
        self.server = aiohttp.web.Server(handler)
        self.runner = aiohttp.web.ServerRunner(self.server)
        await self.runner.setup()
        self.site = aiohttp.web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

    async def stop(self):

        # Close web server
        await self.site.stop()
        await self.runner.cleanup()

    async def run(self):

        await self.start()

        # Sleep until we have a result
        while self.running:
            await asyncio.sleep(0.2)

        await self.stop()

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
    async def get_code(self):
        return await self.get_code_coro()

    def get_auth_url(self):

        # Build request to OAUTH endpoint
        url = self.oauth_base + '/oauth/authorize'

        params = urlencode(
            {
                'response_type': 'code',
	        'client_id': self.config.get("application.client-id"),
                'scope': 'read:vat write:vat',
                'redirect_uri': 'http://localhost:9876/auth',
            }
        )

        return url + "?" + params

    # Co-routine implementation
    async def get_code_coro(self):

        url = self.get_auth_url()
        
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
    async def get_auth(self, code):
        auth = await self.get_auth_coro(code)
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
    async def refresh_token(self, refresh):
        return await self.refresh_token_coro(refresh)

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

        dev_os_fam = self.config.get("identity.device.os-family")
        dev_os_version = self.config.get("identity.device.os-version")
        dev_manuf = self.config.get("identity.device.device-manufacturer")
        dev_model = self.config.get("identity.device.device-model")
        dev_id = self.config.get("identity.device.id")

        if dev_os_fam == "":
            raise RuntimeError("identity.device.os-family not set")
        if dev_os_version == "":
            raise RuntimeError("identity.device.os-version not set")
        if dev_manuf == "":
            raise RuntimeError("identity.device.device-manufacturer not set")
        if dev_model == "":
            raise RuntimeError("identity.device.device-model not set")
        if dev_id == "":
            raise RuntimeError("identity.device.id not set")

        ua = urlencode({
            "os-family": dev_os_fam,
            "os-version": dev_os_version,
            "device-manufacturer": dev_manuf,
            "device-model": dev_model
        })

        # Return headers
        return {
            'Gov-Client-Connection-Method': 'OTHER_DIRECT',
            'Gov-Client-Device-ID': dev_id,
            'Gov-Client-User-Ids': 'os=%s' % self.config.get("identity.user"),
            # Batch code, we're doing everything in UTC
            'Gov-Client-Timezone': 'UTC+00:00',
            'Gov-Client-Local-IPs': self.config.get("identity.local-ip"),
            'Gov-Client-Local-IPs-Timestamp': self.config.get("identity.time"),
            'Gov-Client-MAC-Addresses': mac,
            'Gov-Client-User-Agent': ua,
            'Gov-Vendor-Version': 'gnucash-uk-vat=1.0',
            'Gov-Vendor-Product-Name': 'gnucash-uk-vat',
            'Authorization': 'Bearer %s' % self.auth.get("access_token"),
        }

    # Test fraud headers.  Only available in Sandbox, not production
    async def test_fraud_headers(self):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        url = self.api_base + '/test/fraud-prevention-headers/validate'

        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

        return obj

    # API request, fetch obligations which are in state O.
    async def get_open_obligations(self, vrn):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "status": "O"
        }

        url = self.api_base + '/organisations/vat/%s/obligations?%s' % (
            vrn,
            urlencode(params)
        )

        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        obligations = [
            Obligation.from_dict(v) for v in  obj["obligations"]
        ]

        return obligations

    # API request, fetch obligations which are in a time period.
    async def get_obligations(self, vrn, start=None, end=None):

        if start == None:
            start = datetime.utcnow() - timedelta(days=(2 * 356))

        if end == None:
            end = datetime.utcnow()

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

        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        return [
            Obligation.from_dict(v) for v in obj["obligations"]
        ]

    # API request, fetch a VAT return instance.
    async def get_vat_return(self, vrn, period):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "periodKey": period
        }

        url = self.api_base + '/organisations/vat/%s/returns/%s' % (
            vrn, quote_plus(period)
        )

        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

        return Return.from_dict(obj)

    # API request, submit a VAT return.
    async def submit_vat_return(self, vrn, rtn):

        headers = self.build_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        url = self.api_base + '/organisations/vat/%s/returns' % (
            vrn
        )

        async with aiohttp.ClientSession() as client:
            async with client.post(url, headers=headers,
                                   json=rtn.to_dict()) as resp:
                if resp.status != 201:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

        if "code" in obj:
            raise RuntimeError(obj["message"])

        return obj

    # Get liabilities in time period
    async def get_vat_liabilities(self, vrn, start, end):

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

        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

        return [Liability.from_dict(v) for v in obj["liabilities"]]

    # Get payments in time period
    async def get_vat_payments(self, vrn, start, end):

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

        async with aiohttp.ClientSession() as client:
            async with client.get(url, headers=headers) as resp:
                if resp.status != 200:
                    try:
                        msg = (await resp.json())["message"]
                    except:
                        msg = "HTTP error %d" % resp.status
                    raise RuntimeError(msg)

                obj = await resp.json()

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

def create(config, auth):

    # Get profile
    prof = config.get("application.profile")

    # Initialise API client endpoint based on selected profile
    if prof == "prod":
        return Vat(config, auth)
    elif prof == "test":
        return VatTest(config, auth)
    elif prof == "local":
        return VatLocalTest(config, auth)
    else:
        raise RuntimeError("Profile '%s' is not known." % prof)

