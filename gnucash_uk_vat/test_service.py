#!/usr/bin/env python3

"""
VAT Test Service CLI
"""

import asyncio
from aiohttp import web
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
import sys
import argparse
from urllib.parse import urlencode, quote_plus
import secrets
import copy
from typing import Optional, Dict, Any, Union

from .model import *

class Api:

    def __init__(self, template: Any, listen: str = "0.0.0.0:8080",
                 username: Optional[str] = None, password: Optional[str] = None,
                 headers: bool = False, secret: Optional[str] = None) -> None:
        self.listen = listen
        self.template = template
        self.data: Dict[str, Any] = {}
        self.headers = headers
        self.username = username
        self.password = password

        self.captured_headers: Dict[str, str] = {}

        # This is a test service, secrets here are for testing that clients
        # handle secrets properly.  Nobody should be using this service
        # with real data.
        if secret == None:
            self.secret = "1KGHk9KDMCjAu0Sr"
        else:
            self.secret = secret

        self.refresh_token = "67890"

        self.access_token = self.secret

    def handle_headers(self, request) -> None:

        if self.headers: 
            for k in  request.headers:
                print("%s: %s" % (k, request.headers[k]))
            print()

        for k in  request.headers:
            if k.lower().startswith("gov-"):
                self.captured_headers[k] = request.headers[k]

    async def get_headers(self, request):

        return web.json_response(self.captured_headers)

    def fab_data(self, dt: str) -> Any:

        dt_parsed = datetime.strptime(dt, "%d%m%y").date()

        # Create:
        # Open obligations for period starting dt, and following period
        # Filed obligations for previous two periods
        # Payments for the first of those periods
        # Liabilty for the second of those periods

        # FIXME: This treats 1 month = 30 days, VAT return periods are really
        # calendar months
        
        p1s = dt_parsed - timedelta(days=210)
        p1e = p1s + timedelta(days=90)
        p1d = p1e + timedelta(days=30)
        p1p = p1d - timedelta(days=5)

        p2s = p1s + timedelta(days=90)
        p2e = p2s + timedelta(days=90)
        p2d = p2e + timedelta(days=30)
        p2p = p2d - timedelta(days=5)

        p3s = p2s + timedelta(days=90)
        p3e = p3s + timedelta(days=90)
        p3d = p3e + timedelta(days=30)
        p3p = p3d - timedelta(days=5)

        p4s = p3s + timedelta(days=90)
        p4e = p4s + timedelta(days=90)
        p4d = p4e + timedelta(days=30)
        p4p = p4d - timedelta(days=5)

        rec = {
            "payments": [
                {
                    "amount": 123.45,
                    "received": p1p.isoformat()
                }
            ],
            "liabilities": [
                {
                    "type": "Net VAT",
                    "originalAmount": 1100,
                    "taxPeriod": {
                        "from": p1s.isoformat(),
                        "to": p1e.isoformat(),
                    },
                    "due": p1d.isoformat(),
                },
                {
                    "type": "Net VAT",
                    "originalAmount": 1100,
                    "outstandingAmount": 1100,
                    "taxPeriod": {
                        "from": p2s.isoformat(),
                        "to": p2e.isoformat(),
                    },
                    "due": p2d.isoformat(),
                },
            ],
            "returns": [
                {
                    "periodKey": "#000",
                    "vatDueSales": 100,
                    "vatDueAcquisitions": 120,
                    "totalVatDue": 220,
                    "vatReclaimedCurrPeriod": 30,
                    "netVatDue": 180,
                    "totalValueSalesExVAT": 1000,
                    "totalValuePurchasesExVAT": 1200,
                    "totalValueGoodsSuppliedExVAT": 50,
                    "totalAcquisitionsExVAT": 30
                },
                {
                    "periodKey": "#001",
                    "vatDueSales": 100,
                    "vatDueAcquisitions": 120,
                    "totalVatDue": 220,
                    "vatReclaimedCurrPeriod": 30,
                    "netVatDue": 180,
                    "totalValueSalesExVAT": 1000,
                    "totalValuePurchasesExVAT": 1200,
                    "totalValueGoodsSuppliedExVAT": 50,
                    "totalAcquisitionsExVAT": 30
                },
            ],
            "obligations": [
                {
                    "status": "F",
                    "periodKey": "#000",
                    "start": p1s.isoformat(),
                    "end": p1e.isoformat(),
                    "received": p1p.isoformat(),
                    "due": p1d.isoformat(),
                },
                {
                    "status": "F",
                    "periodKey": "#002",
                    "start": p2s.isoformat(),
                    "end": p2e.isoformat(),
                    "received": p2p.isoformat(),
                    "due": p2d.isoformat(),
                },
                {
                    "status": "O",
                    "periodKey": "#003",
                    "start": p3s.isoformat(),
                    "end": p3e.isoformat(),
                    "due": p3d.isoformat(),
                },
                {
                    "status": "O",
                    "periodKey": "#004",
                    "start": p4s.isoformat(),
                    "end": p4e.isoformat(),
                    "due": p4d.isoformat(),
                },
            ]
        }

        rec = { "record": rec }
        return VATData.from_dict(rec).data["record"]


    def get_data(self, vrn: str) -> Any:

        if vrn not in self.data:

            # There are magic code VRNs which encode a data, and the
            # VAT data is built around that date.
            # Format is 999ddmmyy

            if str(vrn)[0:3] == "999":

                dt = str(vrn)[3:]

                if len(dt) == 6:
                    self.data[vrn] = self.fab_data(dt)
                    return self.data[vrn]

            self.data[vrn] = copy.deepcopy(self.template)

        return self.data[vrn]

    def check_auth(self, request) -> None:
        try:

            tok = request.headers["Authorization"].split(" ")
            if tok[0] != "Bearer":
                raise web.HTTPUnauthorized()
            if tok[1] != self.access_token:
                raise web.HTTPUnauthorized()
        except:
            raise web.HTTPUnauthorized()

    async def get_return(self, request):

        self.check_auth(request)

        self.handle_headers(request)

        key = request.match_info["periodKey"]
        vrn = request.match_info["vrn"]

        user = self.get_data(vrn)

        for v in user.returns:
            if v.periodKey == key:
                return web.Response(
                    body=json.dumps(v.to_dict(), indent=4),
                    content_type="application/json"
                )

        raise web.HTTPBadRequest()

    async def get_fraud_validate(self, request):

        self.check_auth(request)

        self.handle_headers(request)

        return web.Response(
            body=json.dumps({}) + "\n",
            content_type="application/json"
        )

    async def get_obligations(self, request):

        self.check_auth(request)

        self.handle_headers(request)

        start=None
        end=None
        status=None
        vrn = request.match_info["vrn"]

        try:
            start = datetime.fromisoformat(request.query["from"]).date()
        except:
            pass

        try:
            end = datetime.fromisoformat(request.query["to"]).date()
        except:
            pass

        try:
            status = request.query["status"]
        except:
            pass

        try:
            obls = self.get_data(vrn).obligations
        except:
            raise web.HTTPBadRequest()

        if start and end:
            obls = [
                v for v in obls
                if v.in_range(start, end)
            ]

        if status:
            obls = [
                v for v in obls
                if v.status == status
            ]

        resp = {
            "obligations": [
                v.to_dict()
                for v in obls
            ]
        }

        return web.Response(
            body=json.dumps(resp, indent=4) + "\n",
            content_type="application/json"
        )

    async def get_liabilities(self, request):

        self.check_auth(request)

        self.handle_headers(request)

        try:
            start = datetime.fromisoformat(request.query["from"]).date()
            end = datetime.fromisoformat(request.query["to"]).date()
        except:
            raise web.HTTPBadRequest()

        vrn = request.match_info["vrn"]

        liabilities = self.get_data(vrn).liabilities

        resp = {
            "liabilities": [
                v.to_dict() for v in liabilities
                if v.in_range(start, end)
            ]
        }

        return web.Response(
            body=json.dumps(resp, indent=4) + "\n",
            content_type="application/json"
        )

    async def get_payments(self, request):

        self.check_auth(request)

        self.handle_headers(request)

        try:
            start = datetime.fromisoformat(request.query["from"]).date()
            end = datetime.fromisoformat(request.query["to"]).date()
        except:
            raise web.HTTPBadRequest()

        vrn = request.match_info["vrn"]

        payments = self.get_data(vrn).payments

        resp = {
            "payments": [
                v.to_dict() for v in payments
                if v.in_range(start, end)
            ]
        }

        return web.Response(
            body=json.dumps(resp, indent=4) + "\n",
            content_type="application/json"
        )

    async def submit_return(self, request):

        self.check_auth(request)

        self.handle_headers(request)

        body = await request.json()

        rtn =  Return.from_dict(body)

        if not rtn.finalised:
            raise web.HTTPBadRequest()

        vrn = request.match_info["vrn"]

        self.get_data(vrn).add_return(rtn)

        resp = {
            "processingDate": datetime.now(timezone.utc).isoformat(),
            "paymentIndicator": "BANK",
            "formBundleNumber": str(uuid.uuid1()),
            "chargeRefNumber": str(uuid.uuid1()),
        }

        return web.HTTPCreated(
            body=json.dumps(resp, indent=4).encode("utf-8"),
            content_type="application/json"
        )

    async def get_token(self, request):

        data = await request.post()
        grant = data['grant_type']
        
        # Validate client credentials for all grant types
        client_id = data.get('client_id', '')
        client_secret = data.get('client_secret', '')
        
        # For testing, accept specific test client credentials
        valid_client_id = "test-client-id"
        valid_client_secret = "test-client-secret"
        
        if client_id != valid_client_id or client_secret != valid_client_secret:
            raise web.HTTPUnauthorized()

        if grant == "refresh_token":
            if data["refresh_token"] != self.refresh_token:
                raise web.HTTPUnauthorized()
            token = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_type": "bearer",
                "expires_in": 1440
            }

        elif grant == "authorization_code":

            code = data['code']
            if code != self.code:
                raise web.HTTPUnauthorized()

            token = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "token_type": "bearer",
                "expires_in": 1440
            }

        else:

            raise web.HTTPUnauthorized()

        return web.Response(
            body=json.dumps(token, indent=4) + "\n",
            content_type="application/json"
        )

    async def authorize(self, request):

        try:
            client_id = request.query["client_id"]
            scope = request.query["scope"]
            redirect = request.query["redirect_uri"]
        except:
            raise web.HTTPBadRequest()

        state=""

        try:
            state = request.query["state"]
        except:
            pass

        page = """
<html>
  <body>
    <h1>Test system, don't enter real creds in here</h1>
    <form action="/oauth/login" method="get">
      <p>Creds are ignored anyway, just press submit.</p>
      <div>
	<label for="username">Username</label>
	<input name="username" type="text">
      </div>
      <div>
	<label for="password">Password</label>
	<input name="password" type="password">
      </div>
      <input name="client_id" type="hidden" value="%s">
      <input name="state" type="hidden" value="%s">
      <input name="scope" type="hidden" value="%s">
      <input name="redirect_uri" type="hidden" value="%s">
      <button type="submit">Submit</button>
    </form>
  </body>
</html>
""" % (client_id, state, scope, redirect)

        return web.Response(body=page, content_type="text/html")

    async def login(self, request):

        try:
            client_id = request.query["client_id"]
            scope = request.query["scope"]
            redirect = request.query["redirect_uri"]
        except:
            raise web.HTTPBadRequest()

        try:
            username = request.query["username"]
        except:
            username = None

        try:
            password = request.query["password"]
        except:
            password = None

        if self.username != None and self.username != username:
            raise web.HTTPUnauthorized()

        if self.password != None and self.password != password:
            raise web.HTTPUnauthorized()

        state=""

        try:
            state = request.query["state"]
        except:
            pass

        self.code = secrets.token_hex(16)

        resp = {
            'code': self.code,
        }

        if state != "":
            resp["state"] = state

        url = redirect + "?" + urlencode(resp, quote_via=quote_plus)

        print("Redirect to")
        print(url)

        raise web.HTTPFound(url)

    async def run(self) -> None:

        app = web.Application()

        app.router.add_get('/oauth/authorize', self.authorize)
        app.router.add_get('/oauth/login', self.login)
        app.router.add_post('/oauth/token', self.get_token)
        app.router.add_get('/test/fraud-prevention-headers/validate',
                           self.get_fraud_validate)
        app.router.add_get('/organisations/vat/{vrn}/obligations',
                           self.get_obligations)
        app.router.add_get('/organisations/vat/{vrn}/liabilities',
                           self.get_liabilities)
        app.router.add_get('/organisations/vat/{vrn}/payments',
                           self.get_payments)
        app.router.add_get('/organisations/vat/{vrn}/returns/{periodKey}',
                           self.get_return)
        app.router.add_post('/organisations/vat/{vrn}/returns',
                            self.submit_return)
        app.router.add_get('/captured-headers', self.get_headers)

        runner = web.AppRunner(app)
        await runner.setup()

        host = self.listen.split(":", 2)

        site = web.TCPSite(runner, host[0], int(host[1]))
        await site.start()

        while True:
            await asyncio.sleep(1)

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for vat-test-service."""
    parser = argparse.ArgumentParser(description="Gnucash to HMRC VAT API")
    parser.add_argument('--listen', '-l',
                default='localhost:8080',
                        help='Host/port to listen on (default: localhost:8080)')
    parser.add_argument('--data', '-d',
                default='vat-data.json',
                        help='Data file to load at init (default: vat-data.json)')
    parser.add_argument('--dump-headers', '-H', action='store_true',
                        help='Whether to dump headers')
    parser.add_argument('--username', '-u',
                        help='Enables authentication with the specified username')
    parser.add_argument('--password', '-p',
                        help='Enables authentication with the specified password')
    parser.add_argument('--secret', '-S',
                        help='A key used to seed token generation, default hard-coded')
    return parser

def main() -> None:
    """Main entry point for vat-test-service."""
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])

    data = open(args.data).read()
    template = VATData.from_json(data).data["TEMPLATE"]
    a = Api(template, args.listen, headers=args.dump_headers,
            username=args.username, password=args.password, secret=args.secret)

    loop = asyncio.run(a.run())

if __name__ == "__main__":
    main()