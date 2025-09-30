"""
Contract tests for extension points in gnucash-uk-vat.

These tests ensure that extension points remain stable and can be safely
used by external code (like accountsmachine) without breaking when changes
are made to the base library.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
import aiohttp
from datetime import date

from gnucash_uk_vat.hmrc import Vat
from gnucash_uk_vat.model import Return


class TestBuildFraudHeadersExtensionPoint:
    """Test that build_fraud_headers() is a stable extension point"""

    def test_build_fraud_headers_method_exists(self):
        """Test that build_fraud_headers() method exists on Vat class"""
        # Create a minimal Vat instance
        config = {
            "identity.mac-address": "00:00:00:00:00:00",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Test",
            "identity.device.device-model": "TestModel",
            "identity.device.id": "test-device",
            "application.product-name": "test",
            "application.product-version": "1.0",
            "identity.user": "testuser",
            "identity.local-ip": "127.0.0.1",
            "identity.time": "2023-01-01T00:00:00.000Z",
        }
        auth = {"access_token": "test-token"}

        vat = Vat(config, auth)

        # Verify method exists
        assert hasattr(vat, 'build_fraud_headers')
        assert callable(vat.build_fraud_headers)

        # Verify it returns a dict
        headers = vat.build_fraud_headers()
        assert isinstance(headers, dict)
        assert len(headers) > 0

    def test_build_fraud_headers_signature(self):
        """Test that build_fraud_headers() has stable signature"""
        import inspect

        # Get the method signature
        sig = inspect.signature(Vat.build_fraud_headers)
        params = list(sig.parameters.keys())

        # Should only have 'self' parameter
        assert params == ['self'], f"Expected only 'self' parameter, got {params}"

        # Should return something (not specified as None)
        assert sig.return_annotation == inspect.Signature.empty or sig.return_annotation == dict

    def test_subclass_can_override_build_fraud_headers(self):
        """Test that subclasses can override build_fraud_headers()"""

        # Create a subclass that overrides the method
        class CustomVat(Vat):
            def build_fraud_headers(self):
                # Return custom headers
                return {
                    'Custom-Header': 'custom-value',
                    'Gov-Vendor-Version': 'custom-version',
                    'Authorization': f'Bearer {self.auth.get("access_token")}'
                }

        config = {
            "identity.mac-address": "00:00:00:00:00:00",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Test",
            "identity.device.device-model": "TestModel",
            "identity.device.id": "test-device",
            "application.product-name": "test",
            "application.product-version": "1.0",
            "identity.user": "testuser",
            "identity.local-ip": "127.0.0.1",
            "identity.time": "2023-01-01T00:00:00.000Z",
        }
        auth = {"access_token": "test-token-123"}

        custom_vat = CustomVat(config, auth)
        headers = custom_vat.build_fraud_headers()

        # Verify custom headers are returned
        assert headers['Custom-Header'] == 'custom-value'
        assert headers['Gov-Vendor-Version'] == 'custom-version'
        assert headers['Authorization'] == 'Bearer test-token-123'


class TestOverriddenHeadersFlowThrough:
    """Test that overridden headers actually make it into HTTP requests"""

    @pytest.mark.asyncio
    async def test_submit_vat_return_uses_overridden_headers(self):
        """Test that submit_vat_return() uses headers from overridden build_fraud_headers()"""

        # Create a subclass with custom headers (simulating accountsmachine pattern)
        class ExtendedVat(Vat):
            def build_fraud_headers(self):
                # Simulate extended fraud headers like accountsmachine
                return {
                    'Gov-Client-Connection-Method': 'WEB_APP_VIA_SERVER',
                    'Gov-Client-Window-Size': 'width=1920&height=1080',
                    'Gov-Client-Screens': 'width=1920&height=1080&scaling-factor=1&colour-depth=24',
                    'Gov-Vendor-Version': 'accounts-svc=1.2.3&accounts-web=4.5.6',
                    'Gov-Client-User-IDs': 'accountsmachine.io=testuser&email=test@example.com',
                    'Authorization': f'Bearer {self.auth.get("access_token")}'
                }

        config = {
            "identity.mac-address": "00:00:00:00:00:00",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Test",
            "identity.device.device-model": "TestModel",
            "identity.device.id": "test-device",
            "application.product-name": "test",
            "application.product-version": "1.0",
            "identity.user": "testuser",
            "identity.local-ip": "127.0.0.1",
            "identity.time": "2023-01-01T00:00:00.000Z",
        }
        auth = {"access_token": "test-custom-token"}

        vat = ExtendedVat(config, auth)
        vat.api_base = "https://test.example.com"

        # Create a test VAT return
        vat_return = Return()
        vat_return.periodKey = "A001"
        vat_return.vatDueSales = 100.0
        vat_return.vatDueAcquisitions = 50.0
        vat_return.totalVatDue = 150.0
        vat_return.vatReclaimedCurrPeriod = 75.0
        vat_return.netVatDue = 75.0
        vat_return.totalValueSalesExVAT = 1000
        vat_return.totalValuePurchasesExVAT = 500
        vat_return.totalValueGoodsSuppliedExVAT = 800
        vat_return.totalAcquisitionsExVAT = 200
        vat_return.finalised = True

        # Mock aiohttp to capture the request
        mock_response = AsyncMock()
        mock_response.status = 201
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_post = MagicMock(return_value=mock_response)
        mock_session.post = mock_post
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            await vat.submit_vat_return("123456789", vat_return)

        # Verify the request was made
        assert mock_post.called

        # Get the headers that were actually sent
        call_kwargs = mock_post.call_args[1]
        actual_headers = call_kwargs['headers']

        # Verify our custom headers made it through
        assert actual_headers['Gov-Client-Connection-Method'] == 'WEB_APP_VIA_SERVER'
        assert actual_headers['Gov-Client-Window-Size'] == 'width=1920&height=1080'
        assert actual_headers['Gov-Client-Screens'] == 'width=1920&height=1080&scaling-factor=1&colour-depth=24'
        assert actual_headers['Gov-Vendor-Version'] == 'accounts-svc=1.2.3&accounts-web=4.5.6'
        assert actual_headers['Gov-Client-User-IDs'] == 'accountsmachine.io=testuser&email=test@example.com'
        assert actual_headers['Authorization'] == 'Bearer test-custom-token'

        # Verify Accept header was added by the API method
        assert actual_headers['Accept'] == 'application/vnd.hmrc.1.0+json'

    @pytest.mark.asyncio
    async def test_get_vat_liabilities_uses_overridden_headers(self):
        """Test that get_vat_liabilities() uses headers from overridden build_fraud_headers()"""

        class ExtendedVat(Vat):
            def build_fraud_headers(self):
                return {
                    'Gov-Client-Public-IP': '203.0.113.42',
                    'Gov-Client-Timezone': 'UTC+00:00',
                    'Gov-Vendor-Product-Name': 'accountsmachine.io',
                    'Authorization': f'Bearer {self.auth.get("access_token")}'
                }

        config = {
            "identity.mac-address": "00:00:00:00:00:00",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Test",
            "identity.device.device-model": "TestModel",
            "identity.device.id": "test-device",
            "application.product-name": "test",
            "application.product-version": "1.0",
            "identity.user": "testuser",
            "identity.local-ip": "127.0.0.1",
            "identity.time": "2023-01-01T00:00:00.000Z",
        }
        auth = {"access_token": "liability-token"}

        vat = ExtendedVat(config, auth)
        vat.api_base = "https://test.example.com"

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"liabilities": []})
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_get = MagicMock(return_value=mock_response)
        mock_session.get = mock_get
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            await vat.get_vat_liabilities("123456789", date(2023, 1, 1), date(2023, 12, 31))

        # Get the headers that were actually sent
        call_kwargs = mock_get.call_args[1]
        actual_headers = call_kwargs['headers']

        # Verify our custom headers made it through
        assert actual_headers['Gov-Client-Public-IP'] == '203.0.113.42'
        assert actual_headers['Gov-Client-Timezone'] == 'UTC+00:00'
        assert actual_headers['Gov-Vendor-Product-Name'] == 'accountsmachine.io'
        assert actual_headers['Authorization'] == 'Bearer liability-token'

    @pytest.mark.asyncio
    async def test_get_obligations_uses_overridden_headers(self):
        """Test that get_obligations() uses headers from overridden build_fraud_headers()"""

        class ExtendedVat(Vat):
            def build_fraud_headers(self):
                return {
                    'Gov-Client-Device-ID': 'custom-device-12345',
                    'Gov-Client-Multi-Factor': 'type=TOTP&timestamp=2023-01-01T12:00:00Z',
                    'Authorization': f'Bearer {self.auth.get("access_token")}'
                }

        config = {
            "identity.mac-address": "00:00:00:00:00:00",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Test",
            "identity.device.device-model": "TestModel",
            "identity.device.id": "test-device",
            "application.product-name": "test",
            "application.product-version": "1.0",
            "identity.user": "testuser",
            "identity.local-ip": "127.0.0.1",
            "identity.time": "2023-01-01T00:00:00.000Z",
        }
        auth = {"access_token": "obligations-token"}

        vat = ExtendedVat(config, auth)
        vat.api_base = "https://test.example.com"

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"obligations": []})
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_get = MagicMock(return_value=mock_response)
        mock_session.get = mock_get
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            await vat.get_obligations("123456789", date(2023, 1, 1), date(2023, 12, 31))

        # Get the headers that were actually sent
        call_kwargs = mock_get.call_args[1]
        actual_headers = call_kwargs['headers']

        # Verify our custom headers made it through
        assert actual_headers['Gov-Client-Device-ID'] == 'custom-device-12345'
        assert actual_headers['Gov-Client-Multi-Factor'] == 'type=TOTP&timestamp=2023-01-01T12:00:00Z'
        assert actual_headers['Authorization'] == 'Bearer obligations-token'


class TestExtensionPointStability:
    """Test that the extension point is called by all relevant methods"""

    @pytest.mark.asyncio
    async def test_all_api_methods_call_build_fraud_headers(self):
        """Test that all major API methods call build_fraud_headers()"""

        # Track whether build_fraud_headers was called
        calls = []

        class SpyVat(Vat):
            def build_fraud_headers(self):
                calls.append('build_fraud_headers')
                return {
                    'Authorization': f'Bearer {self.auth.get("access_token")}',
                    'Test-Header': 'test-value'
                }

        config = {
            "identity.mac-address": "00:00:00:00:00:00",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Test",
            "identity.device.device-model": "TestModel",
            "identity.device.id": "test-device",
            "application.product-name": "test",
            "application.product-version": "1.0",
            "identity.user": "testuser",
            "identity.local-ip": "127.0.0.1",
            "identity.time": "2023-01-01T00:00:00.000Z",
        }
        auth = {"access_token": "test-token"}

        vat = SpyVat(config, auth)
        vat.api_base = "https://test.example.com"

        # Test various API methods
        # Test get_obligations
        mock_response_obligations = AsyncMock()
        mock_response_obligations.status = 200
        mock_response_obligations.json = AsyncMock(return_value={"obligations": []})
        mock_response_obligations.__aenter__.return_value = mock_response_obligations
        mock_response_obligations.__aexit__.return_value = None

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response_obligations)
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None

        with patch('aiohttp.ClientSession', return_value=mock_session):
            calls.clear()
            await vat.get_obligations("123456789", date(2023, 1, 1), date(2023, 12, 31))
            assert 'build_fraud_headers' in calls, "get_obligations should call build_fraud_headers"

        # Test get_vat_liabilities
        mock_response_liabilities = AsyncMock()
        mock_response_liabilities.status = 200
        mock_response_liabilities.json = AsyncMock(return_value={"liabilities": []})
        mock_response_liabilities.__aenter__.return_value = mock_response_liabilities
        mock_response_liabilities.__aexit__.return_value = None

        mock_session.get = MagicMock(return_value=mock_response_liabilities)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            calls.clear()
            await vat.get_vat_liabilities("123456789", date(2023, 1, 1), date(2023, 12, 31))
            assert 'build_fraud_headers' in calls, "get_vat_liabilities should call build_fraud_headers"

        # Test get_vat_payments
        mock_response_payments = AsyncMock()
        mock_response_payments.status = 200
        mock_response_payments.json = AsyncMock(return_value={"payments": []})
        mock_response_payments.__aenter__.return_value = mock_response_payments
        mock_response_payments.__aexit__.return_value = None

        mock_session.get = MagicMock(return_value=mock_response_payments)

        with patch('aiohttp.ClientSession', return_value=mock_session):
            calls.clear()
            await vat.get_vat_payments("123456789", date(2023, 1, 1), date(2023, 12, 31))
            assert 'build_fraud_headers' in calls, "get_vat_payments should call build_fraud_headers"

        # Test submit_vat_return separately (uses POST)
        mock_response_post = AsyncMock()
        mock_response_post.status = 201
        mock_response_post.__aenter__.return_value = mock_response_post
        mock_response_post.__aexit__.return_value = None

        mock_session.post = MagicMock(return_value=mock_response_post)

        vat_return = Return()
        vat_return.periodKey = "A001"
        vat_return.vatDueSales = 100.0
        vat_return.vatDueAcquisitions = 50.0
        vat_return.totalVatDue = 150.0
        vat_return.vatReclaimedCurrPeriod = 75.0
        vat_return.netVatDue = 75.0
        vat_return.totalValueSalesExVAT = 1000
        vat_return.totalValuePurchasesExVAT = 500
        vat_return.totalValueGoodsSuppliedExVAT = 800
        vat_return.totalAcquisitionsExVAT = 200
        vat_return.finalised = True

        with patch('aiohttp.ClientSession', return_value=mock_session):
            calls.clear()
            await vat.submit_vat_return("123456789", vat_return)
            assert 'build_fraud_headers' in calls, "submit_vat_return should call build_fraud_headers"
