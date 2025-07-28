"""
Utility functions for piecash testing.

This module provides helpers for working with the test-gnucash.db file
and creating test data for VAT calculations.
"""

import piecash
import warnings
from pathlib import Path
from typing import Dict, List, Optional
from datetime import date, datetime
from decimal import Decimal

# Suppress piecash SQLAlchemy warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', message='.*relationship.*overlaps.*')

TEST_DB_PATH = Path(__file__).parent / "test-gnucash.db"

class PiecashTestHelper:
    """Helper class for piecash database testing."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize with test database."""
        self.db_path = db_path or str(TEST_DB_PATH)
        self._book = None
    
    def __enter__(self):
        """Context manager entry."""
        self._book = piecash.open_book(self.db_path, readonly=True)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self._book:
            self._book.close()
            self._book = None
    
    @property
    def book(self) -> piecash.Book:
        """Get the opened book."""
        if not self._book:
            raise RuntimeError("Book not opened. Use as context manager.")
        return self._book
    
    def get_account_structure(self) -> Dict[str, List[str]]:
        """Get the account hierarchy structure for testing."""
        structure = {}
        for acc in self.book.root_account.children:
            structure[acc.name] = [child.name for child in acc.children]
        return structure
    
    def get_vat_accounts(self) -> Dict[str, str]:
        """Get VAT-related account paths from the test database."""
        vat_accounts = {}
        
        # Find VAT accounts based on test configuration
        account_map = {
            'vatDueSales': 'VAT:Output:Sales',
            'vatDueAcquisitions': 'VAT:Output:EU', 
            'totalVatDue': 'VAT:Output',
            'vatReclaimedCurrPeriod': 'VAT:Input',
            'netVatDue': 'VAT',
            'totalValueSalesExVAT': 'Income:Sales',
            'totalValuePurchasesExVAT': 'Expenses:VAT Purchases',
            'totalValueGoodsSuppliedExVAT': 'Income:Sales:EU:Goods',
            'totalAcquisitionsExVAT': 'Expenses:VAT Purchases:EU Reverse VAT',
            'liabilities': 'VAT:Liabilities',
            'bills': 'Accounts Payable'
        }
        
        for field, path in account_map.items():
            try:
                account = self.find_account_by_path(path)
                vat_accounts[field] = account.fullname if account else None
            except:
                vat_accounts[field] = None
                
        return vat_accounts
    
    def find_account_by_path(self, path: str) -> Optional[piecash.Account]:
        """Find account by colon-separated path (e.g., 'VAT:Output:Sales')."""
        parts = path.split(':')
        current = self.book.root_account
        
        for part in parts:
            found = False
            for child in current.children:
                if child.name == part:
                    current = child
                    found = True
                    break
            if not found:
                return None
        
        return current if current != self.book.root_account else None
    
    def get_transactions_in_period(self, start_date: date, end_date: date) -> List[piecash.Transaction]:
        """Get all transactions within a date range."""
        return [
            txn for txn in self.book.transactions
            if start_date <= txn.post_date <= end_date
        ]
    
    def get_splits_for_account(self, account: piecash.Account, 
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None) -> List[piecash.Split]:
        """Get splits for an account within an optional date range."""
        splits = account.splits
        
        if start_date or end_date:
            splits = [
                split for split in splits
                if (not start_date or split.transaction.post_date >= start_date) and
                   (not end_date or split.transaction.post_date <= end_date)
            ]
        
        return splits
    
    def calculate_account_balance(self, account_path: str,
                                start_date: Optional[date] = None,
                                end_date: Optional[date] = None) -> Decimal:
        """Calculate account balance for a given period."""
        account = self.find_account_by_path(account_path)
        if not account:
            return Decimal('0')
        
        splits = self.get_splits_for_account(account, start_date, end_date)
        return sum(split.value for split in splits)
    
    def get_test_data_summary(self) -> Dict:
        """Get a summary of test data for validation."""
        return {
            'total_accounts': len(list(self.book.accounts)),
            'total_transactions': len(list(self.book.transactions)),
            'root_accounts': [acc.name for acc in self.book.root_account.children],
            'vat_account_exists': self.find_account_by_path('VAT') is not None,
            'income_account_exists': self.find_account_by_path('Income') is not None,
            'expense_account_exists': self.find_account_by_path('Expenses') is not None,
        }


def create_test_config_with_piecash() -> Dict:
    """Create a test configuration that uses the piecash backend."""
    return {
        "accounts": {
            "kind": "piecash",
            "file": str(TEST_DB_PATH),
            "vatDueSales": "VAT:Output:Sales",
            "vatDueAcquisitions": "VAT:Output:EU",
            "totalVatDue": "VAT:Output", 
            "vatReclaimedCurrPeriod": "VAT:Input",
            "netVatDue": "VAT",
            "totalValueSalesExVAT": "Income:Sales",
            "totalValuePurchasesExVAT": "Expenses:VAT Purchases",
            "totalValueGoodsSuppliedExVAT": "Income:Sales:EU:Goods",
            "totalAcquisitionsExVAT": "Expenses:VAT Purchases:EU Reverse VAT",
            "liabilities": "VAT:Liabilities",
            "bills": "Accounts Payable"
        },
        "application": {
            "profile": "test"
        }
    }


def verify_test_database() -> bool:
    """Verify that the test database has the expected structure."""
    try:
        with PiecashTestHelper() as helper:
            summary = helper.get_test_data_summary()
            
            # Basic validation
            required_checks = [
                summary['total_accounts'] > 50,  # Should have reasonable number of accounts
                summary['total_transactions'] > 0,  # Should have some transactions
                summary['vat_account_exists'],  # Must have VAT accounts
                summary['income_account_exists'],  # Must have Income accounts
                'VAT' in summary['root_accounts'],  # VAT should be a root account
                'Income' in summary['root_accounts'],  # Income should be a root account
                'Expenses' in summary['root_accounts'],  # Expenses should be a root account
            ]
            
            return all(required_checks)
            
    except Exception as e:
        print(f"Test database verification failed: {e}")
        return False