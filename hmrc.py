
from urllib.parse import urlencode, quote_plus
import aiohttp
import aiohttp.web
import time
import asyncio
from datetime import datetime, timedelta, date
import requests
import json

box = [
    
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

class AuthCollector:

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.running = True
        self.result = None

    async def run(self):

        async def handler(req):

            if self.result == None:
                self.result = {
                    v: req.query[v]
                    for v in req.query
                }

            self.running = False

            return aiohttp.web.Response(
                body='Token received.',
                content_type="text/html"
            )

        server = aiohttp.web.Server(handler)
        runner = aiohttp.web.ServerRunner(server)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, self.host, self.port)
        await site.start()

        start = time.time()

        while self.running:
            await asyncio.sleep(0.2)

        await site.stop()
        await runner.cleanup()

        return self.result

class HmrcTest:
    def __init__(self, config, auth):
        self.config = config
        self.auth = auth
        self.oauth_base = 'https://test-www.tax.service.gov.uk'
        self.api_base = 'https://test-api.service.hmrc.gov.uk'

    def get_code(self):
        return asyncio.run(self.get_code_coro())

    async def get_code_coro(self):

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

        print("Please visit the following URL and authenticate:")
        print(url)

        a = AuthCollector("localhost", 9876)
        res = await a.run()

        if "error" in res:
            raise RuntimeError(str(res))

        code = res["code"]

        return code

    def get_auth(self, code):
        auth = asyncio.run(self.get_auth_coro(code))
        self.auth.auth = auth

    async def get_auth_coro(self, code):

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


    def refresh_token(self, refresh):
        return asyncio.run(self.refresh_token_coro(refresh))

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

    def get_fraud_headers(self):
        return {
            'Gov-Client-Connection-Method': 'OTHER_DIRECT',
            'Gov-Client-Device-ID': 'abb03181-0664-4a4d-8ddd-fc69b2d577d7',
            'Gov-Client-User-Ids': 'os=fjbloggs',
            'Gov-Client-Timezone': 'UTC+00:00',
            'Gov-Client-Local-IPs': '10.0.2.15',
            'Gov-Client-MAC-Addresses': '02:53:4a:6d:8c:85'.replace(":", "%3A"),
            'Gov-Client-User-Agent': 'Linux/5.8.7-200.fc32.x86_64 (Intel/x686)',
            'Gov-Client-Multi-Factor': 'type=OTHER&timestamp=2017-04-21T13%3A23Z&unique-reference=fbloggs',
            'Gov-Vendor-Version': 'my-application=1.7.0',
            'Gov-Vendor-License-IDs': 'gnu=e0d2747b9ab7abb6eb65e0373fa1b428a28bd6d8a2380106dcc080f58005ee14',
            'Authorization': 'Bearer %s' % self.auth.get("access_token"),
        }

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

        obj = resp.json()

        if "obligations" not in obj:
            raise RuntimeError(obj["message"])

        for v in obj["obligations"]:
            v["start"] = date.fromisoformat(v["start"])
            v["end"] = date.fromisoformat(v["end"])
            v["due"] = date.fromisoformat(v["due"])

        return obj["obligations"]

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

    def get_vat_return(self, vrn, period):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        params = {
            "periodKey": period
        }

        url = self.api_base + '/organisations/vat/%s/returns/%s' % (
            vrn, period
        )

        resp = requests.get(url, headers=headers)

        obj = resp.json()

        if "code" in obj:
            raise RuntimeError(obj["message"])

        return obj

    def submit_vat_return(self, vrn, rtn):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'

        url = self.api_base + '/organisations/vat/%s/returns' % (
            vrn
        )

        resp = requests.post(url, headers=headers, data=json.dumps(rtn))

        obj = resp.json()

        if "code" in obj:
            raise RuntimeError(obj["message"])

        return obj

    def get_vat_liabilities(self, vrn, start, end):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'
#        headers['Gov-Test-Scenario'] = 'MULTIPLE_LIABILITIES'

        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }

        url = self.api_base + '/organisations/vat/%s/liabilities?%s' % (
            vrn,
            urlencode(params)
        )

        resp = requests.get(url, headers=headers)

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

    def get_vat_payments(self, vrn, start, end):

        headers = self.get_fraud_headers()
        headers['Accept'] = 'application/vnd.hmrc.1.0+json'
        headers['Gov-Test-Scenario'] = 'MULTIPLE_PAYMENTS'

        params = {
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d")
        }

        url = self.api_base + '/organisations/vat/%s/payments?%s' % (
            vrn,
            urlencode(params)
        )

        resp = requests.get(url, headers=headers)

        obj = resp.json()

        if "payments" not in obj:
            raise RuntimeError(obj["message"])

        for v in obj["payments"]:
            if "received" in v:
                v["received"] = date.fromisoformat(v["received"])

        return obj["payments"]
