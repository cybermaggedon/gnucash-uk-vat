
import pytest
import pytest_asyncio
import json
import hmac
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock

from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, TestClient, TestServer

from gnucash_uk_vat.oauth_proxy import OAuthProxy, verify_hash


VERIFICATION_SECRET = "test-verification-secret"
TEST_EMAIL = "user@example.com"
CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"
HMRC_URL = "https://test-www.tax.service.gov.uk"


def compute_hash(secret, email):
    return hmac.new(
        secret.encode(), email.encode(), hashlib.sha256
    ).hexdigest()


VALID_HASH = compute_hash(VERIFICATION_SECRET, TEST_EMAIL)


class TestVerifyHash:

    def test_valid_hash(self):
        assert verify_hash(VERIFICATION_SECRET, TEST_EMAIL, VALID_HASH)

    def test_invalid_hash(self):
        assert not verify_hash(VERIFICATION_SECRET, TEST_EMAIL, "badhash")

    def test_wrong_email(self):
        assert not verify_hash(
            VERIFICATION_SECRET, "other@example.com", VALID_HASH
        )

    def test_wrong_secret(self):
        h = compute_hash("wrong-secret", TEST_EMAIL)
        assert not verify_hash(VERIFICATION_SECRET, TEST_EMAIL, h)


@pytest.fixture
def proxy():
    return OAuthProxy(CLIENT_ID, CLIENT_SECRET, HMRC_URL,
                      VERIFICATION_SECRET)


@pytest.fixture
def app(proxy):
    return proxy.create_app()


@pytest_asyncio.fixture
async def client(aiohttp_client, app):
    return await aiohttp_client(app)


class TestAuthUrl:

    @pytest.mark.asyncio
    async def test_returns_hmrc_url(self, client):
        resp = await client.post("/auth-url", json={
            "email": TEST_EMAIL,
            "hash": VALID_HASH,
            "redirect_uri": "http://localhost:9876/auth",
        })
        assert resp.status == 200
        data = await resp.json()
        url = data["url"]
        assert "oauth/authorize" in url
        assert f"client_id={CLIENT_ID}" in url
        assert "redirect_uri=http" in url

    @pytest.mark.asyncio
    async def test_invalid_hash_returns_403(self, client):
        resp = await client.post("/auth-url", json={
            "email": TEST_EMAIL,
            "hash": "invalid",
            "redirect_uri": "http://localhost:9876/auth",
        })
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_missing_field_returns_400(self, client):
        resp = await client.post("/auth-url", json={
            "email": TEST_EMAIL,
            "hash": VALID_HASH,
        })
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_missing_email_returns_400(self, client):
        resp = await client.post("/auth-url", json={
            "hash": VALID_HASH,
            "redirect_uri": "http://localhost:9876/auth",
        })
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_invalid_json_returns_400(self, client):
        resp = await client.post(
            "/auth-url",
            data=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_redirect_uri_included_in_url(self, client):
        resp = await client.post("/auth-url", json={
            "email": TEST_EMAIL,
            "hash": VALID_HASH,
            "redirect_uri": "http://localhost:5555/callback",
        })
        assert resp.status == 200
        data = await resp.json()
        assert "localhost%3A5555" in data["url"] or "localhost:5555" in data["url"]


class TestToken:

    @pytest.mark.asyncio
    async def test_missing_code_returns_400(self, client):
        resp = await client.post("/token", json={
            "email": TEST_EMAIL,
            "hash": VALID_HASH,
            "redirect_uri": "http://localhost:9876/auth",
        })
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_invalid_hash_returns_403(self, client):
        resp = await client.post("/token", json={
            "code": "testcode",
            "redirect_uri": "http://localhost:9876/auth",
            "email": TEST_EMAIL,
            "hash": "invalid",
        })
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_missing_email_returns_400(self, client):
        resp = await client.post("/token", json={
            "code": "testcode",
            "redirect_uri": "http://localhost:9876/auth",
            "hash": VALID_HASH,
        })
        assert resp.status == 400


class TestRefresh:

    @pytest.mark.asyncio
    async def test_missing_refresh_token_returns_400(self, client):
        resp = await client.post("/refresh", json={
            "email": TEST_EMAIL,
            "hash": VALID_HASH,
        })
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_invalid_hash_returns_403(self, client):
        resp = await client.post("/refresh", json={
            "refresh_token": "sometoken",
            "email": TEST_EMAIL,
            "hash": "invalid",
        })
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_missing_email_returns_400(self, client):
        resp = await client.post("/refresh", json={
            "refresh_token": "sometoken",
            "hash": VALID_HASH,
        })
        assert resp.status == 400
