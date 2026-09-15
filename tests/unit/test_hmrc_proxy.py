
import pytest
import pytest_asyncio
import json
import hmac
import hashlib
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from gnucash_uk_vat.hmrc import Vat
from gnucash_uk_vat.crypto import encrypt_response


PROXY_URL = "http://localhost:8888"
PROXY_EMAIL = "user@example.com"
PROXY_SECRET = "test-secret"


def make_config(proxy=True):
    cfg = MagicMock()
    values = {}

    if proxy:
        values.update({
            "proxy.url": PROXY_URL,
            "proxy.email": PROXY_EMAIL,
            "proxy.secret": PROXY_SECRET,
        })
    else:
        values.update({
            "proxy.url": None,
            "application.client-id": "cid",
            "application.client-secret": "csecret",
        })

    cfg.get = lambda key, **kwargs: values.get(key)
    return cfg


def make_auth():
    auth = MagicMock()
    auth.get = lambda key: {
        "access_token": "tok",
        "refresh_token": "ref",
    }.get(key)
    return auth


class TestIsProxyMode:

    def test_proxy_mode_when_proxy_url_set(self):
        vat = Vat(make_config(proxy=True), make_auth())
        assert vat._is_proxy_mode()

    def test_direct_mode_when_no_proxy_url(self):
        vat = Vat(make_config(proxy=False), make_auth())
        assert not vat._is_proxy_mode()


class TestComputeHash:

    def test_hash_is_hmac_sha256(self):
        vat = Vat(make_config(proxy=True), make_auth())
        expected = hmac.new(
            PROXY_SECRET.encode(), PROXY_EMAIL.encode(), hashlib.sha256
        ).hexdigest()
        assert vat._compute_hash() == expected


class TestGetAuthUrlProxy:

    def test_calls_proxy(self):
        vat = Vat(make_config(proxy=True), make_auth())

        expected_url = "https://hmrc.example.com/oauth/authorize?foo=bar"

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"url": expected_url}
        ).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response) as m:
            url = vat.get_auth_url()

        assert url == expected_url
        call_args = m.call_args[0][0]
        assert call_args.full_url == PROXY_URL + "/auth-url"
        assert call_args.method == "POST"

        body = json.loads(call_args.data)
        assert body["email"] == PROXY_EMAIL
        assert "hash" in body
        assert body["redirect_uri"] == "http://localhost:9876/auth"


class TestGetAuthCoroProxy:

    @pytest.mark.asyncio
    async def test_exchanges_code_via_proxy(self):
        vat = Vat(make_config(proxy=True), make_auth())

        token_payload = {
            "access_token": "new-access",
            "refresh_token": "new-refresh",
            "token_type": "bearer",
            "expires_in": 14400,
        }
        encrypted = encrypt_response(token_payload, PROXY_EMAIL, PROXY_SECRET)

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = encrypted

        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_resp

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_ctx

        mock_cs = AsyncMock()
        mock_cs.__aenter__.return_value = mock_session

        with patch("aiohttp.ClientSession", return_value=mock_cs):
            result = await vat.get_auth_coro("test-code")

        assert result["access_token"] == "new-access"
        assert result["refresh_token"] == "new-refresh"
        assert result["token_type"] == "bearer"
        assert "expires" in result

        call_args = mock_session.post.call_args
        assert call_args[0][0] == PROXY_URL + "/token"
        body = call_args[1]["json"]
        assert body["code"] == "test-code"
        assert body["email"] == PROXY_EMAIL
        assert "hash" in body

    @pytest.mark.asyncio
    async def test_403_raises_runtime_error(self):
        vat = Vat(make_config(proxy=True), make_auth())

        mock_resp = AsyncMock()
        mock_resp.status = 403

        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_resp

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_ctx

        mock_cs = AsyncMock()
        mock_cs.__aenter__.return_value = mock_session

        with patch("aiohttp.ClientSession", return_value=mock_cs):
            with pytest.raises(RuntimeError, match="verification hash"):
                await vat.get_auth_coro("test-code")


class TestRefreshTokenCoroProxy:

    @pytest.mark.asyncio
    async def test_refreshes_via_proxy(self):
        vat = Vat(make_config(proxy=True), make_auth())

        token_payload = {
            "access_token": "refreshed-access",
            "refresh_token": "refreshed-refresh",
            "token_type": "bearer",
            "expires_in": 14400,
        }
        encrypted = encrypt_response(token_payload, PROXY_EMAIL, PROXY_SECRET)

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json.return_value = encrypted

        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_resp

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_ctx

        mock_cs = AsyncMock()
        mock_cs.__aenter__.return_value = mock_session

        with patch("aiohttp.ClientSession", return_value=mock_cs):
            result = await vat.refresh_token_coro("old-refresh-token")

        assert result["access_token"] == "refreshed-access"
        assert result["refresh_token"] == "refreshed-refresh"

        call_args = mock_session.post.call_args
        assert call_args[0][0] == PROXY_URL + "/refresh"
        body = call_args[1]["json"]
        assert body["refresh_token"] == "old-refresh-token"
        assert body["email"] == PROXY_EMAIL

    @pytest.mark.asyncio
    async def test_502_raises_runtime_error(self):
        vat = Vat(make_config(proxy=True), make_auth())

        mock_resp = AsyncMock()
        mock_resp.status = 502

        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_resp

        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_ctx

        mock_cs = AsyncMock()
        mock_cs.__aenter__.return_value = mock_session

        with patch("aiohttp.ClientSession", return_value=mock_cs):
            with pytest.raises(RuntimeError, match="refresh request"):
                await vat.refresh_token_coro("old-refresh-token")
