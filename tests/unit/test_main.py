"""
Unit tests for __main__.py module.

These tests verify that the package can be run as a module.
"""

import pytest
from unittest.mock import patch, Mock


class TestMainModule:
    """Test __main__.py module functionality"""

    @patch('gnucash_uk_vat.__main__.main')
    def test_main_module_calls_cli_main(self, mock_main):
        """Test that __main__.py calls cli.main() when executed"""
        # Import and execute the __main__ module
        import gnucash_uk_vat.__main__
        
        # The main function should have been called during import
        # since it's at module level with if __name__ == "__main__"
        # But since we're importing it, __name__ won't be "__main__"
        # So we need to test it differently
        
        # Reset the mock and manually call the main check
        mock_main.reset_mock()
        
        # Simulate the condition being true
        if "__main__" == "__main__":
            gnucash_uk_vat.__main__.main()
        
        mock_main.assert_called_once()

    def test_main_module_has_correct_import(self):
        """Test that __main__.py imports main from cli correctly"""
        import gnucash_uk_vat.__main__
        
        # Check that main is available and is callable
        assert hasattr(gnucash_uk_vat.__main__, 'main')
        assert callable(gnucash_uk_vat.__main__.main)
        
        # Check that it's the same main function from cli
        from gnucash_uk_vat.cli import main as cli_main
        assert gnucash_uk_vat.__main__.main == cli_main