"""
Integration tests for OAuth authentication flow.

These tests verify the complete OAuth authentication process
using the vat-test-service mock server.
"""

import pytest
import asyncio
import aiohttp
from urllib.parse import urlparse, parse_qs

from gnucash_uk_vat.config import Config
from gnucash_uk_vat.auth import Auth
from gnucash_uk_vat.hmrc import VatLocalTest


@pytest.mark.asyncio
class TestOAuthIntegration:
    """Test OAuth authentication flow end-to-end"""
    
    async def test_authorization_url_generation(self, vat_test_service, integration_test_env):
        """Test that authorization URL is generated correctly"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        auth_url = vat_client.get_auth_url()
        
        # Parse the URL to verify it's correct
        parsed_url = urlparse(auth_url)
        query_params = parse_qs(parsed_url.query)
        
        assert parsed_url.scheme == "http"
        assert parsed_url.netloc == "localhost:8081"
        assert parsed_url.path == "/oauth/authorize"
        assert query_params["response_type"][0] == "code"
        assert query_params["client_id"][0] == "test-client-id"
        assert query_params["scope"][0] == "read:vat write:vat"
        assert query_params["redirect_uri"][0] == "http://localhost:9876/auth"
    
    async def test_authorization_endpoint_responds(self, vat_test_service, integration_test_env):
        """Test that the authorization endpoint responds correctly"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        auth_url = vat_client.get_auth_url()
        
        # Test that the authorization endpoint responds
        async with aiohttp.ClientSession() as session:
            async with session.get(auth_url) as resp:
                # Should get a redirect or success response
                assert resp.status in [200, 302]
    
    async def test_token_exchange_format(self, vat_test_service, integration_test_env):
        """Test token exchange request format"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Simulate token exchange by making direct request
        token_url = f"{vat_test_service}/oauth/token"
        
        token_data = {
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:9876/auth',
            'code': 'test-auth-code'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=token_data) as resp:
                # Should get a valid token response
                assert resp.status == 200
                token_response = await resp.json()
                
                # Verify response format
                assert "access_token" in token_response
                assert "token_type" in token_response
                assert token_response["token_type"] == "bearer"
    
    async def test_refresh_token_flow(self, vat_test_service, integration_test_env):
        """Test refresh token flow"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Test refresh token request
        token_url = f"{vat_test_service}/oauth/token"
        
        refresh_data = {
            'client_id': 'test-client-id',
            'client_secret': 'test-client-secret',
            'grant_type': 'refresh_token',
            'refresh_token': '67890'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=refresh_data) as resp:
                assert resp.status == 200
                token_response = await resp.json()
                
                # Verify refresh token response
                assert "access_token" in token_response
                assert "refresh_token" in token_response
                assert token_response["token_type"] == "bearer"
    
    async def test_invalid_credentials_handling(self, vat_test_service, integration_test_env):
        """Test handling of invalid credentials"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Test with invalid client credentials
        token_url = f"{vat_test_service}/oauth/token"
        
        invalid_data = {
            'client_id': 'invalid-client-id',
            'client_secret': 'invalid-secret',
            'grant_type': 'authorization_code',
            'redirect_uri': 'http://localhost:9876/auth',
            'code': 'test-auth-code'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=invalid_data) as resp:
                # Should get an error response
                assert resp.status == 400
                error_response = await resp.json()
                assert "error" in error_response
    
    async def test_bearer_token_usage(self, vat_test_service, integration_test_env):
        """Test using bearer token for API calls"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Test API call with bearer token
        api_url = f"{vat_test_service}/organisations/vat/999150423/obligations"
        headers = vat_client.build_fraud_headers()
        
        async with aiohttp.ClientSession() as session:
            # Add query parameters as required by HMRC API
            params = {
                'from': '2023-01-01',
                'to': '2023-12-31'
            }
            
            async with session.get(api_url, headers=headers, params=params) as resp:
                # Should get successful response with valid token
                assert resp.status == 200
                data = await resp.json()
                assert "obligations" in data
    
    async def test_invalid_token_handling(self, vat_test_service, integration_test_env):
        """Test handling of invalid bearer tokens"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        # Set invalid token
        auth.auth = {
            "access_token": "invalid-token-12345",
            "refresh_token": "67890",
            "token_type": "bearer",
            "expires": "2025-12-31T23:59:59"
        }
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Test API call with invalid token
        api_url = f"{vat_test_service}/organisations/vat/999150423/obligations"
        headers = vat_client.build_fraud_headers()
        
        async with aiohttp.ClientSession() as session:
            params = {
                'from': '2023-01-01',
                'to': '2023-12-31'
            }
            
            async with session.get(api_url, headers=headers, params=params) as resp:
                # Should get unauthorized response
                assert resp.status == 401