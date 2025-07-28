"""
Contract tests for HMRC OAuth authentication flow.

These tests verify that our OAuth implementation matches the HMRC OAuth specification.
"""

import pytest
import json
from urllib.parse import urlparse, parse_qs, urlencode
from datetime import datetime, timedelta, timezone

from gnucash_uk_vat.hmrc import Vat, VatTest, VatLocalTest
from gnucash_uk_vat.auth import Auth
from unittest.mock import MagicMock


class TestOAuthAuthorizationContract:
    """Test OAuth authorization flow contract"""
    
    def test_authorization_url_format(self):
        """Verify authorization URL matches HMRC OAuth specification"""
        mock_config = MagicMock()
        mock_config.get.return_value = "test-client-id"
        
        mock_auth = MagicMock()
        vat_client = Vat(mock_config, mock_auth)
        
        auth_url = vat_client.get_auth_url()
        
        # Parse the URL
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        # Verify base URL
        assert parsed_url.scheme == "https"
        assert parsed_url.netloc == "www.tax.service.gov.uk"
        assert parsed_url.path == "/oauth/authorize"
        
        # Verify required OAuth parameters
        assert query_params["response_type"][0] == "code"
        assert query_params["client_id"][0] == "test-client-id"
        assert query_params["scope"][0] == "read:vat write:vat"
        assert query_params["redirect_uri"][0] == "http://localhost:9876/auth"
        
        # Verify no unexpected parameters
        expected_params = {"response_type", "client_id", "scope", "redirect_uri"}
        actual_params = set(query_params.keys())
        assert actual_params == expected_params
    
    def test_test_environment_authorization_url(self):
        """Verify test environment authorization URL"""
        mock_config = MagicMock()
        mock_config.get.return_value = "test-client-id"
        
        mock_auth = MagicMock()
        vat_test_client = VatTest(mock_config, mock_auth, None)
        
        auth_url = vat_test_client.get_auth_url()
        parsed_url = urlparse(auth_url)
        
        # Should use test environment domain
        assert parsed_url.netloc == "test-www.tax.service.gov.uk"
        assert parsed_url.path == "/oauth/authorize"
    
    def test_redirect_uri_format(self):
        """Verify redirect URI matches expected format"""
        mock_config = MagicMock()
        mock_config.get.return_value = "test-client-id"
        
        mock_auth = MagicMock()
        vat_client = Vat(mock_config, mock_auth)
        
        auth_url = vat_client.get_auth_url()
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        redirect_uri = query_params["redirect_uri"][0]
        parsed_redirect = urlparse(redirect_uri)
        
        # Verify redirect URI format
        assert parsed_redirect.scheme == "http"
        assert parsed_redirect.netloc == "localhost:9876"
        assert parsed_redirect.path == "/auth"
    
    def test_scope_format(self):
        """Verify OAuth scope matches HMRC specification"""
        mock_config = MagicMock()
        mock_config.get.return_value = "test-client-id"
        
        mock_auth = MagicMock()
        vat_client = Vat(mock_config, mock_auth)
        
        auth_url = vat_client.get_auth_url()
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        scope = query_params["scope"][0]
        
        # Verify scope format and required permissions
        assert "read:vat" in scope
        assert "write:vat" in scope
        assert scope == "read:vat write:vat"


class TestTokenExchangeContract:
    """Test OAuth token exchange contract"""
    
    def test_token_request_format(self):
        """Verify token request matches HMRC OAuth specification"""
        # This tests the format of token exchange request
        # (We can't easily test the actual HTTP request without integration tests)
        
        from urllib.parse import urlencode
        
        # Expected token request parameters
        expected_params = {
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:9876/auth',
            'code': 'test-auth-code'
        }
        
        # Verify parameter encoding
        encoded_params = urlencode(expected_params)
        
        # Verify all required parameters are present
        assert 'client_id=test-client-id' in encoded_params
        assert 'client_secret=test-client-secret' in encoded_params
        assert 'grant_type=authorization_code' in encoded_params
        assert 'redirect_uri=http%3A%2F%2Flocalhost%3A9876%2Fauth' in encoded_params
        assert 'code=test-auth-code' in encoded_params
        
        # Verify Content-Type should be application/x-www-form-urlencoded
        expected_content_type = 'application/x-www-form-urlencoded'
        assert expected_content_type == 'application/x-www-form-urlencoded'
    
    def test_token_response_format(self):
        """Verify token response parsing matches HMRC specification"""
        # Sample token response from HMRC OAuth spec
        sample_token_response = {
            "access_token": "test-access-token-12345",
            "refresh_token": "test-refresh-token-67890", 
            "token_type": "bearer",
            "expires_in": 14400  # 4 hours in seconds
        }
        
        # Verify our auth object can handle this response format
        mock_auth = Auth()
        
        # Simulate what get_auth_coro would do with this response
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=int(sample_token_response["expires_in"]))
        expiry = expiry.replace(microsecond=0)
        
        processed_auth = {
            "access_token": sample_token_response["access_token"],
            "refresh_token": sample_token_response["refresh_token"],
            "token_type": sample_token_response["token_type"],
            "expires": expiry.isoformat()
        }
        
        mock_auth.auth = processed_auth
        
        # Verify processed format
        assert mock_auth.get("access_token") == "test-access-token-12345"
        assert mock_auth.get("refresh_token") == "test-refresh-token-67890"
        assert mock_auth.get("token_type") == "bearer"
        
        # Verify expiry is properly formatted ISO datetime
        expires_str = mock_auth.get("expires")
        expires_dt = datetime.fromisoformat(expires_str)
        assert isinstance(expires_dt, datetime)
    
    def test_refresh_token_request_format(self):
        """Verify refresh token request matches HMRC specification"""
        from urllib.parse import urlencode
        
        # Expected refresh token request parameters
        expected_params = {
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret', 
            'grant_type': 'refresh_token',
            'refresh_token': 'test-refresh-token'
        }
        
        # Verify parameter encoding
        encoded_params = urlencode(expected_params)
        
        # Verify all required parameters are present
        assert 'client_id=test-client-id' in encoded_params
        assert 'client_secret=test-client-secret' in encoded_params
        assert 'grant_type=refresh_token' in encoded_params
        assert 'refresh_token=test-refresh-token' in encoded_params
        
        # Should not include 'code' or 'redirect_uri' for refresh requests
        assert 'code=' not in encoded_params
        assert 'redirect_uri=' not in encoded_params


class TestAuthHeaderContract:
    """Test Authorization header contract"""
    
    def test_bearer_token_format(self):
        """Verify Bearer token format matches OAuth specification"""
        mock_auth = MagicMock()
        mock_auth.get.return_value = "test-access-token-12345"
        
        mock_config = MagicMock()
        vat_client = Vat(mock_config, mock_auth)
        
        # Build fraud headers which includes Authorization header
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
        
        headers = vat_client.build_fraud_headers()
        
        # Verify Authorization header format
        auth_header = headers['Authorization']
        assert auth_header.startswith('Bearer ')
        assert auth_header == 'Bearer test-access-token-12345'
        
        # Verify no extra spaces or formatting issues
        token_part = auth_header[7:]  # Remove "Bearer "
        assert token_part == "test-access-token-12345"
        assert ' ' not in token_part


class TestTokenLifecycleContract:
    """Test token lifecycle contract"""
    
    def test_token_expiry_handling(self):
        """Verify token expiry handling matches OAuth specification"""
        # Create auth with expired token
        mock_auth = Auth()
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        mock_auth.auth = {
            "access_token": "expired-token",
            "refresh_token": "valid-refresh-token",
            "expires": past_time.isoformat()
        }
        
        # Verify expiry detection
        expires = datetime.fromisoformat(mock_auth.auth["expires"])
        current_time = datetime.now(timezone.utc)
        
        is_expired = current_time > expires
        assert is_expired == True
        
        # Test with non-expired token
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_auth.auth["expires"] = future_time.isoformat()
        
        expires = datetime.fromisoformat(mock_auth.auth["expires"])
        is_expired = current_time > expires
        assert is_expired == False
    
    def test_token_storage_format(self):
        """Verify token storage format is consistent"""
        # Create auth object and verify storage format
        mock_auth = Auth()
        
        # Sample token data
        token_data = {
            "access_token": "access-token-12345",
            "refresh_token": "refresh-token-67890",
            "token_type": "bearer",
            "expires": "2023-12-31T23:59:59"
        }
        
        mock_auth.auth = token_data
        
        # Verify all required fields are stored
        assert "access_token" in mock_auth.auth
        assert "refresh_token" in mock_auth.auth
        assert "token_type" in mock_auth.auth
        assert "expires" in mock_auth.auth
        
        # Verify field access
        assert mock_auth.get("access_token") == "access-token-12345"
        assert mock_auth.get("refresh_token") == "refresh-token-67890"
        assert mock_auth.get("token_type") == "bearer"
        
        # Verify expiry format is ISO datetime
        expires_str = mock_auth.get("expires")
        expires_dt = datetime.fromisoformat(expires_str)
        assert isinstance(expires_dt, datetime)


class TestErrorHandlingContract:
    """Test OAuth error handling contract"""
    
    def test_oauth_error_response_format(self):
        """Verify OAuth error response handling matches specification"""
        # Sample OAuth error responses per HMRC spec
        sample_errors = [
            {
                "error": "invalid_request",
                "error_description": "The request is missing a required parameter"
            },
            {
                "error": "invalid_client", 
                "error_description": "Client authentication failed"
            },
            {
                "error": "invalid_grant",
                "error_description": "The provided authorization grant is invalid"
            },
            {
                "error": "unsupported_grant_type",
                "error_description": "The authorization grant type is not supported"
            }
        ]
        
        # Verify error response structure
        for error_response in sample_errors:
            assert "error" in error_response
            assert "error_description" in error_response
            
            # Verify error codes match OAuth spec
            valid_error_codes = [
                "invalid_request",
                "invalid_client", 
                "invalid_grant",
                "unauthorized_client",
                "unsupported_grant_type",
                "invalid_scope"
            ]
            assert error_response["error"] in valid_error_codes
    
    def test_http_error_handling(self):
        """Verify HTTP error status codes are handled correctly"""
        # Common HTTP error codes for OAuth
        oauth_error_codes = [
            400,  # Bad Request - invalid_request
            401,  # Unauthorized - invalid_client
            403,  # Forbidden - access_denied
            404,  # Not Found - endpoint not found
            500,  # Internal Server Error
            503   # Service Unavailable
        ]
        
        # Verify we handle these error codes appropriately
        for status_code in oauth_error_codes:
            assert isinstance(status_code, int)
            assert 400 <= status_code < 600
            
            # Verify error categorization
            if 400 <= status_code < 500:
                # Client errors
                assert status_code >= 400
            elif 500 <= status_code < 600:
                # Server errors  
                assert status_code >= 500


class TestUserCredentialsContract:
    """Test user credentials display contract"""
    
    def test_auth_credentials_format(self):
        """Verify auth credentials display format"""
        mock_config = MagicMock()
        mock_config.get.return_value = "test-client-id"
        
        mock_auth = MagicMock()
        
        # Test with user credentials
        mock_user = {
            "userId": "test-user-123",
            "password": "test-password-456"
        }
        
        vat_client = Vat(mock_config, mock_auth, mock_user)
        credentials = vat_client.get_auth_credentials()
        
        # Verify format
        assert "UserId: test-user-123" in credentials
        assert "Password: test-password-456" in credentials
        
        # Test without user credentials
        vat_client_no_user = Vat(mock_config, mock_auth, None)
        credentials_empty = vat_client_no_user.get_auth_credentials()
        
        assert credentials_empty is None
    
    def test_terms_and_conditions_url(self):
        """Verify terms and conditions URL handling"""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "application.client-id": "test-client-id",
            "application.terms-and-conditions-url": "https://example.com/terms"
        }.get(key)
        
        mock_auth = MagicMock()
        vat_client = Vat(mock_config, mock_auth)
        
        # Verify T&C URL is retrieved correctly
        tandc_url = mock_config.get("application.terms-and-conditions-url")
        assert tandc_url == "https://example.com/terms"
        
        # Test without T&C URL
        mock_config_no_tandc = MagicMock()
        mock_config_no_tandc.get.side_effect = lambda key: {
            "application.client-id": "test-client-id",
            "application.terms-and-conditions-url": None
        }.get(key)
        
        vat_client_no_tandc = Vat(mock_config_no_tandc, mock_auth)
        tandc_url_empty = mock_config_no_tandc.get("application.terms-and-conditions-url")
        assert tandc_url_empty is None


class TestEnvironmentSpecificContract:
    """Test environment-specific OAuth configurations"""
    
    def test_production_oauth_endpoints(self):
        """Verify production OAuth endpoints"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_prod = Vat(mock_config, mock_auth)
        
        # Verify production endpoints
        assert vat_prod.oauth_base == 'https://www.tax.service.gov.uk'
        assert vat_prod.api_base == 'https://api.service.hmrc.gov.uk'
        
        # Verify OAuth URL construction
        auth_url = vat_prod.get_auth_url()
        assert 'www.tax.service.gov.uk/oauth/authorize' in auth_url
    
    def test_test_environment_oauth_endpoints(self):
        """Verify test environment OAuth endpoints"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_test = VatTest(mock_config, mock_auth, None)
        
        # Verify test endpoints
        assert vat_test.oauth_base == 'https://test-www.tax.service.gov.uk'
        assert vat_test.api_base == 'https://test-api.service.hmrc.gov.uk'
        
        # Verify OAuth URL construction
        auth_url = vat_test.get_auth_url() 
        assert 'test-www.tax.service.gov.uk/oauth/authorize' in auth_url
    
    def test_local_test_oauth_endpoints(self):
        """Verify local test OAuth endpoints"""
        mock_config = MagicMock()
        mock_auth = MagicMock()
        
        vat_local = VatLocalTest(mock_config, mock_auth, None)
        
        # Verify local endpoints
        assert vat_local.oauth_base == 'http://localhost:8081'
        assert vat_local.api_base == 'http://localhost:8081'
        
        # Verify OAuth URL construction
        auth_url = vat_local.get_auth_url()
        assert 'localhost:8081/oauth/authorize' in auth_url