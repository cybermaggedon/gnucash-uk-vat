import pytest
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import datetime

from gnucash_uk_vat.config import Config, initialise_config, get_device_config


class TestConfig:
    """Test the Config class functionality"""
    
    def test_init_with_file(self, tmp_path):
        """Test Config initialization with a JSON file"""
        # Create a test config file
        config_data = {
            "application": {
                "profile": "test",
                "client-id": "test-client-123"
            },
            "identity": {
                "vrn": "123456789"
            }
        }
        config_file = tmp_path / "test_config.json"
        config_file.write_text(json.dumps(config_data))
        
        # Load the config
        config = Config(config_file)
        
        assert config.file == config_file
        assert config.config == config_data
    
    def test_init_with_dict(self):
        """Test Config initialization with a dictionary"""
        config_data = {
            "test": "value",
            "nested": {
                "key": "value2"
            }
        }
        
        config = Config(config=config_data)
        
        assert config.config == config_data
        assert config.file == Path("config.json")  # Default file name
    
    def test_init_file_not_found(self):
        """Test Config initialization with non-existent file"""
        with pytest.raises(FileNotFoundError):
            Config(Path("non_existent_file.json"))
    
    def test_init_invalid_json(self, tmp_path):
        """Test Config initialization with invalid JSON"""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{ invalid json }")
        
        with pytest.raises(json.JSONDecodeError):
            Config(config_file)


class TestConfigGet:
    """Test the Config.get() method"""
    
    @pytest.fixture
    def config(self):
        """Create a test config object"""
        config_data = {
            "level1": {
                "level2": {
                    "level3": "deep_value",
                    "number": 42
                },
                "simple": "value"
            },
            "top_level": "top_value"
        }
        return Config(config=config_data)
    
    def test_get_top_level(self, config):
        """Test getting top-level values"""
        assert config.get("top_level") == "top_value"
    
    def test_get_nested_one_level(self, config):
        """Test getting one level nested values"""
        assert config.get("level1.simple") == "value"
    
    def test_get_nested_deep(self, config):
        """Test getting deeply nested values"""
        assert config.get("level1.level2.level3") == "deep_value"
        assert config.get("level1.level2.number") == 42
    
    def test_get_non_existent_key(self, config):
        """Test getting non-existent keys returns None"""
        assert config.get("non_existent") is None
        assert config.get("level1.non_existent") is None
        assert config.get("level1.level2.non_existent") is None
    
    def test_get_partial_path(self, config):
        """Test getting partial paths returns the sub-dictionary"""
        result = config.get("level1")
        assert isinstance(result, dict)
        assert "level2" in result
        assert "simple" in result
        
        result2 = config.get("level1.level2")
        assert isinstance(result2, dict)
        assert result2["level3"] == "deep_value"


class TestConfigSet:
    """Test the Config.set() method"""
    
    @pytest.fixture
    def config(self):
        """Create a test config object"""
        config_data = {
            "level1": {
                "level2": {
                    "existing": "value"
                }
            }
        }
        return Config(config=config_data)
    
    def test_set_top_level(self, config):
        """Test setting top-level values"""
        config.set("new_key", "new_value")
        assert config.get("new_key") == "new_value"
    
    def test_set_nested(self, config):
        """Test setting nested values"""
        config.set("level1.level2.new_nested", "nested_value")
        assert config.get("level1.level2.new_nested") == "nested_value"
        # Ensure existing values are preserved
        assert config.get("level1.level2.existing") == "value"
    
    def test_set_overwrite_existing(self, config):
        """Test overwriting existing values"""
        config.set("level1.level2.existing", "new_value")
        assert config.get("level1.level2.existing") == "new_value"
    
    def test_set_with_none_default(self, config):
        """Test setting None values (default behavior)"""
        config.set("test_key", None)
        assert config.get("test_key") is None
        assert "test_key" in config.config
    
    def test_set_with_none_apply_false(self, config):
        """Test not setting None values when applyNone=False"""
        config.set("existing_key", "existing_value")
        config.set("existing_key", None, applyNone=False)
        assert config.get("existing_key") == "existing_value"
        
        # New key should not be created
        config.set("new_key_none", None, applyNone=False)
        assert config.get("new_key_none") is None
        assert "new_key_none" not in config.config


class TestConfigWrite:
    """Test the Config.write() method"""
    
    def test_write_default_file(self, tmp_path):
        """Test writing to the default file"""
        config_file = tmp_path / "config.json"
        config_data = {"test": "value"}
        config = Config(config_file, config=config_data)
        
        config.write()
        
        # Read the written file
        written_data = json.loads(config_file.read_text())
        assert written_data == config_data
    
    def test_write_override_file(self, tmp_path):
        """Test writing to a different file"""
        config_file = tmp_path / "config.json"
        override_file = tmp_path / "override.json"
        config_data = {"test": "value"}
        config = Config(config_file, config=config_data)
        
        config.write(override_file)
        
        # Original file should not exist
        assert not config_file.exists()
        # Override file should exist
        assert override_file.exists()
        written_data = json.loads(override_file.read_text())
        assert written_data == config_data
    
    def test_write_formatted_json(self, tmp_path):
        """Test that JSON is written with proper formatting"""
        config_file = tmp_path / "config.json"
        config_data = {
            "nested": {
                "key": "value"
            }
        }
        config = Config(config_file, config=config_data)
        
        config.write()
        
        # Check that the file is properly formatted
        file_content = config_file.read_text()
        assert "    " in file_content  # Check for indentation
        assert file_content == json.dumps(config_data, indent=4)


class TestInitialiseConfig:
    """Test the initialise_config function"""
    
    @patch('gnucash_uk_vat.config.get_device_config')
    @patch('gnucash_uk_vat.config.get_gateway_mac')
    @patch('gnucash_uk_vat.config.get_gateway_ip')
    def test_create_new_config_file(self, mock_ip, mock_mac, mock_device, tmp_path):
        """Test creating a new config file when it doesn't exist"""
        mock_ip.return_value = "192.168.1.100"
        mock_mac.return_value = "aa:bb:cc:dd:ee:ff"
        mock_device.return_value = {
            'os-family': 'Linux',
            'os-version': '5.0',
            'device-manufacturer': 'Test Manufacturer',
            'device-model': 'Test Model',
            'id': 'test-device-id'
        }
        
        config_file = tmp_path / "new_config.json"
        
        # Mock os.environ.get to return a test home directory
        with patch.dict(os.environ, {'HOME': str(tmp_path)}):
            initialise_config(config_file, None)
        
        # Check that the file was created
        assert config_file.exists()
        
        # Load and verify the created config
        created_config = json.loads(config_file.read_text())
        assert "application" in created_config
        assert "identity" in created_config
        assert "accounts" in created_config
        assert created_config["identity"]["mac-address"] == "aa:bb:cc:dd:ee:ff"
        assert created_config["identity"]["local-ip"] == "192.168.1.100"
    
    @patch('gnucash_uk_vat.config.get_device_config')
    @patch('gnucash_uk_vat.config.get_gateway_mac')
    @patch('gnucash_uk_vat.config.get_gateway_ip')
    def test_update_existing_config_file(self, mock_ip, mock_mac, mock_device, tmp_path):
        """Test updating an existing config file"""
        mock_ip.return_value = "192.168.1.100"
        mock_mac.return_value = "aa:bb:cc:dd:ee:ff"
        mock_device.return_value = {
            'os-family': 'Linux',
            'os-version': '5.0',
            'device-manufacturer': 'Test Manufacturer',
            'device-model': 'Test Model',
            'id': 'test-device-id'
        }
        
        # Create an existing config file
        config_file = tmp_path / "existing_config.json"
        existing_data = {
            "application": {
                "profile": "test",
                "client-id": "existing-client"
            }
        }
        config_file.write_text(json.dumps(existing_data))
        
        with patch.dict(os.environ, {'HOME': str(tmp_path)}):
            initialise_config(config_file, None)
        
        # The file should still be written to the specified path
        assert config_file.exists()
        
        # Load the updated config
        updated_config = json.loads(config_file.read_text())
        # Should preserve existing application profile
        assert updated_config["application"]["profile"] == "test"
    
    @patch('gnucash_uk_vat.config.get_device_config')
    @patch('gnucash_uk_vat.config.get_gateway_mac')
    @patch('gnucash_uk_vat.config.get_gateway_ip')
    def test_private_config_loading(self, mock_ip, mock_mac, mock_device, tmp_path):
        """Test loading values from private config file"""
        mock_ip.return_value = "192.168.1.100"
        mock_mac.return_value = "aa:bb:cc:dd:ee:ff"
        mock_device.return_value = {
            'os-family': 'Linux',
            'os-version': '5.0',
            'device-manufacturer': 'Test Manufacturer',
            'device-model': 'Test Model',
            'id': 'test-device-id'
        }
        
        # Create a private config file
        private_config_data = {
            "application": {
                "client-id": "private-client-id",
                "client-secret": "private-secret"
            },
            "identity": {
                "vrn": "987654321"
            }
        }
        private_config_file = tmp_path / ".test_config.json"
        private_config_file.write_text(json.dumps(private_config_data))
        
        config_file = tmp_path / "test_config.json"
        
        with patch.dict(os.environ, {'HOME': str(tmp_path)}):
            initialise_config(config_file, None)
        
        # Load the created config
        created_config = json.loads(config_file.read_text())
        
        # Should use values from private config
        assert created_config["application"]["client-id"] == "private-client-id"
        assert created_config["application"]["client-secret"] == "private-secret"
    
    @patch('gnucash_uk_vat.config.get_device_config')
    @patch('gnucash_uk_vat.config.get_gateway_mac')
    @patch('gnucash_uk_vat.config.get_gateway_ip')
    def test_test_user_vrn_override(self, mock_ip, mock_mac, mock_device, tmp_path):
        """Test VRN override for test environments"""
        mock_ip.return_value = "192.168.1.100"
        mock_mac.return_value = "aa:bb:cc:dd:ee:ff"
        mock_device.return_value = {
            'os-family': 'Linux',
            'os-version': '5.0',
            'device-manufacturer': 'Test Manufacturer',
            'device-model': 'Test Model',
            'id': 'test-device-id'
        }
        
        config_file = tmp_path / "test_config.json"
        
        # Create a mock user object
        user = Config(config={"vrn": "test-vrn-123"})
        
        with patch.dict(os.environ, {'HOME': str(tmp_path)}):
            initialise_config(config_file, user)
        
        # Load the created config
        created_config = json.loads(config_file.read_text())
        
        # Should use test user VRN when profile is not 'prod'
        if created_config["application"]["profile"] != "prod":
            assert created_config["identity"]["vrn"] == "test-vrn-123"


class TestGetDeviceConfig:
    """Test the get_device_config function"""
    
    @patch('gnucash_uk_vat.config.get_device')
    @patch('platform.uname')
    def test_get_device_config_success(self, mock_uname, mock_get_device):
        """Test successful device config retrieval"""
        # Mock device info
        mock_get_device.return_value = {
            "manufacturer": "Test Manufacturer",
            "model": "Test Model"
        }
        
        # Mock platform info
        mock_uname_result = MagicMock()
        mock_uname_result.system = "Linux"
        mock_uname_result.release = "5.0.0"
        mock_uname.return_value = mock_uname_result
        
        result = get_device_config()
        
        assert result['os-family'] == "Linux"
        assert result['os-version'] == "5.0.0"
        assert result['device-manufacturer'] == "Test Manufacturer"
        assert result['device-model'] == "Test Model"
        assert 'id' in result  # UUID should be generated
    
    @patch('gnucash_uk_vat.config.get_device')
    def test_get_device_config_failure(self, mock_get_device):
        """Test device config retrieval failure"""
        mock_get_device.return_value = None
        
        with pytest.raises(RuntimeError) as exc_info:
            get_device_config()
        
        assert "Couldn't fetch device information" in str(exc_info.value)
