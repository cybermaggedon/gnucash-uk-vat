import pytest
import json
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock, mock_open
import tempfile

from gnucash_uk_vat.auth import Auth


class TestAuthInit:
    """Test Auth class initialization"""
    
    def test_init_with_valid_file(self, tmp_path):
        """Test Auth initialization with valid JSON file"""
        auth_data = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "expires": "2025-01-01T00:00:00"
        }
        auth_file = tmp_path / "test_auth.json"
        auth_file.write_text(json.dumps(auth_data))
        
        auth = Auth(str(auth_file))
        
        assert auth.file == str(auth_file)
        assert auth.auth == auth_data
    
    def test_init_with_non_existent_file(self):
        """Test Auth initialization with non-existent file creates empty auth"""
        auth = Auth("non_existent_auth.json")
        
        assert auth.file == "non_existent_auth.json"
        assert auth.auth == {}
    
    def test_init_with_invalid_json(self, tmp_path):
        """Test Auth initialization with invalid JSON creates empty auth"""
        auth_file = tmp_path / "invalid_auth.json"
        auth_file.write_text("{ invalid json }")
        
        auth = Auth(str(auth_file))
        
        assert auth.file == str(auth_file)
        assert auth.auth == {}
    
    def test_init_default_file(self):
        """Test Auth initialization with default filename"""
        with patch("builtins.open", side_effect=FileNotFoundError):
            auth = Auth()
            
        assert auth.file == "auth.json"
        assert auth.auth == {}


class TestAuthGet:
    """Test Auth.get() method"""
    
    @pytest.fixture
    def auth(self):
        """Create test Auth object with nested data"""
        auth = Auth()
        auth.auth = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "expires": "2025-01-01T00:00:00",
            "nested": {
                "key": "value",
                "deep": {
                    "value": 42
                }
            }
        }
        return auth
    
    def test_get_top_level(self, auth):
        """Test getting top-level values"""
        assert auth.get("access_token") == "test_token"
        assert auth.get("refresh_token") == "refresh_token"
        assert auth.get("expires") == "2025-01-01T00:00:00"
    
    def test_get_nested(self, auth):
        """Test getting nested values"""
        assert auth.get("nested.key") == "value"
        assert auth.get("nested.deep.value") == 42
    
    def test_get_non_existent_key(self, auth):
        """Test getting non-existent key raises KeyError"""
        with pytest.raises(KeyError):
            auth.get("non_existent")
        
        with pytest.raises(KeyError):
            auth.get("nested.non_existent")


class TestAuthWrite:
    """Test Auth.write() method"""
    
    def test_write_auth_data(self, tmp_path):
        """Test writing auth data to file"""
        auth_file = tmp_path / "test_auth.json"
        auth = Auth(str(auth_file))
        auth.auth = {
            "access_token": "new_token",
            "refresh_token": "new_refresh",
            "expires": "2025-12-31T23:59:59"
        }
        
        auth.write()
        
        # Read and verify written data
        written_data = json.loads(auth_file.read_text())
        assert written_data == auth.auth
        assert "access_token" in written_data
        assert written_data["access_token"] == "new_token"
    
    def test_write_formatted_json(self, tmp_path):
        """Test that JSON is written with proper formatting"""
        auth_file = tmp_path / "test_auth.json"
        auth = Auth(str(auth_file))
        auth.auth = {"key": "value", "nested": {"inner": "data"}}
        
        auth.write()
        
        # Check formatting
        file_content = auth_file.read_text()
        assert "    " in file_content  # Check for indentation
        assert file_content == json.dumps(auth.auth, indent=4)


class TestAuthRefresh:
    """Test Auth.refresh() method"""
    
    @pytest.mark.asyncio
    async def test_refresh_token(self, tmp_path):
        """Test refreshing auth token"""
        auth_file = tmp_path / "test_auth.json"
        auth = Auth(str(auth_file))
        auth.auth = {
            "access_token": "old_token",
            "refresh_token": "refresh_token",
            "expires": "2020-01-01T00:00:00"
        }
        
        # Mock service
        mock_service = AsyncMock()
        new_auth_data = {
            "access_token": "new_token",
            "refresh_token": "new_refresh_token",
            "expires": "2025-12-31T23:59:59"
        }
        mock_service.refresh_token.return_value = new_auth_data
        
        await auth.refresh(mock_service)
        
        # Verify service was called with correct refresh token
        mock_service.refresh_token.assert_called_once_with("refresh_token")
        
        # Verify auth data was updated
        assert auth.auth == new_auth_data
        
        # Verify file was written
        written_data = json.loads(auth_file.read_text())
        assert written_data == new_auth_data
    
    @pytest.mark.asyncio
    async def test_refresh_updates_auth_object(self):
        """Test that refresh updates the auth object in memory"""
        auth = Auth()
        auth.auth = {"refresh_token": "test_refresh"}
        
        mock_service = AsyncMock()
        new_auth = {
            "access_token": "new_access",
            "refresh_token": "new_refresh",
            "expires": "2025-01-01T00:00:00"
        }
        mock_service.refresh_token.return_value = new_auth
        
        with patch.object(auth, 'write'):
            await auth.refresh(mock_service)
        
        assert auth.auth == new_auth


class TestAuthMaybeRefresh:
    """Test Auth.maybe_refresh() method"""
    
    @pytest.mark.asyncio
    async def test_maybe_refresh_no_expiry(self):
        """Test maybe_refresh raises error when no expiry exists"""
        auth = Auth()
        auth.auth = {"access_token": "token"}  # No expires field
        
        mock_service = AsyncMock()
        
        with pytest.raises(RuntimeError) as exc_info:
            await auth.maybe_refresh(mock_service)
        
        assert "No token expiry" in str(exc_info.value)
        assert "Have you authenticated?" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_maybe_refresh_not_expired(self):
        """Test maybe_refresh does nothing when token not expired"""
        auth = Auth()
        future_time = datetime.utcnow() + timedelta(hours=1)
        auth.auth = {
            "access_token": "token",
            "expires": future_time.isoformat()
        }
        
        mock_service = AsyncMock()
        
        with patch.object(auth, 'refresh') as mock_refresh:
            await auth.maybe_refresh(mock_service)
        
        # Refresh should not be called
        mock_refresh.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_maybe_refresh_expired(self):
        """Test maybe_refresh calls refresh when token expired"""
        auth = Auth()
        past_time = datetime.utcnow() - timedelta(hours=1)
        auth.auth = {
            "access_token": "old_token",
            "refresh_token": "refresh_token",
            "expires": past_time.isoformat()
        }
        
        mock_service = AsyncMock()
        
        with patch.object(auth, 'refresh') as mock_refresh:
            await auth.maybe_refresh(mock_service)
        
        # Refresh should be called
        mock_refresh.assert_called_once_with(mock_service)
    
    @pytest.mark.asyncio
    async def test_maybe_refresh_exact_expiry_time(self):
        """Test maybe_refresh behavior at exact expiry time"""
        auth = Auth()
        # Set expires to current time (edge case)
        current_time = datetime.utcnow()
        auth.auth = {
            "access_token": "token",
            "refresh_token": "refresh_token",
            "expires": current_time.isoformat()
        }
        
        mock_service = AsyncMock()
        
        with patch.object(auth, 'refresh') as mock_refresh:
            with patch('gnucash_uk_vat.auth.datetime') as mock_datetime:
                # Mock datetime.utcnow to return exact same time
                mock_datetime.utcnow.return_value = current_time
                mock_datetime.fromisoformat = datetime.fromisoformat
                
                await auth.maybe_refresh(mock_service)
        
        # Should not refresh if times are exactly equal
        mock_refresh.assert_not_called()


class TestAuthIntegration:
    """Integration tests for Auth class"""
    
    @pytest.mark.asyncio
    async def test_full_auth_lifecycle(self, tmp_path):
        """Test complete auth lifecycle: init, refresh, write"""
        # Initial auth data
        initial_auth = {
            "access_token": "initial_token",
            "refresh_token": "initial_refresh",
            "expires": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }
        
        auth_file = tmp_path / "lifecycle_auth.json"
        auth_file.write_text(json.dumps(initial_auth))
        
        # Create Auth object
        auth = Auth(str(auth_file))
        
        # Verify initial load
        assert auth.get("access_token") == "initial_token"
        
        # Mock service for refresh
        mock_service = AsyncMock()
        new_auth = {
            "access_token": "refreshed_token",
            "refresh_token": "refreshed_refresh",
            "expires": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }
        mock_service.refresh_token.return_value = new_auth
        
        # Perform maybe_refresh (should trigger refresh due to expired token)
        await auth.maybe_refresh(mock_service)
        
        # Verify auth was refreshed
        assert auth.get("access_token") == "refreshed_token"
        
        # Verify file was updated
        saved_auth = json.loads(auth_file.read_text())
        assert saved_auth["access_token"] == "refreshed_token"