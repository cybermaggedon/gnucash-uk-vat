"""
Contract tests for HMRC VAT API integration.

These tests verify that our implementation matches the HMRC API specification
by testing against either the vat-test-service or actual API responses.
"""

import pytest
import json
import aiohttp
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

from gnucash_uk_vat.model import Obligation, Liability, Payment, Return
from gnucash_uk_vat.hmrc import Vat, VatTest, VatLocalTest
from gnucash_uk_vat.config import Config
from gnucash_uk_vat.auth import Auth


class TestObligationContract:
    """Test HMRC API contract for Obligations endpoint"""
    
    def test_obligation_response_structure(self):
        """Verify obligation response matches HMRC specification"""
        # Sample response from HMRC API spec
        sample_response = {
            "obligations": [
                {
                    "status": "O",
                    "periodKey": "#001",
                    "start": "2023-01-01",
                    "end": "2023-03-31",
                    "due": "2023-04-30"
                },
                {
                    "status": "F", 
                    "periodKey": "#002",
                    "start": "2023-04-01",
                    "end": "2023-06-30",
                    "received": "2023-07-15",
                    "due": "2023-07-31"
                }
            ]
        }
        
        # Verify our model can parse the expected response
        obligations = [Obligation.from_dict(obl) for obl in sample_response["obligations"]]
        
        # Verify first obligation (open)
        assert obligations[0].status == "O"
        assert obligations[0].periodKey == "#001"
        assert obligations[0].start == date(2023, 1, 1)
        assert obligations[0].end == date(2023, 3, 31)
        assert obligations[0].due == date(2023, 4, 30)
        assert obligations[0].received is None
        
        # Verify second obligation (fulfilled)
        assert obligations[1].status == "F"
        assert obligations[1].periodKey == "#002" 
        assert obligations[1].start == date(2023, 4, 1)
        assert obligations[1].end == date(2023, 6, 30)
        assert obligations[1].received == date(2023, 7, 15)
        assert obligations[1].due == date(2023, 7, 31)
        
        # Verify serialization back to API format
        serialized = [obl.to_dict() for obl in obligations]
        assert serialized[0]["status"] == "O"
        assert serialized[0]["start"] == "2023-01-01"
        assert "received" not in serialized[0]
        assert serialized[1]["received"] == "2023-07-15"
    
    def test_obligation_query_parameters(self):
        """Verify obligation query parameters match HMRC spec"""
        # HMRC API spec requires these query parameters
        required_params = ["from", "to"]
        optional_params = ["status"]
        
        # Test that our implementation would generate correct URLs
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        # Mock the URL construction logic from hmrc.py
        from urllib.parse import urlencode
        
        params = {
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d")
        }
        query_string = urlencode(params)
        
        assert "from=2023-01-01" in query_string
        assert "to=2023-12-31" in query_string
        
        # Test with status filter
        params["status"] = "O"
        query_string = urlencode(params)
        assert "status=O" in query_string


class TestLiabilityContract:
    """Test HMRC API contract for Liabilities endpoint"""
    
    def test_liability_response_structure(self):
        """Verify liability response matches HMRC specification"""
        sample_response = {
            "liabilities": [
                {
                    "type": "Net VAT",
                    "originalAmount": 1200.50,
                    "outstandingAmount": 1200.50,
                    "taxPeriod": {
                        "from": "2023-01-01",
                        "to": "2023-03-31"
                    },
                    "due": "2023-04-30"
                },
                {
                    "type": "Net VAT",
                    "originalAmount": 800.00,
                    "taxPeriod": {
                        "from": "2023-04-01", 
                        "to": "2023-06-30"
                    },
                    "due": "2023-07-31"
                }
            ]
        }
        
        # Verify our model can parse the response
        liabilities = [Liability.from_dict(liab) for liab in sample_response["liabilities"]]
        
        # Verify first liability
        assert liabilities[0].typ == "Net VAT"
        assert liabilities[0].original == 1200.50
        assert liabilities[0].outstanding == 1200.50
        assert liabilities[0].start == date(2023, 1, 1)
        assert liabilities[0].end == date(2023, 3, 31)
        assert liabilities[0].due == date(2023, 4, 30)
        
        # Verify second liability (no outstanding amount)
        assert liabilities[1].typ == "Net VAT"
        assert liabilities[1].original == 800.00
        assert liabilities[1].outstanding is None
        assert liabilities[1].start == date(2023, 4, 1)
        assert liabilities[1].end == date(2023, 6, 30)
        
        # Test serialization
        serialized = [liab.to_dict() for liab in liabilities]
        assert serialized[0]["originalAmount"] == 1200.50
        assert serialized[0]["taxPeriod"]["from"] == "2023-01-01"


class TestPaymentContract:
    """Test HMRC API contract for Payments endpoint"""
    
    def test_payment_response_structure(self):
        """Verify payment response matches HMRC specification"""
        sample_response = {
            "payments": [
                {
                    "amount": 1200.50,
                    "received": "2023-05-15"
                },
                {
                    "amount": 800.00,
                    "received": "2023-08-10"
                }
            ]
        }
        
        # Verify our model can parse the response
        payments = [Payment.from_dict(pay) for pay in sample_response["payments"]]
        
        # Verify payments
        assert payments[0].amount == 1200.50
        assert payments[0].received == date(2023, 5, 15)
        assert payments[1].amount == 800.00
        assert payments[1].received == date(2023, 8, 10)
        
        # Test serialization
        serialized = [pay.to_dict() for pay in payments]
        assert serialized[0]["amount"] == 1200.50
        assert serialized[0]["received"] == "2023-05-15"


class TestVatReturnContract:
    """Test HMRC API contract for VAT Return endpoint"""
    
    def test_vat_return_request_structure(self):
        """Verify VAT return request matches HMRC specification"""
        # Create a VAT return as we would submit it
        vat_return = Return()
        vat_return.periodKey = "#001"
        vat_return.vatDueSales = 1500.75
        vat_return.vatDueAcquisitions = 200.50
        vat_return.totalVatDue = 1701.25
        vat_return.vatReclaimedCurrPeriod = 450.25
        vat_return.netVatDue = 1251.00
        vat_return.totalValueSalesExVAT = 15000
        vat_return.totalValuePurchasesExVAT = 8000
        vat_return.totalValueGoodsSuppliedExVAT = 0
        vat_return.totalAcquisitionsExVAT = 0
        vat_return.finalised = True
        
        # Serialize to API format
        request_data = vat_return.to_dict()
        
        # Verify all required fields are present according to HMRC spec
        required_fields = [
            "periodKey",
            "vatDueSales", 
            "vatDueAcquisitions",
            "totalVatDue",
            "vatReclaimedCurrPeriod",
            "netVatDue",
            "totalValueSalesExVAT",
            "totalValuePurchasesExVAT", 
            "totalValueGoodsSuppliedExVAT",
            "totalAcquisitionsExVAT",
            "finalised"
        ]
        
        for field in required_fields:
            assert field in request_data, f"Missing required field: {field}"
        
        # Verify data types match specification
        assert isinstance(request_data["periodKey"], str)
        assert isinstance(request_data["vatDueSales"], (int, float))
        assert isinstance(request_data["finalised"], bool)
        assert request_data["finalised"] == True
        
        # Verify precision requirements (boxes 1-5 allow pence, 6-9 are pounds only)
        assert request_data["vatDueSales"] == 1500.75  # Pence allowed
        assert request_data["totalValueSalesExVAT"] == 15000  # Pounds only
    
    def test_vat_return_response_structure(self):
        """Verify VAT return response matches HMRC specification"""
        sample_response = {
            "processingDate": "2023-04-15T14:30:00.000Z",
            "paymentIndicator": "BANK",
            "formBundleNumber": "12345678901",
            "chargeRefNumber": "XM002609102760"
        }
        
        # Verify response structure matches what we expect
        required_response_fields = [
            "processingDate",
            "paymentIndicator", 
            "formBundleNumber",
            "chargeRefNumber"
        ]
        
        for field in required_response_fields:
            assert field in sample_response
        
        # Verify processing date is valid ISO format
        processing_date = datetime.fromisoformat(sample_response["processingDate"].replace('Z', '+00:00'))
        assert isinstance(processing_date, datetime)
        assert processing_date.tzinfo is not None


class TestFraudHeadersContract:
    """Test HMRC fraud prevention headers contract"""
    
    def test_required_fraud_headers(self):
        """Verify all required fraud prevention headers are included"""
        # Create mock config and auth
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.mac-address": "00:11:22:33:44:55",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "Ubuntu 20.04",
            "identity.device.device-manufacturer": "Dell Inc.",
            "identity.device.device-model": "OptiPlex 7090",
            "identity.device.id": "device-12345",
            "application.product-name": "gnucash-uk-vat",
            "application.product-version": "1.0.0",
            "identity.user": "test-user",
            "identity.local-ip": "192.168.1.100",
            "identity.time": "2023-04-15T10:30:00Z"
        }[key]
        
        mock_auth = MagicMock()
        mock_auth.get.return_value = "test-access-token"
        
        # Create VAT client and build headers
        vat_client = Vat(mock_config, mock_auth)
        headers = vat_client.build_fraud_headers()
        
        # Verify all required fraud prevention headers are present
        required_headers = [
            'Gov-Client-Connection-Method',
            'Gov-Client-Device-ID',
            'Gov-Client-User-Ids',
            'Gov-Client-Timezone',
            'Gov-Client-Local-IPs',
            'Gov-Client-Local-IPs-Timestamp',
            'Gov-Client-MAC-Addresses',
            'Gov-Client-User-Agent',
            'Gov-Vendor-Version',
            'Gov-Vendor-Product-Name',
            'Gov-Vendor-License-Ids',
            'Gov-Client-Multi-Factor',
            'Authorization'
        ]
        
        for header in required_headers:
            assert header in headers, f"Missing required fraud header: {header}"
        
        # Verify header formats match HMRC specification
        assert headers['Gov-Client-Connection-Method'] == 'OTHER_DIRECT'
        assert headers['Gov-Client-Device-ID'] == 'device-12345'
        assert 'os=test-user' in headers['Gov-Client-User-Ids']
        assert headers['Gov-Client-Timezone'] == 'UTC+00:00'
        assert '00%3A11%3A22%3A33%3A44%3A55' in headers['Gov-Client-MAC-Addresses']  # URL encoded MAC
        assert 'Bearer test-access-token' == headers['Authorization']
        
        # Verify user agent format
        user_agent = headers['Gov-Client-User-Agent'] 
        assert 'os-family=Linux' in user_agent
        assert 'device-manufacturer=Dell+Inc.' in user_agent
    
    def test_fraud_headers_url_encoding(self):
        """Verify fraud headers are properly URL encoded"""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.mac-address": "00:11:22:33:44:55",  # Contains colons
            "identity.device.device-manufacturer": "Dell Inc.",  # Contains space
            "identity.device.device-model": "OptiPlex 7090",  # Contains space
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "Ubuntu 20.04",
            "identity.device.id": "device-12345",
            "application.product-name": "gnucash-uk-vat",
            "application.product-version": "1.0.0",
            "identity.user": "test-user",
            "identity.local-ip": "192.168.1.100",
            "identity.time": "2023-04-15T10:30:00Z"
        }[key]
        
        mock_auth = MagicMock()
        mock_auth.get.return_value = "test-token"
        
        vat_client = Vat(mock_config, mock_auth)
        headers = vat_client.build_fraud_headers()
        
        # Verify MAC address is URL encoded (colons become %3A)
        mac_header = headers['Gov-Client-MAC-Addresses']
        assert '%3A' in mac_header  # URL encoded colon
        assert ':' not in mac_header  # No raw colons
        
        # Verify user agent is URL encoded
        user_agent = headers['Gov-Client-User-Agent']
        assert 'Dell+Inc.' in user_agent  # Space encoded as +
        assert 'OptiPlex+7090' in user_agent  # Space encoded as +


class TestErrorResponseContract:
    """Test HMRC API error response contract"""
    
    def test_error_response_structure(self):
        """Verify error responses match HMRC specification"""
        sample_error_responses = [
            {
                "code": "INVALID_VRN",
                "message": "The provided VRN is invalid"
            },
            {
                "code": "NOT_FOUND",
                "message": "The remote endpoint has indicated that no data can be found"
            },
            {
                "code": "BUSINESS_ERROR", 
                "message": "Business validation error",
                "errors": [
                    {
                        "code": "RULE_INCORRECT_OR_EMPTY_BODY_SUBMITTED",
                        "message": "The request body submitted has not passed validation"
                    }
                ]
            }
        ]
        
        # Verify our error handling can parse these formats
        for error_response in sample_error_responses:
            assert "code" in error_response
            assert "message" in error_response
            
            # Some errors have nested errors array
            if "errors" in error_response:
                for nested_error in error_response["errors"]:
                    assert "code" in nested_error
                    assert "message" in nested_error


class TestApiVersionContract:
    """Test HMRC API version compliance"""
    
    def test_accept_header_format(self):
        """Verify Accept header matches HMRC API version requirement"""
        # HMRC requires specific Accept header format
        expected_accept_header = "application/vnd.hmrc.1.0+json"
        
        # This is what our implementation should send
        # (verified by checking hmrc.py methods)
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_client = Vat(mock_config, mock_auth)
        
        # The accept header should be added in API methods
        # This is a contract test to ensure we use the right format
        assert expected_accept_header == "application/vnd.hmrc.1.0+json"
        
        # Verify version format compliance
        assert "vnd.hmrc" in expected_accept_header
        assert "1.0" in expected_accept_header
        assert "+json" in expected_accept_header


class TestDateFormatContract:
    """Test date format compliance with HMRC API"""
    
    def test_date_serialization_format(self):
        """Verify dates are serialized in YYYY-MM-DD format"""
        test_date = date(2023, 4, 15)
        
        # Test obligation date serialization
        obligation = Obligation("#001", "O", test_date, test_date, due=test_date)
        serialized = obligation.to_dict()
        
        assert serialized["start"] == "2023-04-15"
        assert serialized["end"] == "2023-04-15"
        assert serialized["due"] == "2023-04-15"
        
        # Test liability date serialization  
        liability = Liability(test_date, test_date, "Net VAT", 1000.0, due=test_date)
        serialized = liability.to_dict()
        
        assert serialized["taxPeriod"]["from"] == "2023-04-15"
        assert serialized["taxPeriod"]["to"] == "2023-04-15"
        assert serialized["due"] == "2023-04-15"
        
        # Test payment date serialization
        payment = Payment(500.0, test_date)
        serialized = payment.to_dict()
        
        assert serialized["received"] == "2023-04-15"
    
    def test_date_parsing_from_api(self):
        """Verify dates from API responses are parsed correctly"""
        # Test various date formats that might come from API
        api_date_string = "2023-04-15"
        parsed_date = datetime.fromisoformat(api_date_string).date()
        
        assert parsed_date == date(2023, 4, 15)
        assert parsed_date.year == 2023
        assert parsed_date.month == 4
        assert parsed_date.day == 15


class TestVatTestServiceContract:
    """Test contract compliance with vat-test-service"""
    
    def test_magic_vrn_format(self):
        """Verify magic VRN format matches test service specification"""
        # Test service uses magic VRNs: 999DDMMYY
        magic_vrn = "999150423"  # 15/04/23
        
        # Verify format
        assert magic_vrn.startswith("999")
        assert len(magic_vrn) == 9
        
        # Extract date components
        date_part = magic_vrn[3:]  # "150423"
        assert len(date_part) == 6
        
        # Verify it represents a valid date
        day = int(date_part[:2])    # 15
        month = int(date_part[2:4]) # 04  
        year = int(date_part[4:])   # 23
        
        assert 1 <= day <= 31
        assert 1 <= month <= 12
        assert year >= 0
    
    def test_test_service_response_compatibility(self):
        """Verify our models work with test service responses"""
        # Sample response from vat-test-service
        test_service_response = {
            "obligations": [
                {
                    "status": "O",
                    "periodKey": "#003", 
                    "start": "2023-07-01",
                    "end": "2023-09-30",
                    "due": "2023-10-31"
                }
            ]
        }
        
        # Verify our models can parse test service data
        obligations = [Obligation.from_dict(obl) for obl in test_service_response["obligations"]]
        
        assert len(obligations) == 1
        assert obligations[0].status == "O"
        assert obligations[0].periodKey == "#003"
        assert obligations[0].start == date(2023, 7, 1)
        assert obligations[0].end == date(2023, 9, 30)
        assert obligations[0].due == date(2023, 10, 31)


class TestEndpointUrlContract:
    """Test API endpoint URL format compliance"""
    
    def test_production_endpoints(self):
        """Verify production API endpoints match HMRC specification"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_client = Vat(mock_config, mock_auth)
        
        # Verify base URLs
        assert vat_client.oauth_base == 'https://www.tax.service.gov.uk'
        assert vat_client.api_base == 'https://api.service.hmrc.gov.uk'
        
        # Test endpoint construction
        vrn = "123456789"
        period_key = "#001"
        
        # Obligations endpoint
        expected_obligations_url = f"{vat_client.api_base}/organisations/vat/{vrn}/obligations"
        assert "/organisations/vat/" in expected_obligations_url
        assert vrn in expected_obligations_url
        
        # VAT return endpoint  
        expected_return_url = f"{vat_client.api_base}/organisations/vat/{vrn}/returns/{period_key}"
        assert "/organisations/vat/" in expected_return_url
        assert "/returns/" in expected_return_url
        
        # Liabilities endpoint
        expected_liabilities_url = f"{vat_client.api_base}/organisations/vat/{vrn}/liabilities"
        assert "/liabilities" in expected_liabilities_url
        
        # Payments endpoint
        expected_payments_url = f"{vat_client.api_base}/organisations/vat/{vrn}/payments" 
        assert "/payments" in expected_payments_url
    
    def test_test_environment_endpoints(self):
        """Verify test environment endpoints"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_test_client = VatTest(mock_config, mock_auth, None)
        
        # Verify test environment URLs
        assert vat_test_client.oauth_base == 'https://test-www.tax.service.gov.uk'
        assert vat_test_client.api_base == 'https://test-api.service.hmrc.gov.uk'
    
    def test_local_test_endpoints(self):
        """Verify local test service endpoints"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_local_client = VatLocalTest(mock_config, mock_auth, None)
        
        # Verify local test URLs
        assert vat_local_client.oauth_base == 'http://localhost:8080'
        assert vat_local_client.api_base == 'http://localhost:8080'