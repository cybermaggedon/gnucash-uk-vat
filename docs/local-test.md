
# Test VAT service

There is a test service which serves test data.  (See
`vat-data.json` in the source tree for an example.  The test service (roughly)
conforms to the HMRC VAT API.  The VRN is `vat-data.json` is `1234567890`.

You would run it thus:

```
./test-vat-service -d vat-data.json
```

To invoke the test service, change the configuration file:

```
{
    ...
    "application": {
        ...
	"profile": "local"
	...
    },
    "identity": {
        "vrn": "1234567890",
	...
    }
```

This will cause the adaptor to use `http://localhost:8080` for the VAT service.

You should then use the service as above, including authenticating.
The authentication mechanism is there, but dummy credentials are issued, and
nothing is verified.
