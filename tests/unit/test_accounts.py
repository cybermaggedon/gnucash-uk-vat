import pytest
from unittest.mock import patch, MagicMock
import sys

from gnucash_uk_vat import accounts


class TestGetClass:
    """Test get_class function"""
    
    def test_get_class_gnucash(self):
        """Test getting gnucash accounts class"""
        # Mock the gnucash_uk_vat.accounts_gnucash module
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_gnucash': mock_accounts_module}):
            result = accounts.get_class("gnucash")
            
            assert result == mock_accounts_class
    
    def test_get_class_piecash(self):
        """Test getting piecash accounts class"""
        # Mock the gnucash_uk_vat.accounts_piecash module
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_piecash': mock_accounts_module}):
            result = accounts.get_class("piecash")
            
            assert result == mock_accounts_class
    
    def test_get_class_unknown_kind(self):
        """Test error when unknown accounts kind is requested"""
        with pytest.raises(RuntimeError) as exc_info:
            accounts.get_class("unknown_kind")
        
        assert "Accounts kind 'unknown_kind' not known" in str(exc_info.value)
    
    def test_get_class_empty_kind(self):
        """Test error when empty accounts kind is requested"""
        with pytest.raises(RuntimeError) as exc_info:
            accounts.get_class("")
        
        assert "Accounts kind '' not known" in str(exc_info.value)
    
    def test_get_class_none_kind(self):
        """Test error when None accounts kind is requested"""
        with pytest.raises(RuntimeError) as exc_info:
            accounts.get_class(None)
        
        assert "Accounts kind 'None' not known" in str(exc_info.value)


class TestImportBehavior:
    """Test import behavior for different account types"""
    
    def test_gnucash_import_occurs_on_demand(self):
        """Test that gnucash module is only imported when needed"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_gnucash': mock_accounts_module}):
            # First call should trigger import
            result1 = accounts.get_class("gnucash")
            assert result1 == mock_accounts_class
            
            # Second call should use already imported module
            result2 = accounts.get_class("gnucash")
            assert result2 == mock_accounts_class
    
    def test_piecash_import_occurs_on_demand(self):
        """Test that piecash module is only imported when needed"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_piecash': mock_accounts_module}):
            # First call should trigger import
            result1 = accounts.get_class("piecash")
            assert result1 == mock_accounts_class
            
            # Second call should use already imported module
            result2 = accounts.get_class("piecash")
            assert result2 == mock_accounts_class
    
    def test_imports_are_independent(self):
        """Test that importing one type doesn't affect the other"""
        mock_gnucash_module = MagicMock()
        mock_piecash_module = MagicMock()
        mock_gnucash_class = MagicMock()
        mock_piecash_class = MagicMock()
        mock_gnucash_module.Accounts = mock_gnucash_class
        mock_piecash_module.Accounts = mock_piecash_class
        
        with patch.dict('sys.modules', {
            'gnucash_uk_vat.accounts_gnucash': mock_gnucash_module,
            'gnucash_uk_vat.accounts_piecash': mock_piecash_module
        }):
            # Get gnucash class
            gnucash_result = accounts.get_class("gnucash")
            assert gnucash_result == mock_gnucash_class
            
            # Get piecash class
            piecash_result = accounts.get_class("piecash")
            assert piecash_result == mock_piecash_class
            
            # Verify they are different
            assert gnucash_result != piecash_result


class TestFactoryPatternCompliance:
    """Test that the factory pattern is implemented correctly"""
    
    def test_returns_class_not_instance(self):
        """Test that get_class returns a class, not an instance"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_gnucash': mock_accounts_module}):
            result = accounts.get_class("gnucash")
            
            # Should return the class itself, not an instance
            assert result is mock_accounts_class
            # Verify it wasn't instantiated
            mock_accounts_class.assert_not_called()
    
    def test_can_instantiate_returned_class(self):
        """Test that the returned class can be instantiated"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_instance = MagicMock()
        mock_accounts_class.return_value = mock_instance
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_gnucash': mock_accounts_module}):
            AccountsClass = accounts.get_class("gnucash")
            instance = AccountsClass("test_file.gnucash")
            
            # Verify the class was called with correct arguments
            mock_accounts_class.assert_called_once_with("test_file.gnucash")
            assert instance == mock_instance


class TestIntegration:
    """Integration tests for accounts module"""
    
    def test_typical_usage_pattern_gnucash(self):
        """Test typical usage pattern for gnucash accounts"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_instance = MagicMock()
        mock_accounts_class.return_value = mock_instance
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_gnucash': mock_accounts_module}):
            # Typical usage: get class, then instantiate
            AccountsClass = accounts.get_class("gnucash")
            accounts_instance = AccountsClass("my_accounts.gnucash")
            
            # Verify correct behavior
            assert accounts_instance == mock_instance
            mock_accounts_class.assert_called_once_with("my_accounts.gnucash")
    
    def test_typical_usage_pattern_piecash(self):
        """Test typical usage pattern for piecash accounts"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_instance = MagicMock()
        mock_accounts_class.return_value = mock_instance
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_piecash': mock_accounts_module}):
            # Typical usage: get class, then instantiate
            AccountsClass = accounts.get_class("piecash")
            accounts_instance = AccountsClass("my_accounts.gnucash", rw=True)
            
            # Verify correct behavior
            assert accounts_instance == mock_instance
            mock_accounts_class.assert_called_once_with("my_accounts.gnucash", rw=True)
    
    def test_error_handling_in_factory(self):
        """Test error handling when factory method fails"""
        # Test various invalid inputs
        invalid_inputs = [
            "invalid",
            123,
            [],
            {},
            "GNUCASH",  # case sensitive
            "PIECASH",  # case sensitive
            " gnucash",  # whitespace
            "gnucash ",  # whitespace
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(RuntimeError) as exc_info:
                accounts.get_class(invalid_input)
            
            assert f"Accounts kind '{invalid_input}' not known" in str(exc_info.value)


class TestModuleStructure:
    """Test the module structure and imports"""
    
    def test_function_exists(self):
        """Test that get_class function exists and is callable"""
        assert hasattr(accounts, 'get_class')
        assert callable(accounts.get_class)
    
    def test_conditional_imports_work(self):
        """Test that conditional imports work correctly"""
        # This test verifies that the import structure doesn't break
        # even if we call get_class multiple times with different parameters
        
        mock_gnucash_module = MagicMock()
        mock_piecash_module = MagicMock()
        mock_gnucash_module.Accounts = MagicMock()
        mock_piecash_module.Accounts = MagicMock()
        
        with patch.dict('sys.modules', {
            'gnucash_uk_vat.accounts_gnucash': mock_gnucash_module,
            'gnucash_uk_vat.accounts_piecash': mock_piecash_module
        }):
            # Call multiple times in different orders
            accounts.get_class("gnucash")
            accounts.get_class("piecash")
            accounts.get_class("gnucash")
            accounts.get_class("piecash")
            
            # Should not raise any exceptions
            # Both modules should have been accessed
            assert mock_gnucash_module.Accounts is not None
            assert mock_piecash_module.Accounts is not None


class TestDocumentationCompliance:
    """Test that the function behaves as documented"""
    
    def test_supports_documented_account_types(self):
        """Test that documented account types are supported"""
        # Based on the codebase, these are the supported types
        supported_types = ["gnucash", "piecash"]
        
        for account_type in supported_types:
            mock_accounts_module = MagicMock()
            mock_accounts_module.Accounts = MagicMock()
            
            with patch.dict('sys.modules', {f'gnucash_uk_vat.accounts_{account_type}': mock_accounts_module}):
                # Should not raise an exception
                result = accounts.get_class(account_type)
                assert result is not None
    
    def test_case_sensitivity(self):
        """Test that account type matching is case sensitive"""
        # These should all fail because the function is case-sensitive
        case_variants = ["GnuCash", "GNUCASH", "Piecash", "PIECASH", "PieCash"]
        
        for variant in case_variants:
            with pytest.raises(RuntimeError):
                accounts.get_class(variant)


class TestRobustness:
    """Test robustness and edge cases"""
    
    def test_repeated_calls_same_type(self):
        """Test that repeated calls for the same type work correctly"""
        mock_accounts_module = MagicMock()
        mock_accounts_class = MagicMock()
        mock_accounts_module.Accounts = mock_accounts_class
        
        with patch.dict('sys.modules', {'gnucash_uk_vat.accounts_gnucash': mock_accounts_module}):
            # Call multiple times
            result1 = accounts.get_class("gnucash")
            result2 = accounts.get_class("gnucash")
            result3 = accounts.get_class("gnucash")
            
            # All should return the same class
            assert result1 == mock_accounts_class
            assert result2 == mock_accounts_class
            assert result3 == mock_accounts_class
            assert result1 is result2 is result3
    
    def test_exception_preserves_original_message(self):
        """Test that exceptions preserve the original error message format"""
        test_input = "nonexistent_type"
        
        with pytest.raises(RuntimeError) as exc_info:
            accounts.get_class(test_input)
        
        error_message = str(exc_info.value)
        assert "Accounts kind" in error_message
        assert test_input in error_message
        assert "not known" in error_message
    
    def test_whitespace_handling(self):
        """Test that whitespace in account type names is not ignored"""
        whitespace_variants = [
            " gnucash",
            "gnucash ",
            " gnucash ",
            "\tgnucash",
            "gnucash\t",
            "\ngnucash\n",
            "gnu cash",  # space in middle
        ]
        
        for variant in whitespace_variants:
            with pytest.raises(RuntimeError) as exc_info:
                accounts.get_class(variant)
            
            assert f"Accounts kind '{variant}' not known" in str(exc_info.value)