
# HMRC OAuth Proxy Service

Technical specification for a lightweight intermediary that brokers HMRC
OAuth token operations, removing the need for client-side application
credentials.

## Motivation

The current `gnucash-uk-vat` client authenticates directly with HMRC's
Making Tax Digital OAuth endpoints.  This requires each installation to hold
the HMRC-issued `client-id` and `client-secret` in its local
configuration -- credentials that HMRC prohibits from being shared publicly.

An intermediary service eliminates this requirement.  Application credentials
live on a single server; the client holds only its own per-user access and
refresh tokens.  The client source can be published freely.

This is an additive change.  The existing direct-authentication mechanism
remains available for users who have their own HMRC developer credentials.

## Architecture

The proxy service is a stateless HTTP service that holds the HMRC
application credentials and exposes three endpoints.  It adds credentials to
outbound requests, forwards them to HMRC, and relays responses to the
client.  It stores no per-user data.

The client's ongoing HMRC API usage (submitting VAT returns, checking
obligations, reading liabilities) continues to go directly to HMRC using
the bearer token.  The proxy is only involved in the OAuth token lifecycle.

### Flow

```
 Client                    Proxy                     HMRC
   |                         |                         |
   |  POST /auth-url         |                         |
   |  {email,hash,redir_uri} |                         |
   |------------------------>|                         |
   |                         |                         |
   |  HMRC auth URL          |                         |
   |<------------------------|                         |
   |                         |                         |
   |  User visits URL in browser, logs into HMRC       |
   |-------------------------------------------------->|
   |                         |                         |
   |  Redirect to localhost:9876?code=...              |
   |<--------------------------------------------------|
   |                         |                         |
   |  POST /token {code}     |                         |
   |------------------------>|                         |
   |                         |  + client credentials   |
   |                         |------------------------>|
   |                         |                         |
   |                         |  tokens                 |
   |                         |<------------------------|
   |  tokens                 |                         |
   |<------------------------|                         |
   |                         |                         |
   |  API calls (direct, using bearer token)           |
   |-------------------------------------------------->|
```

## Endpoint Specification

### `POST /auth-url`

Returns the HMRC OAuth authorization URL.  The proxy constructs this from
its stored `client-id` and the `redirect_uri` supplied by the client.

All parameters are sent in a JSON request body (POST) so that the email
address does not appear in URLs, server access logs, or CDN logs.

**Request body:**

```json
{
  "email": "user@example.com",
  "hash": "...",
  "redirect_uri": "http://localhost:9876"
}
```

| Field          | Type   | Description                                          |
|----------------|--------|------------------------------------------------------|
| `email`        | string | User's email address                                 |
| `hash`         | string | HMAC-SHA256 verification hash (see Verification)     |
| `redirect_uri` | string | The client's local OAuth redirect URI                |

**Response:**

```json
{
  "url": "https://www.tax.service.gov.uk/oauth/authorize?response_type=code&client_id=...&scope=read:vat+write:vat&redirect_uri=..."
}
```

**Errors:**

| Status | Condition                            |
|--------|--------------------------------------|
| `400`  | Missing required field               |
| `403`  | Missing or invalid verification hash |

### `POST /token`

Exchanges an authorization code for access and refresh tokens.  The proxy
validates the verification hash, then injects `client_id`, `client_secret`,
and `redirect_uri` before forwarding to HMRC.  The email, hash, and
client-supplied `redirect_uri` are not forwarded; the proxy uses
`redirect_uri` to construct the HMRC token request.

**Request body:**

```json
{
  "code": "a1b2c3d4e5f6...",
  "redirect_uri": "http://localhost:9876",
  "email": "user@example.com",
  "hash": "..."
}
```

| Field          | Type   | Description                                          |
|----------------|--------|------------------------------------------------------|
| `code`         | string | Authorization code from the HMRC redirect            |
| `redirect_uri` | string | Must match the URI used in the `/auth-url` request   |
| `email`        | string | User's email address                                 |
| `hash`         | string | HMAC-SHA256 verification hash (see Verification)     |

**Response:**

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 14400
}
```

**Errors:**

| Status | Condition                            |
|--------|--------------------------------------|
| `400`  | Missing required field               |
| `403`  | Missing or invalid verification hash |
| `502`  | HMRC rejected the token exchange     |

### `POST /refresh`

Refreshes an expired access token.  The proxy validates the verification
hash, then injects `client_id` and `client_secret` before forwarding to
HMRC.  The email and hash are not forwarded.

**Request body:**

```json
{
  "refresh_token": "...",
  "email": "user@example.com",
  "hash": "..."
}
```

| Field           | Type   | Description                                      |
|-----------------|--------|--------------------------------------------------|
| `refresh_token` | string | The refresh token to exchange                    |
| `email`         | string | User's email address                             |
| `hash`          | string | HMAC-SHA256 verification hash (see Verification) |

**Response:**

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 14400
}
```

**Errors:**

| Status | Condition                            |
|--------|--------------------------------------|
| `400`  | Missing `refresh_token`              |
| `403`  | Missing or invalid verification hash |
| `502`  | HMRC rejected the refresh request    |

## Verification

All three endpoints require an email address and a verification hash.
The hash is an HMAC-SHA256 digest computed with the shared secret as key
and the email address as message, hex-encoded:

```
hash = HMAC-SHA256(key=secret, msg=email).hexdigest()
```

In Python:

```python
import hmac, hashlib
h = hmac.new(secret.encode(), email.encode(), hashlib.sha256).hexdigest()
```

Requests with a missing or invalid hash are rejected with `403`.

The email and hash are validated by the proxy and not forwarded to HMRC.

## Client Changes

A new authentication mode is added alongside the existing direct mode.  The
choice is driven by configuration: when `proxy.email` is set, the client
uses the proxy service.  Otherwise the client authenticates directly
with HMRC using `application.client-id` and `application.client-secret`
as it does today.

### Configuration

```json
{
  "proxy": {
    "email": "user@example.com"
  }
}
```

| Field          | Required | Description                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| `proxy.email`  | yes      | User's email address.  Presence of this field activates proxy mode.         |
| `proxy.url`    | no       | Proxy service URL.  Defaults to `https://auth.prod.accountsmachine.io`.     |

When proxy mode is active, `application.client-id` and
`application.client-secret` are not required.  The `email` is used to
compute the verification hash sent with each proxy request.

### Affected code

Changes are confined to `hmrc.py`.  Three methods gain proxy-aware paths:

| Method                 | Current behaviour                      | Proxy behaviour                      |
|------------------------|----------------------------------------|--------------------------------------|
| `get_auth_url()`       | Builds URL locally using `client-id`   | Calls `POST /auth-url` on the proxy  |
| `get_auth_coro()`      | POSTs code + credentials to HMRC       | POSTs code to proxy `/token`         |
| `refresh_token_coro()` | POSTs refresh token + credentials to HMRC | POSTs refresh token to proxy `/refresh` |

The `AuthCollector` (localhost redirect listener), token storage in
`auth.json`, fraud-prevention headers, and all HMRC API calls remain
unchanged.

## Service Implementation

The proxy service lives in this repository alongside the client.  It is a
minimal async HTTP application -- a single Python module using `aiohttp`
(already a project dependency).  A `console_scripts` entrypoint is defined
in the package so the service can be launched directly after installation.

### Configuration

The service is configured via environment variables:

| Variable               | Purpose                                            |
|------------------------|----------------------------------------------------|
| `HMRC_CLIENT_ID`       | HMRC-issued OAuth client ID                        |
| `HMRC_CLIENT_SECRET`   | HMRC-issued OAuth client secret                    |
| `HMRC_AUTH_URL`        | Base URL for HMRC user-facing OAuth (browser login) |
| `HMRC_API_URL`         | Base URL for HMRC machine-to-machine API (optional; defaults to `HMRC_AUTH_URL`) |
| `VERIFICATION_SECRET`  | Shared secret for hash verification                |

HMRC uses separate domains for browser-facing auth and server-to-server API
calls.  `HMRC_AUTH_URL` is used to construct the authorization URL the user
visits; `HMRC_API_URL` is used for token exchange and refresh.  For the test
service both point to the same host, so `HMRC_API_URL` can be omitted.

| Environment | `HMRC_AUTH_URL`                           | `HMRC_API_URL`                            |
|-------------|-------------------------------------------|-------------------------------------------|
| Production  | `https://www.tax.service.gov.uk`          | `https://api.service.hmrc.gov.uk`         |
| Sandbox     | `https://test-www.tax.service.gov.uk`     | `https://test-api.service.hmrc.gov.uk`    |

### Deployment

The service is stateless and requires no database, no filesystem access,
and no persistent storage.  It handles only token-lifecycle traffic -- a low
request volume per user (one authorization, then periodic refreshes).  Any
hosting platform that serves HTTPS is suitable.

### HTTPS

The proxy must be served over TLS.  The client will refuse to send
verification hashes or relay authorization codes over plain HTTP.

## Security Considerations

- The proxy sees authorization codes and tokens in transit.  Codes are
  single-use and short-lived; tokens are relayed, not stored.
- Application credentials (`client-id`, `client-secret`) never leave the
  proxy service.
- All endpoints are guarded by verification hash.  Rate limiting should
  also be applied at the infrastructure level.
- All communication between client and proxy must use HTTPS.

## Testing

The existing `test_service.py` mock HMRC server provides the OAuth
endpoints the proxy will call.  Integration tests for the proxy can run
against this mock in the same way the client's integration tests do today.

Contract tests should verify that the proxy's requests to HMRC match the
format specified in the existing `test_oauth_contract.py` suite.

The client's proxy-mode paths should be tested using a mock proxy service,
verifying that the client correctly delegates token operations and handles
error responses.
