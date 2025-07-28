import pytest
import json
import asyncio
from datetime import datetime, timedelta, date
from unittest.mock import patch, MagicMock, AsyncMock, Mock
from urllib.parse import urlencode, quote_plus
import aiohttp
import aiohttp.web
import hashlib

from gnucash_uk_vat.hmrc import (
    AuthCollector, Vat, VatTest, VatLocalTest, create
)
from gnucash_uk_vat.model import Obligation, Liability, Payment, Return


class TestAuthCollector:
    """Test the AuthCollector class"""
    
    @pytest.mark.asyncio
    async def test_init(self):
        """Test AuthCollector initialization"""
        collector = AuthCollector("localhost", 9876)
        
        assert collector.host == "localhost"
        assert collector.port == 9876
        assert collector.running == True
        assert collector.result is None
    
    @pytest.mark.asyncio
    async def test_start_and_handler(self):
        """Test AuthCollector starts web server and handles requests"""
        collector = AuthCollector("localhost", 9877)
        
        # Start the collector
        await collector.start()
        
        # Simulate a request to the handler
        async with aiohttp.ClientSession() as session:
            async with session.get(
                'http://localhost:9877/test?code=test_code&state=test_state'
            ) as resp:
                assert resp.status == 200
                body = await resp.text()
                assert body == 'Token received.'
        
        # Check result was stored
        assert collector.result == {
            'code': 'test_code',
            'state': 'test_state'
        }
        assert collector.running == False
        
        # Clean up
        await collector.stop()
    
    @pytest.mark.asyncio
    async def test_run_complete_flow(self):
        """Test complete run flow of AuthCollector"""
        collector = AuthCollector("localhost", 9878)
        
        async def simulate_request():
            # Wait a bit for server to start
            await asyncio.sleep(0.5)
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'http://localhost:9878/auth?code=auth_code'
                ) as resp:
                    assert resp.status == 200
        
        # Run collector and simulator concurrently
        result, _ = await asyncio.gather(
            collector.run(),
            simulate_request()
        )
        
        assert result == {'code': 'auth_code'}


class TestVat:
    """Test the Vat class"""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock config object"""
        config = MagicMock()
        config.get.side_effect = lambda key: {
            "application.client-id": "test_client_id",
            "application.client-secret": "test_client_secret",
            "application.product-name": "test_product",
            "application.product-version": "1.0.0",
            "application.terms-and-conditions-url": "http://example.com/terms",
            "identity.mac-address": "aa:bb:cc:dd:ee:ff",
            "identity.device.os-family": "Linux",
            "identity.device.os-version": "5.0",
            "identity.device.device-manufacturer": "Dell",
            "identity.device.device-model": "XPS",
            "identity.device.id": "device123",
            "identity.user": "testuser",
            "identity.local-ip": "192.168.1.100",
            "identity.time": "2023-01-01T00:00:00Z"
        }.get(key, "")
        return config
    
    @pytest.fixture
    def mock_auth(self):
        """Create mock auth object"""
        auth = MagicMock()
        auth.get.return_value = "test_access_token"
        auth.auth = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires": "2025-01-01T00:00:00"
        }
        return auth
    
    @pytest.fixture
    def vat_client(self, mock_config, mock_auth):
        """Create Vat client instance"""
        return Vat(mock_config, mock_auth)
    
    def test_init(self, mock_config, mock_auth):
        """Test Vat initialization"""
        vat = Vat(mock_config, mock_auth)
        
        assert vat.config == mock_config
        assert vat.auth == mock_auth
        assert vat.user is None
        assert vat.oauth_base == 'https://www.tax.service.gov.uk'
        assert vat.api_base == 'https://api.service.hmrc.gov.uk'
    
    def test_init_with_user(self, mock_config, mock_auth):
        """Test Vat initialization with user"""
        user = {"userId": "test", "password": "pass"}
        vat = Vat(mock_config, mock_auth, user)
        
        assert vat.user == user
    
    def test_get_auth_url(self, vat_client):
        """Test building authorization URL"""
        url = vat_client.get_auth_url()
        
        expected_base = "https://www.tax.service.gov.uk/oauth/authorize"
        assert url.startswith(expected_base)
        assert "response_type=code" in url
        assert "client_id=test_client_id" in url
        assert "scope=read%3Avat+write%3Avat" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A9876%2Fauth" in url
    
    def test_get_auth_credentials_no_user(self, vat_client):
        """Test getting auth credentials with no user"""
        assert vat_client.get_auth_credentials() is None
    
    def test_get_auth_credentials_with_user(self, mock_config, mock_auth):
        """Test getting auth credentials with user"""
        user = MagicMock()
        user.get.side_effect = lambda key: {
            "userId": "testuser",
            "password": "testpass"
        }.get(key)
        
        vat = Vat(mock_config, mock_auth, user)
        creds = vat.get_auth_credentials()
        
        assert "UserId: testuser" in creds
        assert "Password: testpass" in creds
    
    def test_build_fraud_headers(self, vat_client):
        """Test building fraud prevention headers"""
        headers = vat_client.build_fraud_headers()
        
        assert headers['Gov-Client-Connection-Method'] == 'OTHER_DIRECT'
        assert headers['Gov-Client-Device-ID'] == 'device123'
        assert headers['Gov-Client-User-Ids'] == 'os=testuser'
        assert headers['Gov-Client-Timezone'] == 'UTC+00:00'
        assert headers['Gov-Client-Local-IPs'] == '192.168.1.100'
        assert headers['Gov-Client-MAC-Addresses'] == 'aa%3Abb%3Acc%3Add%3Aee%3Aff'
        assert headers['Authorization'] == 'Bearer test_access_token'
        assert 'Gov-Client-User-Agent' in headers
        assert 'Gov-Vendor-Version' in headers
        assert 'Gov-Vendor-License-Ids' in headers
    
    def test_build_fraud_headers_missing_fields(self, mock_config, mock_auth):
        """Test build_fraud_headers with missing required fields"""
        # Mock config to return empty strings for required fields
        mock_config.get.side_effect = lambda key: ""
        
        vat = Vat(mock_config, mock_auth)
        
        with pytest.raises(RuntimeError) as exc_info:
            vat.build_fraud_headers()
        
        assert "not set" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_auth_coro(self, vat_client):
        """Test get_auth_coro method"""
        mock_response = {
            "access_token": "new_access_token",
            "refresh_token": "new_refresh_token",
            "token_type": "Bearer",
            "expires_in": "3600"
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Create properly mocked async context managers
            mock_session = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            
            # Mock the async context manager chain
            mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await vat_client.get_auth_coro("test_code")
        
        assert result["access_token"] == "new_access_token"
        assert result["refresh_token"] == "new_refresh_token"
        assert "expires" in result
    
    @pytest.mark.asyncio
    async def test_refresh_token_coro(self, vat_client):
        """Test refresh_token_coro method"""
        mock_response = {
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "token_type": "Bearer",
            "expires_in": "3600"
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.json.return_value = mock_response
            
            # Mock the async context manager chain
            mock_session.post.return_value.__aenter__ = AsyncMock(return_value=mock_resp)
            mock_session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await vat_client.refresh_token_coro("refresh_token")
        
        assert result["access_token"] == "refreshed_access_token"
        assert result["refresh_token"] == "refreshed_refresh_token"
    
    @pytest.mark.asyncio
    async def test_test_fraud_headers(self, vat_client):
        """Test test_fraud_headers method"""
        mock_response = {"status": "valid"}
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            with patch('builtins.print'):  # Suppress print output
                result = await vat_client.test_fraud_headers()
        
        assert result == {"status": "valid"}
    
    @pytest.mark.asyncio
    async def test_test_fraud_headers_error(self, vat_client):
        """Test test_fraud_headers with error response"""
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value={"message": "Invalid headers"})
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            with pytest.raises(RuntimeError) as exc_info:
                with patch('builtins.print'):
                    await vat_client.test_fraud_headers()
            
            assert "Invalid headers" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_open_obligations(self, vat_client):
        """Test get_open_obligations method"""
        mock_response = {
            "obligations": [
                {
                    "status": "O",
                    "periodKey": "18A1",
                    "start": "2023-01-01",
                    "end": "2023-03-31",
                    "due": "2023-05-07"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            result = await vat_client.get_open_obligations("123456789")
        
        assert len(result) == 1
        assert isinstance(result[0], Obligation)
        assert result[0].status == "O"
        assert result[0].periodKey == "18A1"
    
    @pytest.mark.asyncio
    async def test_get_obligations(self, vat_client):
        """Test get_obligations method"""
        mock_response = {
            "obligations": [
                {
                    "status": "F",
                    "periodKey": "18A1",
                    "start": "2023-01-01",
                    "end": "2023-03-31"
                },
                {
                    "status": "O",
                    "periodKey": "18A2",
                    "start": "2023-04-01",
                    "end": "2023-06-30"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            start = date(2023, 1, 1)
            end = date(2023, 12, 31)
            result = await vat_client.get_obligations("123456789", start, end)
        
        assert len(result) == 2
        assert all(isinstance(o, Obligation) for o in result)
    
    @pytest.mark.asyncio
    async def test_get_vat_return(self, vat_client):
        """Test get_vat_return method"""
        mock_response = {
            "periodKey": "18A1",
            "vatDueSales": 100.50,
            "vatDueAcquisitions": 0,
            "totalVatDue": 100.50,
            "vatReclaimedCurrPeriod": 50.25,
            "netVatDue": 50.25,
            "totalValueSalesExVAT": 502,
            "totalValuePurchasesExVAT": 251,
            "totalValueGoodsSuppliedExVAT": 0,
            "totalAcquisitionsExVAT": 0
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            result = await vat_client.get_vat_return("123456789", "18A1")
        
        assert isinstance(result, Return)
        assert result.periodKey == "18A1"
        assert result.vatDueSales == 100.50
        assert result.netVatDue == 50.25
    
    @pytest.mark.asyncio
    async def test_submit_vat_return(self, vat_client):
        """Test submit_vat_return method"""
        # Create a return object
        rtn = Return()
        rtn.periodKey = "18A1"
        rtn.vatDueSales = 100.0
        rtn.vatDueAcquisitions = 0
        rtn.totalVatDue = 100.0
        rtn.vatReclaimedCurrPeriod = 50.0
        rtn.netVatDue = 50.0
        rtn.totalValueSalesExVAT = 500
        rtn.totalValuePurchasesExVAT = 250
        rtn.totalValueGoodsSuppliedExVAT = 0
        rtn.totalAcquisitionsExVAT = 0
        rtn.finalised = True
        
        mock_response = {
            "processingDate": "2023-05-07T10:00:00Z",
            "paymentIndicator": "DD",
            "formBundleNumber": "123456789012"
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 201
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_resp
            
            result = await vat_client.submit_vat_return("123456789", rtn)
        
        assert result["formBundleNumber"] == "123456789012"
    
    @pytest.mark.asyncio
    async def test_submit_vat_return_error(self, vat_client):
        """Test submit_vat_return with error response"""
        rtn = Return()
        rtn.periodKey = "18A1"
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 400
            mock_resp.json = AsyncMock(return_value={"message": "Invalid return"})
            
            mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_resp
            
            with pytest.raises(RuntimeError) as exc_info:
                await vat_client.submit_vat_return("123456789", rtn)
            
            assert "Invalid return" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_vat_liabilities(self, vat_client):
        """Test get_vat_liabilities method"""
        mock_response = {
            "liabilities": [
                {
                    "taxPeriod": {
                        "from": "2023-01-01",
                        "to": "2023-03-31"
                    },
                    "type": "VAT",
                    "originalAmount": 1000.0,
                    "outstandingAmount": 500.0,
                    "due": "2023-05-07"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            start = date(2023, 1, 1)
            end = date(2023, 12, 31)
            result = await vat_client.get_vat_liabilities("123456789", start, end)
        
        assert len(result) == 1
        assert isinstance(result[0], Liability)
        assert result[0].original == 1000.0
        assert result[0].outstanding == 500.0
    
    @pytest.mark.asyncio
    async def test_get_vat_payments(self, vat_client):
        """Test get_vat_payments method"""
        mock_response = {
            "payments": [
                {
                    "amount": 1000.0,
                    "received": "2023-05-07"
                },
                {
                    "amount": 500.0,
                    "received": "2023-06-07"
                }
            ]
        }
        
        with patch('aiohttp.ClientSession') as mock_session:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value=mock_response)
            
            mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_resp
            
            start = date(2023, 1, 1)
            end = date(2023, 12, 31)
            result = await vat_client.get_vat_payments("123456789", start, end)
        
        assert len(result) == 2
        assert all(isinstance(p, Payment) for p in result)
        assert result[0].amount == 1000.0
        assert result[1].amount == 500.0


class TestVatTest:
    """Test the VatTest class"""
    
    def test_init(self):
        """Test VatTest initialization"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        mock_user = MagicMock()
        
        vat = VatTest(mock_config, mock_auth, mock_user)
        
        assert vat.config == mock_config
        assert vat.auth == mock_auth
        assert vat.user == mock_user
        assert vat.oauth_base == 'https://test-www.tax.service.gov.uk'
        assert vat.api_base == 'https://test-api.service.hmrc.gov.uk'


class TestVatLocalTest:
    """Test the VatLocalTest class"""
    
    def test_init(self):
        """Test VatLocalTest initialization"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        mock_user = MagicMock()
        
        vat = VatLocalTest(mock_config, mock_auth, mock_user)
        
        assert vat.config == mock_config
        assert vat.auth == mock_auth
        assert vat.user == mock_user
        assert vat.oauth_base == 'http://localhost:8080'
        assert vat.api_base == 'http://localhost:8080'


class TestCreate:
    """Test the create factory function"""
    
    def test_create_prod(self):
        """Test creating production Vat instance"""
        mock_config = MagicMock()
        mock_config.get.return_value = "prod"
        mock_auth = MagicMock()
        mock_user = MagicMock()
        
        result = create(mock_config, mock_auth, mock_user)
        
        assert isinstance(result, Vat)
        assert not isinstance(result, (VatTest, VatLocalTest))
    
    def test_create_test(self):
        """Test creating test Vat instance"""
        mock_config = MagicMock()
        mock_config.get.return_value = "test"
        mock_auth = MagicMock()
        mock_user = MagicMock()
        
        result = create(mock_config, mock_auth, mock_user)
        
        assert isinstance(result, VatTest)
    
    def test_create_local(self):
        """Test creating local test Vat instance"""
        mock_config = MagicMock()
        mock_config.get.return_value = "local"
        mock_auth = MagicMock()
        mock_user = MagicMock()
        
        result = create(mock_config, mock_auth, mock_user)
        
        assert isinstance(result, VatLocalTest)
    
    def test_create_unknown_profile(self):
        """Test create with unknown profile"""
        mock_config = MagicMock()
        mock_config.get.return_value = "unknown"
        mock_auth = MagicMock()
        mock_user = MagicMock()
        
        with pytest.raises(RuntimeError) as exc_info:
            create(mock_config, mock_auth, mock_user)
        
        assert "Profile 'unknown' is not known" in str(exc_info.value)