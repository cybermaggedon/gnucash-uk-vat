"""
Unit tests for the piecash accounts backend.

These tests focus on the accounts_piecash module functionality
and its integration with the piecash library.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import date
import tempfile
import json
from pathlib import Path

from gnucash_uk_vat.config import Config
from gnucash_uk_vat.accounts import get_class
from tests.fixtures.piecash_utils import create_test_config_with_piecash


class TestAccountsPiecashUnit:
    """Unit tests for piecash accounts backend."""
    
    @pytest.fixture
    def piecash_config(self):
        """Create test configuration."""
        config_data = create_test_config_with_piecash()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
        
        yield Config(f)
        
        # Cleanup
        f.unlink()
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_accounts_initialization(self, mock_piecash, piecash_config):
        """Test accounts backend initialization."""
        mock_book = Mock()
        mock_piecash.open_book.return_value = mock_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config.get("accounts.file"))
        
        # Should open the book with correct parameters
        mock_piecash.open_book.assert_called_once_with(
            piecash_config.get("accounts.file"), 
            readonly=True
        )
        
        assert accounts is not None
        assert accounts.book is mock_book
    
    def test_backend_selection(self):
        """Test that the correct backend class is returned."""
        accounts_class = get_class("piecash")
        
        # Should import and return the piecash accounts class
        from gnucash_uk_vat import accounts_piecash
        assert accounts_class == accounts_piecash.Accounts
    
    def test_invalid_backend_selection(self):
        """Test error handling for invalid backend selection."""
        with pytest.raises(RuntimeError, match="Accounts kind 'invalid' not known"):
            get_class("invalid")
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_readonly_mode_default(self, mock_piecash, piecash_config):
        """Test that accounts are opened in readonly mode by default."""
        mock_book = Mock()
        mock_piecash.open_book.return_value = mock_book
        
        accounts_class = get_class("piecash")
        accounts_class(piecash_config.get("accounts.file"))
        
        # Should open in readonly mode by default (rw=False)
        mock_piecash.open_book.assert_called_once_with(
            piecash_config.get("accounts.file"),
            readonly=True
        )
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_readwrite_mode(self, mock_piecash, piecash_config):
        """Test that accounts can be opened in read-write mode."""
        mock_book = Mock()
        mock_piecash.open_book.return_value = mock_book
        
        accounts_class = get_class("piecash")
        accounts_class(piecash_config.get("accounts.file"), rw=True)
        
        # Should open in read-write mode when rw=True
        mock_piecash.open_book.assert_called_once_with(
            piecash_config.get("accounts.file"),
            readonly=False
        )


class TestAccountsPiecashEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def piecash_config(self):
        """Create test configuration."""
        config_data = create_test_config_with_piecash()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
        
        yield Config(f)
        
        f.unlink()
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_file_not_found(self, mock_piecash, piecash_config):
        """Test behavior when database file doesn't exist."""
        mock_piecash.open_book.side_effect = FileNotFoundError("File not found")
        
        accounts_class = get_class("piecash")
        
        with pytest.raises(FileNotFoundError):
            accounts_class(piecash_config.get("accounts.file"))
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_corrupted_database(self, mock_piecash, piecash_config):
        """Test behavior with corrupted database."""
        mock_piecash.open_book.side_effect = Exception("Database corrupted")
        
        accounts_class = get_class("piecash")
        
        with pytest.raises(Exception, match="Database corrupted"):
            accounts_class(piecash_config.get("accounts.file"))
