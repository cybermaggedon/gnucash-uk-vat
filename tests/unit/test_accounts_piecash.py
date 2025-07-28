"""
Unit tests for the piecash accounts backend.

These tests focus on the accounts_piecash module functionality
and its integration with the piecash library.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
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
    def mock_piecash_book(self):
        """Create a mock piecash book for testing."""
        mock_book = Mock()
        mock_root = Mock()
        mock_book.root_account = mock_root
        mock_book.accounts = []
        mock_book.transactions = []
        return mock_book
    
    @pytest.fixture
    def piecash_config(self):
        """Create test configuration."""
        config_data = create_test_config_with_piecash()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            config_file = f.name
        
        yield Config(config_file)
        
        # Cleanup
        Path(config_file).unlink()
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_accounts_initialization(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test accounts backend initialization."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Should open the book with correct parameters
        mock_piecash.open_book.assert_called_once_with(
            piecash_config.get("accounts.file"), 
            readonly=True
        )
        
        assert accounts is not None
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_get_root_account(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test getting root account."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        root = accounts.get_root()
        assert root == mock_piecash_book.root_account
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_get_account_simple(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test getting a simple account by name."""
        # Create mock account hierarchy
        mock_account = Mock()
        mock_account.name = "TestAccount"
        mock_piecash_book.root_account.children = [mock_account]
        
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Should find the account
        result = accounts.get_account("TestAccount")
        assert result == mock_account
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_get_account_nested(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test getting nested account by path."""
        # Create mock nested hierarchy: Root -> Parent -> Child
        mock_child = Mock()
        mock_child.name = "Child"
        mock_child.children = []
        
        mock_parent = Mock()
        mock_parent.name = "Parent"
        mock_parent.children = [mock_child]
        
        mock_piecash_book.root_account.children = [mock_parent]
        
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Should find nested account
        result = accounts.get_account("Parent:Child")
        assert result == mock_child
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_get_account_not_found(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test behavior when account is not found."""
        mock_piecash_book.root_account.children = []
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Should return None for non-existent account
        result = accounts.get_account("NonExistent")
        assert result is None
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_is_debit_detection(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test account debit/credit classification."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Test different account types
        test_cases = [
            ("ASSET", True),
            ("EXPENSE", True),
            ("LIABILITY", False),
            ("INCOME", False),
            ("EQUITY", False),
        ]
        
        for account_type, expected_is_debit in test_cases:
            mock_account = Mock()
            mock_account.type = account_type
            
            result = accounts.is_debit(mock_account)
            assert result == expected_is_debit, f"Failed for account type {account_type}"
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_get_splits(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test getting splits for an account."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        # Create mock account with splits
        mock_split1 = Mock()
        mock_split1.transaction.post_date = date(2023, 1, 15)
        mock_split1.value = 100
        
        mock_split2 = Mock()
        mock_split2.transaction.post_date = date(2023, 2, 15)
        mock_split2.value = 200
        
        mock_split3 = Mock()
        mock_split3.transaction.post_date = date(2023, 3, 15)
        mock_split3.value = 300
        
        mock_account = Mock()
        mock_account.splits = [mock_split1, mock_split2, mock_split3]
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Test getting all splits
        all_splits = accounts.get_splits(mock_account, None, None)
        assert len(all_splits) == 3
        
        # Test date filtering
        filtered_splits = accounts.get_splits(
            mock_account, 
            date(2023, 1, 1), 
            date(2023, 2, 28)
        )
        assert len(filtered_splits) == 2
        assert mock_split1 in filtered_splits
        assert mock_split2 in filtered_splits
        assert mock_split3 not in filtered_splits
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_get_splits_empty_account(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test getting splits from account with no transactions."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        mock_account = Mock()
        mock_account.splits = []
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        splits = accounts.get_splits(mock_account, None, None)
        assert splits == []
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_readonly_mode(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test that accounts are opened in readonly mode."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        accounts_class = get_class("piecash")
        accounts_class(piecash_config)
        
        # Should always open in readonly mode for piecash
        mock_piecash.open_book.assert_called_once_with(
            piecash_config.get("accounts.file"),
            readonly=True
        )
    
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


class TestAccountsPiecashEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def piecash_config(self):
        """Create test configuration."""
        config_data = create_test_config_with_piecash()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            config_file = f.name
        
        yield Config(config_file)
        
        Path(config_file).unlink()
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_file_not_found(self, mock_piecash, piecash_config):
        """Test behavior when database file doesn't exist."""
        mock_piecash.open_book.side_effect = FileNotFoundError("File not found")
        
        accounts_class = get_class("piecash")
        
        with pytest.raises(FileNotFoundError):
            accounts_class(piecash_config)
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_corrupted_database(self, mock_piecash, piecash_config):
        """Test behavior with corrupted database."""
        mock_piecash.open_book.side_effect = Exception("Database corrupted")
        
        accounts_class = get_class("piecash")
        
        with pytest.raises(Exception, match="Database corrupted"):
            accounts_class(piecash_config)
    
    @patch('gnucash_uk_vat.accounts_piecash.piecash')
    def test_account_path_with_special_characters(self, mock_piecash, piecash_config, mock_piecash_book):
        """Test account paths with special characters."""
        mock_piecash.open_book.return_value = mock_piecash_book
        
        # Create mock account with special characters
        mock_account = Mock()
        mock_account.name = "Account:With:Colons"
        mock_account.children = []
        
        mock_piecash_book.root_account.children = [mock_account]
        
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config)
        
        # Should handle account name with colons correctly
        # (This tests the edge case where account names contain the path separator)
        result = accounts.get_account("Account:With:Colons")
        assert result == mock_account