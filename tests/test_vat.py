
import pytest

from gnucash_uk_vat.hmrc import Vat
from gnucash_uk_vat.model import Liability
import datetime
from urllib.parse import urlencode, quote_plus
import hashlib
import json
import aiohttp

example_client_id = "09198fncaw9890"
example_mac_address = "01:23:45:67:89:ab"
example_os_family = "Aardvark Bunches"
example_os_version = "1.23.5.15-12312.515"
example_device_manufacturer = "Aardvark Limited"
example_device_model = "Turtledove Power Buncher"
example_device_id = "lasueno9l2nx987[n"
example_product_name = "gnucash-UK-vAt"
example_product_version = "12.412.41.251"
example_user = "fred-bloggs"
example_local_ip = "89.42.61.251"
example_identity_time = datetime.datetime.fromisoformat("2045-03-30T15:34:51Z")
example_access_token = "l1kj23k1j31k2hu31k2hj3lkl12j3j123jklk23jl12k3j"

example_start = datetime.date.fromisoformat("2019-04-06")
example_end = datetime.date.fromisoformat("2023-12-29")
example_vrn = "918273645"

example_liabilities = {
    "liabilities": [
        {
            "taxPeriod": {
                "from": "2021-09-12",
                "to": "2051-11-30",
            },
            "type": "asd",
            "originalAmount": 11414.45,
            "outstandingAmount": 4124.91,
            "due": "2026-04-12",
        },
        {
            "taxPeriod": {
                "from": "2041-09-12",
                "to": "2071-11-30",
            },
            "type": "asd",
            "originalAmount": 11414.45,
            "outstandingAmount": 4124.91,
            "due": "2046-04-12",
        }
    ]
}

example_config = {
    "application.client-id": example_client_id,
    "identity.mac-address": example_mac_address,
    "identity.device.os-family": example_os_family,
    "identity.device.os-version": example_os_version,
    "identity.device.device-manufacturer": example_device_manufacturer,
    "identity.device.device-model": example_device_model,
    "identity.device.id": example_device_id,
    "application.product-name": example_product_name,
    "application.product-version": example_product_version,
    "identity.user": example_user,
    "identity.local-ip": example_local_ip,
    "identity.time": str(example_identity_time),
}

example_auth = {
    "access_token": example_access_token,
}

expected_ua = urlencode({
    "os-family": example_os_family,
    "os-version": example_os_version,
    "device-manufacturer": example_device_manufacturer,
    "device-model": example_device_model,
})

expected_headers={
    'Gov-Client-Connection-Method': 'OTHER_DIRECT',
    'Gov-Client-Device-ID': 'lasueno9l2nx987[n',
    'Gov-Client-User-Ids': 'os=fred-bloggs',
    'Gov-Client-Timezone': 'UTC+00:00',
    'Gov-Client-Local-IPs': '89.42.61.251',
    'Gov-Client-Local-IPs-Timestamp': '2045-03-30 15:34:51+00:00',
    'Gov-Client-MAC-Addresses': '01%3A23%3A45%3A67%3A89%3Aab',
    'Gov-Client-User-Agent': 'os-family=Aardvark+Bunches&os-version=1.23.5.15-12312.515&device-manufacturer=Aardvark+Limited&device-model=Turtledove+Power+Buncher',
    'Gov-Vendor-Version': 'gnucash-UK-vAt=12.412.41.251',
    'Gov-Vendor-Product-Name': 'gnucash-UK-vAt',
    'Gov-Vendor-License-Ids': 'gnucash-UK-vAt=c56950db1ed4422dd0a597779b4362613e6aee57',
    'Gov-Client-Multi-Factor': '',
    'Authorization': 'Bearer l1kj23k1j31k2hu31k2hj3lkl12j3j123jklk23jl12k3j',
}

def test_url():

    vat = Vat(example_config, example_auth)

    url = vat.get_auth_url()

    assert(url == f"https://www.tax.service.gov.uk/oauth/authorize?response_type=code&client_id={example_client_id}&scope=read%3Avat+write%3Avat&redirect_uri=http%3A%2F%2Flocalhost%3A9876%2Fauth")

def test_fraud_headers():

    vat = Vat(example_config, example_auth)

    headers = vat.build_fraud_headers()

    hashed_license_id = hashlib.sha1(b'GPL3').hexdigest()

    assert(headers['Gov-Client-Connection-Method'] == 'OTHER_DIRECT')
    assert(headers['Gov-Client-Device-ID'] == example_device_id)

    assert(headers['Gov-Client-User-Ids'] == f'os={example_user}')
    assert(headers['Gov-Client-Timezone'] == 'UTC+00:00')
    assert(headers['Gov-Client-Local-IPs'] == example_local_ip)
    assert(headers['Gov-Client-Local-IPs-Timestamp'] == str(example_identity_time))
    assert(
        headers['Gov-Client-MAC-Addresses'] ==
        quote_plus(example_mac_address)
    )
    assert(headers['Gov-Client-User-Agent'] == expected_ua)

    assert(
        headers['Gov-Vendor-Version'] ==
        '%s=%s' % (example_product_name, example_product_version)
    )

    assert(headers['Gov-Vendor-Product-Name'] == '%s' % example_product_name)

    assert(
        headers['Gov-Vendor-License-Ids'] ==
        '%s=%s' % (example_product_name, hashed_license_id )
    )

    assert(headers['Gov-Client-Multi-Factor'] == '')
    assert(headers['Authorization'] == f"Bearer {example_access_token}")

    # What's the point of the above?  This tests just as well
    assert(headers == expected_headers)

@pytest.mark.asyncio    
async def test_get_vat_liabilities(mocker):

    vat = Vat(example_config, example_auth)

    class MockResponse:
        def __init__(self, text, status):
            self.obj = text
            self.status = status

        async def text(self):
            return json.dumps(self.obj)

        async def json(self):
            return self.obj

        async def __aexit__(self, exc_type, exc, tb):
            pass

        async def __aenter__(self):
            return self

    resp = MockResponse(example_liabilities, 200)

    mocker.patch('aiohttp.ClientSession.get', return_value=resp)

    liabs = await vat.get_vat_liabilities(
        example_vrn, example_start, example_end
    )

    aiohttp.ClientSession.get.assert_called_once_with(
        "https://api.service.hmrc.gov.uk/organisations/vat/918273645/liabilities?from=2019-04-06&to=2023-12-29",
        headers={
            'Gov-Client-Connection-Method': 'OTHER_DIRECT',
            'Gov-Client-Device-ID': 'lasueno9l2nx987[n',
            'Gov-Client-User-Ids': 'os=fred-bloggs',
            'Gov-Client-Timezone': 'UTC+00:00',
            'Gov-Client-Local-IPs': '89.42.61.251',
            'Gov-Client-Local-IPs-Timestamp': '2045-03-30 15:34:51+00:00',
            'Gov-Client-MAC-Addresses': '01%3A23%3A45%3A67%3A89%3Aab',
            'Gov-Client-User-Agent': 'os-family=Aardvark+Bunches&os-version=1.23.5.15-12312.515&device-manufacturer=Aardvark+Limited&device-model=Turtledove+Power+Buncher',
            'Gov-Vendor-Version': 'gnucash-UK-vAt=12.412.41.251',
            'Gov-Vendor-Product-Name': 'gnucash-UK-vAt',
            'Gov-Vendor-License-Ids': 'gnucash-UK-vAt=c56950db1ed4422dd0a597779b4362613e6aee57',
            'Gov-Client-Multi-Factor': '',
            'Authorization': 'Bearer l1kj23k1j31k2hu31k2hj3lkl12j3j123jklk23jl12k3j',
            'Accept': 'application/vnd.hmrc.1.0+json'
        }
    )

    assert(
        str(liabs[0].start) ==
        example_liabilities["liabilities"][0]["taxPeriod"]["from"]
    )

    assert(
        str(liabs[0].end) ==
        example_liabilities["liabilities"][0]["taxPeriod"]["to"]
    )


    assert(
        str(liabs[0].typ) ==
        example_liabilities["liabilities"][0]["type"]
    )

    assert(
        liabs[0].original ==
        example_liabilities["liabilities"][0]["originalAmount"]
    )

    assert(
        liabs[0].outstanding ==
        example_liabilities["liabilities"][0]["outstandingAmount"]
    )

    assert(
        str(liabs[0].due) ==
        example_liabilities["liabilities"][0]["due"]
    )

