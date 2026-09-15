
# Test VAT service

There is a test service which serves test data.  (See
`vat-data.json` in the source tree for an example.  The test service (roughly)
conforms to the HMRC VAT API.  The VRN in `vat-data.json` is `1234567890`.

## Direct mode

In direct mode, the client talks directly to the test service using
dummy credentials.

Start the test service:

```
vat-test-service
```

Set the configuration to use the local test service:

```json
{
    "application": {
        "profile": "local",
        "client-id": "test-client-id",
        "client-secret": "test-client-secret"
    },
    "identity": {
        "vrn": "1234567890"
    }
}
```

This will cause the client to use `http://localhost:8080` for the VAT
service.  You should then use the service as normal, including
authenticating.  The authentication mechanism is there, but dummy
credentials are issued, and nothing is verified.

## Proxy mode

In proxy mode, the client talks to a local OAuth proxy which forwards
token operations to the test service.  This exercises the same code
path used in production with the hosted proxy.

You need three terminals:

**Terminal 1** -- start the test service on port 8081:

```
vat-test-service --listen localhost:8081
```

**Terminal 2** -- start the OAuth proxy on port 8080:

```
export HMRC_CLIENT_ID=test-client-id
export HMRC_CLIENT_SECRET=test-client-secret
export HMRC_AUTH_URL=http://localhost:8081
export VERIFICATION_SECRET=verification
vat-oauth-proxy
```

**Terminal 3** -- run the client:

```
gnucash-uk-vat -c config-local.json -a auth-local.json --authenticate
gnucash-uk-vat -c config-local.json -a auth-local.json --show-open-obligations
```

The client configuration for proxy mode should include:

```json
{
    "application": {
        "profile": "local"
    },
    "identity": {
        "vrn": "1234567890"
    },
    "proxy": {
        "url": "http://localhost:8080",
        "email": "test@example.com"
    }
}
```

The `proxy.email` field activates proxy mode.  The `proxy.url` points
to the local proxy rather than the production default.
