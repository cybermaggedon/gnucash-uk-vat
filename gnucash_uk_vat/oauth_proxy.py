
import asyncio
import hmac
import hashlib
import json
import os
import sys

import aiohttp
from aiohttp import web

from .crypto import encrypt_response


def verify_hash(secret, email, provided_hash):
    expected = hmac.new(
        secret.encode(), email.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, provided_hash)


class OAuthProxy:

    def __init__(self, client_id, client_secret, hmrc_auth_url,
                 verification_secret, hmrc_api_url=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.hmrc_auth_url = hmrc_auth_url
        self.hmrc_api_url = hmrc_api_url or hmrc_auth_url
        self.verification_secret = verification_secret

    async def auth_url(self, request):

        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(
                body=json.dumps({"error": "Invalid JSON"}),
                content_type="application/json",
            )

        email = body.get("email")
        h = body.get("hash")
        redirect_uri = body.get("redirect_uri")

        if not email or not h or not redirect_uri:
            raise web.HTTPBadRequest(
                body=json.dumps({"error": "Missing required field"}),
                content_type="application/json",
            )

        if not verify_hash(self.verification_secret, email, h):
            raise web.HTTPForbidden(
                body=json.dumps({"error": "Invalid verification hash"}),
                content_type="application/json",
            )

        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": "read:vat write:vat",
            "redirect_uri": redirect_uri,
        }

        from urllib.parse import urlencode
        url = self.hmrc_auth_url + "/oauth/authorize?" + urlencode(params)

        return web.json_response({"url": url})

    async def token(self, request):

        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(
                body=json.dumps({"error": "Invalid JSON"}),
                content_type="application/json",
            )

        email = body.get("email")
        h = body.get("hash")
        code = body.get("code")
        redirect_uri = body.get("redirect_uri")

        if not email or not h or not code or not redirect_uri:
            raise web.HTTPBadRequest(
                body=json.dumps({"error": "Missing required field"}),
                content_type="application/json",
            )

        if not verify_hash(self.verification_secret, email, h):
            raise web.HTTPForbidden(
                body=json.dumps({"error": "Invalid verification hash"}),
                content_type="application/json",
            )

        from urllib.parse import urlencode
        params = urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        })

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with aiohttp.ClientSession() as client:
            async with client.post(
                self.hmrc_api_url + "/oauth/token",
                headers=headers,
                data=params,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise web.HTTPBadGateway(
                        body=json.dumps({
                            "error": "HMRC rejected the token exchange",
                            "detail": text,
                        }),
                        content_type="application/json",
                    )
                result = await resp.json()

        encrypted = encrypt_response(
            result, email, self.verification_secret,
        )
        return web.json_response(encrypted)

    async def refresh(self, request):

        try:
            body = await request.json()
        except json.JSONDecodeError:
            raise web.HTTPBadRequest(
                body=json.dumps({"error": "Invalid JSON"}),
                content_type="application/json",
            )

        email = body.get("email")
        h = body.get("hash")
        refresh_token = body.get("refresh_token")

        if not email or not h or not refresh_token:
            raise web.HTTPBadRequest(
                body=json.dumps({"error": "Missing required field"}),
                content_type="application/json",
            )

        if not verify_hash(self.verification_secret, email, h):
            raise web.HTTPForbidden(
                body=json.dumps({"error": "Invalid verification hash"}),
                content_type="application/json",
            )

        from urllib.parse import urlencode
        params = urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        })

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with aiohttp.ClientSession() as client:
            async with client.post(
                self.hmrc_api_url + "/oauth/token",
                headers=headers,
                data=params,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise web.HTTPBadGateway(
                        body=json.dumps({
                            "error": "HMRC rejected the refresh request",
                            "detail": text,
                        }),
                        content_type="application/json",
                    )
                result = await resp.json()

        encrypted = encrypt_response(
            result, email, self.verification_secret,
        )
        return web.json_response(encrypted)

    def create_app(self):
        app = web.Application()
        app.router.add_post("/auth-url", self.auth_url)
        app.router.add_post("/token", self.token)
        app.router.add_post("/refresh", self.refresh)
        return app


def main():

    client_id = os.environ.get("HMRC_CLIENT_ID")
    client_secret = os.environ.get("HMRC_CLIENT_SECRET")
    hmrc_auth_url = os.environ.get("HMRC_AUTH_URL")
    hmrc_api_url = os.environ.get("HMRC_API_URL")
    verification_secret = os.environ.get("VERIFICATION_SECRET")

    missing = []
    if not client_id:
        missing.append("HMRC_CLIENT_ID")
    if not client_secret:
        missing.append("HMRC_CLIENT_SECRET")
    if not hmrc_auth_url:
        missing.append("HMRC_AUTH_URL")
    if not verification_secret:
        missing.append("VERIFICATION_SECRET")

    if missing:
        print(
            "Missing required environment variables: " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)

    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("HOST", "0.0.0.0")

    proxy = OAuthProxy(client_id, client_secret, hmrc_auth_url,
                       verification_secret, hmrc_api_url=hmrc_api_url)
    app = proxy.create_app()
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main()
