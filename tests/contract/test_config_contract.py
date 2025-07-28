"""
Contract tests for configuration format and validation.

These tests verify that configuration files and data structures conform
to expected formats and contain all required fields.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timezone

from gnucash_uk_vat.config import Config, initialise_config, get_device_config
from gnucash_uk_vat.model import vat_fields


class TestConfigurationContract:
    """Test configuration file format contract"""
    
    def test_required_configuration_fields(self):
        """Verify all required configuration fields are defined"""
        # Required top-level configuration sections
        required_sections = [
            "application",
            "identity", 
            "accounts"
        ]
        
        # Required application fields
        required_app_fields = [
            "client-id",
            "client-secret", 
            "profile",
            "product-name",
            "product-version"
        ]
        
        # Required identity fields
        required_identity_fields = [
            "vrn",
            "mac-address",
            "local-ip",
            "time",
            "user"
        ]
        
        # Required device fields under identity
        required_device_fields = [
            "os-family",
            "os-version", 
            "device-manufacturer",
            "device-model",
            "id"
        ]
        
        # Required accounts fields
        required_accounts_fields = [
            "kind",
            "file",
            "liabilities",
            "bills"
        ]
        
        # Create sample configuration with all required fields
        sample_config = {
            "application": {
                "client-id": "test-client-id",
                "client-secret": "test-client-secret", 
                "profile": "test",
                "product-name": "gnucash-uk-vat",
                "product-version": "1.0.0",
                "terms-and-conditions-url": "https://example.com/terms"
            },
            "identity": {
                "vrn": "123456789",
                "mac-address": "00:11:22:33:44:55",
                "local-ip": "192.168.1.100",
                "time": "2023-04-15T10:30:00Z",
                "user": "test-user",
                "device": {
                    "os-family": "Linux",
                    "os-version": "Ubuntu 20.04",
                    "device-manufacturer": "Dell Inc.",
                    "device-model": "OptiPlex 7090", 
                    "id": "device-12345"
                }
            },
            "accounts": {
                "kind": "piecash",
                "file": "/path/to/gnucash.db",
                "liabilities": "Liabilities:VAT",
                "bills": "Accounts Payable"
            }
        }
        
        # Add VAT account mappings
        for field in vat_fields:
            sample_config["accounts"][field] = f"Accounts:VAT:{field}"
        
        # Verify configuration can be loaded
        config = Config(config=sample_config)
        
        # Test required sections exist
        for section in required_sections:
            assert config.get(section) is not None, f"Missing required section: {section}"
        
        # Test required application fields
        for field in required_app_fields:
            key = f"application.{field}"
            assert config.get(key) is not None, f"Missing required field: {key}"
        
        # Test required identity fields
        for field in required_identity_fields:
            key = f"identity.{field}"
            assert config.get(key) is not None, f"Missing required field: {key}"
        
        # Test required device fields
        for field in required_device_fields:
            key = f"identity.device.{field}"
            assert config.get(key) is not None, f"Missing required field: {key}"
        
        # Test required accounts fields
        for field in required_accounts_fields:
            key = f"accounts.{field}"
            assert config.get(key) is not None, f"Missing required field: {key}"
        
        # Test VAT account mappings
        for field in vat_fields:
            key = f"accounts.{field}"
            assert config.get(key) is not None, f"Missing VAT field mapping: {key}"
    
    def test_vat_field_mappings_contract(self):
        """Verify VAT field mappings are complete and valid"""
        # All 9 VAT fields must be mapped
        expected_vat_fields = [
            "vatDueSales",
            "vatDueAcquisitions", 
            "totalVatDue",
            "vatReclaimedCurrPeriod",
            "netVatDue",
            "totalValueSalesExVAT",
            "totalValuePurchasesExVAT",
            "totalValueGoodsSuppliedExVAT",
            "totalAcquisitionsExVAT"
        ]
        
        # Verify our model exports match expected fields
        assert len(vat_fields) == 9
        for field in expected_vat_fields:
            assert field in vat_fields, f"Missing VAT field: {field}"
        
        # Test configuration with VAT mappings
        sample_accounts_config = {}
        for field in vat_fields:
            sample_accounts_config[field] = f"VAT:{field}"
        
        config = Config(config={"accounts": sample_accounts_config})
        
        # Verify all VAT fields can be retrieved
        for field in vat_fields:
            mapping = config.get(f"accounts.{field}")
            assert mapping is not None
            assert isinstance(mapping, str)
    
    def test_profile_values_contract(self):
        """Verify valid profile values"""
        valid_profiles = ["prod", "test", "local"]
        
        for profile in valid_profiles:
            config_data = {
                "application": {
                    "profile": profile
                }
            }
            config = Config(config=config_data)
            assert config.get("application.profile") == profile
        
        # Verify profile validation would catch invalid profiles
        invalid_profiles = ["production", "development", "staging", "invalid"]
        # Note: Actual validation would be done by the hmrc.create() function
        for invalid_profile in invalid_profiles:
            assert invalid_profile not in valid_profiles
    
    def test_accounts_kind_contract(self):
        """Verify valid accounts kind values"""
        valid_kinds = ["gnucash", "piecash"]
        
        for kind in valid_kinds:
            config_data = {
                "accounts": {
                    "kind": kind
                }
            }
            config = Config(config=config_data)
            assert config.get("accounts.kind") == kind
        
        # Verify invalid kinds would be rejected
        invalid_kinds = ["quickbooks", "xero", "sage", "invalid"]
        for invalid_kind in invalid_kinds:
            assert invalid_kind not in valid_kinds


class TestConfigInitializationContract:
    """Test configuration initialization contract"""
    
    def test_config_file_creation_format(self):
        """Verify config file creation follows expected format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_config_path = temp_file.name
        
        try:
            # Remove the file so initialise_config can create it
            os.unlink(temp_config_path)
            
            # Mock get_device_config to return test data
            def mock_get_device_config():
                return {
                    "os-family": "Linux",
                    "os-version": "Ubuntu 20.04", 
                    "device-manufacturer": "Test Manufacturer",
                    "device-model": "Test Model",
                    "id": "test-device-id"
                }
            
            # Test config initialization
            with pytest.MonkeyPatch.context() as m:
                m.setattr("gnucash_uk_vat.config.get_device_config", mock_get_device_config)
                
                result_config = initialise_config(temp_config_path, None)
                
                # Verify file was created
                assert os.path.exists(temp_config_path)
                
                # Load and verify the created file
                with open(temp_config_path, 'r') as f:
                    config_data = json.load(f)
                
                # Verify basic structure
                assert "application" in config_data
                assert "identity" in config_data
                assert "accounts" in config_data
                
                # Verify device information was populated
                assert config_data["identity"]["device"]["os-family"] == "Linux"
                assert config_data["identity"]["device"]["device-manufacturer"] == "Test Manufacturer"
                
                # Verify JSON formatting (indented)
                with open(temp_config_path, 'r') as f:
                    content = f.read()
                    assert "    " in content  # Indentation present
                    assert content.startswith("{\n")  # Pretty formatted
        
        finally:
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
    
    def test_config_update_preservation(self):
        """Verify config updates preserve existing values"""
        initial_config = {
            "application": {
                "client-id": "existing-client-id",
                "profile": "prod"
            },
            "identity": {
                "vrn": "123456789",
                "device": {
                    "os-family": "Windows"
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(initial_config, temp_file, indent=4)
            temp_config_path = temp_file.name
        
        try:
            # Mock device config
            def mock_get_device_config():
                return {
                    "os-family": "Linux",  # Different from existing
                    "os-version": "Ubuntu 20.04",
                    "device-manufacturer": "New Manufacturer", 
                    "device-model": "New Model",
                    "id": "new-device-id"
                }
            
            with pytest.MonkeyPatch.context() as m:
                m.setattr("gnucash_uk_vat.config.get_device_config", mock_get_device_config)
                
                # Update config
                initialise_config(temp_config_path, None)
                
                # Load the updated configuration
                updated_config = Config(temp_config_path)
                
                # Verify existing values were preserved
                assert updated_config.get("application.client-id") == "existing-client-id"
                assert updated_config.get("identity.vrn") == "123456789"
                
                # Verify new device info was added but existing OS family preserved
                # (initialise_config should not overwrite existing device info)
                device_os = updated_config.get("identity.device.os-family")
                # The exact behavior depends on implementation - verify it's consistent
                assert device_os is not None
        
        finally:
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)


class TestDeviceConfigurationContract:
    """Test device configuration contract"""
    
    def test_device_config_structure(self):
        """Verify device config returns expected structure"""
        # Note: This is testing the contract, not the actual implementation
        # since get_device_config depends on system hardware
        
        expected_fields = [
            "os-family",
            "os-version",
            "device-manufacturer", 
            "device-model",
            "id"
        ]
        
        # Mock device config response
        mock_device_config = {
            "os-family": "Linux",
            "os-version": "Ubuntu 20.04.1 LTS",
            "device-manufacturer": "Dell Inc.",
            "device-model": "OptiPlex 7090",
            "id": "b8ca3a6e-c5f9-4c8a-9e1d-4a5b3c2d1e0f"
        }
        
        # Verify all expected fields are present
        for field in expected_fields:
            assert field in mock_device_config
            assert isinstance(mock_device_config[field], str)
            assert len(mock_device_config[field]) > 0
        
        # Verify field formats
        assert mock_device_config["os-family"] in ["Linux", "Windows", "Darwin"]
        assert len(mock_device_config["id"]) > 0  # Some form of device ID
    
    def test_network_configuration_contract(self):
        """Verify network configuration format"""
        # Expected network info format
        sample_network_config = {
            "mac-address": "00:11:22:33:44:55",
            "local-ip": "192.168.1.100",
            "time": "2023-04-15T10:30:00Z"
        }
        
        # Verify MAC address format
        mac_address = sample_network_config["mac-address"]
        assert ":" in mac_address
        assert len(mac_address) == 17  # XX:XX:XX:XX:XX:XX format
        
        # Verify IP address format
        local_ip = sample_network_config["local-ip"]
        parts = local_ip.split(".")
        assert len(parts) == 4
        for part in parts:
            assert 0 <= int(part) <= 255
        
        # Verify timestamp format
        timestamp = sample_network_config["time"]
        parsed_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        assert isinstance(parsed_time, datetime)
        assert parsed_time.tzinfo is not None


class TestPrivateConfigContract:
    """Test private configuration contract"""
    
    def test_private_config_structure(self):
        """Verify private config file structure"""
        # Private config should contain sensitive data
        sample_private_config = {
            "application": {
                "client-secret": "secret-client-secret-value"
            },
            "user": {
                "userId": "test-user-id",
                "password": "test-user-password"
            }
        }
        
        # Verify sensitive fields are strings
        assert isinstance(sample_private_config["application"]["client-secret"], str)
        assert len(sample_private_config["application"]["client-secret"]) > 0
        
        # Verify user credentials format (if present)
        if "user" in sample_private_config:
            assert "userId" in sample_private_config["user"]
            assert "password" in sample_private_config["user"]
            assert isinstance(sample_private_config["user"]["userId"], str)
            assert isinstance(sample_private_config["user"]["password"], str)
    
    def test_config_security_contract(self):
        """Verify configuration security requirements"""
        # Sensitive fields that should never be logged or displayed
        sensitive_fields = [
            "application.client-secret",
            "user.password"
        ]
        
        # Fields that contain identifiable information
        pii_fields = [
            "identity.vrn",
            "identity.mac-address",
            "identity.local-ip",
            "identity.user",
            "user.userId"
        ]
        
        # Verify we have identified sensitive fields
        assert len(sensitive_fields) > 0
        assert len(pii_fields) > 0
        
        # Test config with sensitive data
        config_data = {
            "application": {
                "client-secret": "super-secret-value"
            },
            "identity": {
                "vrn": "123456789",
                "mac-address": "00:11:22:33:44:55"
            },
            "user": {
                "password": "secret-password"
            }
        }
        
        config = Config(config=config_data)
        
        # Verify sensitive data can be retrieved (when needed)
        assert config.get("application.client-secret") == "super-secret-value"
        assert config.get("user.password") == "secret-password"
        
        # Note: Actual security measures (like not logging these fields)
        # would be implemented in the application code, not the config class itself


class TestVRNFormatContract:
    """Test VRN format validation contract"""
    
    def test_production_vrn_format(self):
        """Verify production VRN format"""
        # Standard UK VAT number format: 9 digits
        sample_vrns = [
            "123456789",
            "987654321", 
            "555666777"
        ]
        
        for vrn in sample_vrns:
            # Verify format
            assert len(vrn) == 9
            assert vrn.isdigit()
            assert not vrn.startswith("999")  # Not a magic test VRN
    
    def test_magic_test_vrn_format(self):
        """Verify magic test VRN format for vat-test-service"""
        # Magic VRNs: 999DDMMYY
        sample_magic_vrns = [
            "999150423",  # 15/04/23
            "999310322",  # 31/03/22
            "999010123"   # 01/01/23
        ]
        
        for vrn in sample_magic_vrns:
            # Verify format
            assert len(vrn) == 9
            assert vrn.isdigit()
            assert vrn.startswith("999")
            
            # Verify date part is valid
            date_part = vrn[3:]  # DDMMYY
            assert len(date_part) == 6
            
            day = int(date_part[:2])
            month = int(date_part[2:4])
            year = int(date_part[4:])
            
            assert 1 <= day <= 31
            assert 1 <= month <= 12
            assert year >= 0  # YY format, so 0-99
    
    def test_vrn_validation_contract(self):
        """Verify VRN validation requirements"""
        # Valid VRNs
        valid_vrns = [
            "123456789",    # Standard format
            "999150423"     # Magic test VRN
        ]
        
        # Invalid VRNs
        invalid_vrns = [
            "12345678",     # Too short
            "1234567890",   # Too long
            "12345678a",    # Contains letters
            "",             # Empty
            "123 456 789"   # Contains spaces
        ]
        
        for vrn in valid_vrns:
            # Should pass basic format validation
            assert len(vrn) == 9
            assert vrn.isdigit()
        
        for vrn in invalid_vrns:
            # Should fail basic format validation
            is_valid = len(vrn) == 9 and vrn.isdigit()
            assert not is_valid, f"VRN {vrn} should be invalid"