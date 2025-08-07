
import pytest

from gnucash_uk_vat.hmrc import Vat
from gnucash_uk_vat.model import Liability, Return
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
example_identity_time = datetime.datetime.fromisoformat("2045-03-30T15:34:51.123Z")
example_access_token = "l1kj23k1j31k2hu31k2hj3lkl12j3j123jklk23jl12k3j"
example_period_key = "K1234"

example_box_1 = 0.51
example_box_2 = 125.51
example_box_3 = 90851.15
example_box_4 = 985615915.23
example_box_5 = 2789313.77
example_box_6 = 21873
example_box_7 = 18954
example_box_8 = 1239087123
example_box_9 = 1023123093

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

example_return = {
    "periodKey": example_period_key,
    "vatDueSales": example_box_1,
    "vatDueAcquisitions": example_box_2,
    "totalVatDue": example_box_3,
    "vatReclaimedCurrPeriod": example_box_4,
    "netVatDue": example_box_5,
    "totalValueSalesExVAT": example_box_6,
    "totalValuePurchasesExVAT": example_box_7,
    "totalValueGoodsSuppliedExVAT": example_box_8,
    "totalAcquisitionsExVAT": example_box_9,
    "finalised": True,
}

example_submission_response = {
    "example": "dunno"
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
    'Gov-Client-Local-IPs-Timestamp': '2045-03-30T15:34:51.123Z',
    'Gov-Client-MAC-Addresses': '01%3A23%3A45%3A67%3A89%3Aab',
    'Gov-Client-User-Agent': 'os-family=Aardvark+Bunches&os-version=1.23.5.15-12312.515&device-manufacturer=Aardvark+Limited&device-model=Turtledove+Power+Buncher',
    'Gov-Vendor-Version': 'gnucash-UK-vAt=12.412.41.251',
    'Gov-Vendor-Product-Name': 'gnucash-UK-vAt',
    'Gov-Vendor-License-Ids': 'gnucash-UK-vAt=c56950db1ed4422dd0a597779b4362613e6aee57',
    'Gov-Client-Multi-Factor': '',
    'Authorization': 'Bearer l1kj23k1j31k2hu31k2hj3lkl12j3j123jklk23jl12k3j',
}

example_api_base = "https://example.com.nonexistent"
example_oauth_base = "ftp://asdlkjasd.nonexistent.asdklasdasda"

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

def create_vat_client():
    vat = Vat(example_config, example_auth)
    vat.oauth_base = example_api_base
    vat.api_base = example_api_base
    return vat

def test_url():

    vat = create_vat_client()

    url = vat.get_auth_url()

    assert(url == f"{example_api_base}/oauth/authorize?response_type=code&client_id={example_client_id}&scope=read%3Avat+write%3Avat&redirect_uri=http%3A%2F%2Flocalhost%3A9876%2Fauth")

def test_fraud_headers():

    vat = create_vat_client()

    headers = vat.build_fraud_headers()

    hashed_license_id = hashlib.sha1(b'GPL3').hexdigest()

    assert(headers['Gov-Client-Connection-Method'] == 'OTHER_DIRECT')
    assert(headers['Gov-Client-Device-ID'] == example_device_id)

    assert(headers['Gov-Client-User-Ids'] == f'os={example_user}')
    assert(headers['Gov-Client-Timezone'] == 'UTC+00:00')
    assert(headers['Gov-Client-Local-IPs'] == example_local_ip)
    assert(headers['Gov-Client-Local-IPs-Timestamp'] == '2045-03-30T15:34:51.123Z')
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

def test_timestamp_format_validation():
    """Test Gov-Client-Local-IPs-Timestamp format validation"""
    import re
    import ipaddress
    
    vat = create_vat_client()
    headers = vat.build_fraud_headers()
    
    timestamp = headers['Gov-Client-Local-IPs-Timestamp']
    
    # Test ISO format with Z suffix
    iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$'
    assert re.match(iso_pattern, timestamp), f"Timestamp {timestamp} does not match ISO format with 3-digit milliseconds and Z suffix"
    
    # Test it's a valid datetime
    parsed_dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    assert parsed_dt.tzinfo == datetime.timezone.utc, "Timestamp must be in UTC"
    
    # Test milliseconds are exactly 3 digits
    millisecond_part = timestamp.split('.')[1][:-1]  # Remove 'Z'
    assert len(millisecond_part) == 3, f"Milliseconds must be 3 digits, got {len(millisecond_part)}"
    assert millisecond_part.isdigit(), "Milliseconds must be numeric"

def test_ip_address_format_validation():
    """Test Gov-Client-Local-IPs format validation"""
    import ipaddress
    
    vat = create_vat_client()
    headers = vat.build_fraud_headers()
    
    ip_address = headers['Gov-Client-Local-IPs']
    
    # Test it's a valid IP address
    try:
        ipaddress.ip_address(ip_address)
    except ValueError:
        pytest.fail(f"Invalid IP address format: {ip_address}")

def test_mac_address_format_validation():
    """Test Gov-Client-MAC-Addresses format validation"""
    from urllib.parse import unquote_plus
    import re
    
    vat = create_vat_client()
    headers = vat.build_fraud_headers()
    
    mac_encoded = headers['Gov-Client-MAC-Addresses']
    mac_decoded = unquote_plus(mac_encoded)
    
    # Test MAC address format (XX:XX:XX:XX:XX:XX)
    mac_pattern = r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
    assert re.match(mac_pattern, mac_decoded), f"Invalid MAC address format: {mac_decoded}"
    
    # Test URL encoding is correct
    expected_encoded = quote_plus(mac_decoded)
    assert mac_encoded == expected_encoded, f"MAC address not properly URL encoded"

def test_user_agent_format_validation():
    """Test Gov-Client-User-Agent format validation"""
    from urllib.parse import parse_qs, unquote_plus
    
    vat = create_vat_client()
    headers = vat.build_fraud_headers()
    
    user_agent = headers['Gov-Client-User-Agent']
    
    # Test URL encoding format
    try:
        parsed = parse_qs(user_agent, keep_blank_values=True)
        
        # Test required fields are present
        required_fields = ['os-family', 'os-version', 'device-manufacturer', 'device-model']
        for field in required_fields:
            assert field in parsed, f"Required field {field} missing from User-Agent"
            assert len(parsed[field]) == 1, f"Field {field} should have exactly one value"
            assert parsed[field][0], f"Field {field} should not be empty"
            
    except Exception as e:
        pytest.fail(f"Invalid User-Agent URL encoding: {user_agent}, error: {e}")

def test_license_ids_format_validation():
    """Test Gov-Vendor-License-Ids format validation"""
    import re
    
    vat = create_vat_client()
    headers = vat.build_fraud_headers()
    
    license_ids = headers['Gov-Vendor-License-Ids']
    
    # Test format: product-name=sha1-hash
    pattern = r'^[^=]+=[a-f0-9]{40}$'
    assert re.match(pattern, license_ids), f"Invalid license IDs format: {license_ids}"
    
    # Extract and validate SHA1 hash
    parts = license_ids.split('=', 1)
    assert len(parts) == 2, "License IDs must be in format product=hash"
    
    product_name, hash_value = parts
    assert product_name, "Product name must not be empty"
    assert len(hash_value) == 40, f"SHA1 hash must be 40 characters, got {len(hash_value)}"
    assert re.match(r'^[a-f0-9]+$', hash_value), "SHA1 hash must be lowercase hexadecimal"

@pytest.mark.asyncio    
async def test_get_vat_liabilities(mocker):

    vat = create_vat_client()

    resp = MockResponse(example_liabilities, 200)

    mocker.patch('aiohttp.ClientSession.get', return_value=resp)

    liabs = await vat.get_vat_liabilities(
        example_vrn, example_start, example_end
    )

    aiohttp.ClientSession.get.assert_called_once_with(
        f"{example_api_base}/organisations/vat/918273645/liabilities?from=2019-04-06&to=2023-12-29",
        headers=expected_headers | {
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

@pytest.mark.asyncio    
async def test_get_vat_return(mocker):

    vat = create_vat_client()

    resp = MockResponse(example_return, 200)

    mocker.patch('aiohttp.ClientSession.get', return_value=resp)

    rtn = await vat.get_vat_return(example_vrn, example_period_key)

    aiohttp.ClientSession.get.assert_called_once_with(
        f"{example_api_base}/organisations/vat/918273645/returns/K1234",
        headers=expected_headers | {
            'Accept': 'application/vnd.hmrc.1.0+json'
        }
    )

    assert(rtn.periodKey == example_return["periodKey"])
    assert(rtn.vatDueSales == example_return["vatDueSales"])
    assert(rtn.vatDueAcquisitions == example_return["vatDueAcquisitions"])
    assert(rtn.totalVatDue == example_return["totalVatDue"])
    assert(rtn.vatReclaimedCurrPeriod == example_return["vatReclaimedCurrPeriod"])
    assert(rtn.netVatDue == example_return["netVatDue"])
    assert(rtn.totalValueSalesExVAT == example_return["totalValueSalesExVAT"])
    assert(rtn.totalValuePurchasesExVAT == example_return["totalValuePurchasesExVAT"])
    assert(rtn.totalValueGoodsSuppliedExVAT == example_return["totalValueGoodsSuppliedExVAT"])
    assert(rtn.totalAcquisitionsExVAT == example_return["totalAcquisitionsExVAT"])
    assert(rtn.finalised == example_return["finalised"])
    
@pytest.mark.asyncio    
async def test_submit_vat_return(mocker):

    vat = create_vat_client()

    resp = MockResponse(example_submission_response, 201)

    mocker.patch('aiohttp.ClientSession.post', return_value=resp)

    resp = await vat.submit_vat_return(
        example_vrn,
        Return.from_dict(example_return)
    )

    aiohttp.ClientSession.post.assert_called_once_with(
        f"{example_api_base}/organisations/vat/918273645/returns",
        headers=expected_headers | {
            'Accept': 'application/vnd.hmrc.1.0+json'
        },
        json=example_return,
    )

    assert(resp == example_submission_response)

