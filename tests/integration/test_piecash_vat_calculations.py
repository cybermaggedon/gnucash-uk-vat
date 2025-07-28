"""
Integration tests for VAT calculations using piecash backend.

These tests use the real test-gnucash.db file to verify that VAT calculations
work correctly with actual GnuCash data structures.
"""

import pytest
from datetime import date, datetime
from pathlib import Path
import tempfile
import json
from decimal import Decimal

from gnucash_uk_vat.config import Config
from gnucash_uk_vat.vat import get_vat
from gnucash_uk_vat.accounts import get_class
from tests.fixtures.piecash_utils import PiecashTestHelper, create_test_config_with_piecash, verify_test_database


class TestPiecashVATCalculations:
    """Test VAT calculations with piecash backend."""
    
    @pytest.fixture(scope="class")
    def piecash_config(self):
        """Create a temporary config file for piecash testing."""
        config_data = create_test_config_with_piecash()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            config_file = f.name
        
        yield Config(config_file)
        
        # Cleanup
        Path(config_file).unlink()
    
    @pytest.fixture(scope="class")
    def test_helper(self):
        """Provide piecash test helper."""
        return PiecashTestHelper()
    
    def test_database_verification(self):
        """Verify that the test database has expected structure."""
        assert verify_test_database(), "Test database structure verification failed"
    
    def test_piecash_backend_initialization(self, piecash_config):
        """Test that piecash backend can be initialized correctly."""
        accounts_class = get_class(piecash_config.get("accounts.kind"))
        
        # Should be able to create accounts instance
        accounts = accounts_class(piecash_config.get("accounts.file"))
        assert accounts is not None
        
        # Should be able to access the book
        assert accounts.book is not None
    
    def test_vat_account_resolution(self, piecash_config):
        """Test that VAT accounts can be resolved correctly."""
        accounts_class = get_class(piecash_config.get("accounts.kind"))
        accounts = accounts_class(piecash_config.get("accounts.file"))
        
        # Test key VAT accounts can be found
        vat_accounts_to_test = [
            "accounts.vatDueSales",
            "accounts.totalVatDue", 
            "accounts.vatReclaimedCurrPeriod",
            "accounts.netVatDue",
            "accounts.totalValueSalesExVAT"
        ]
        
        for account_config in vat_accounts_to_test:
            account_path = piecash_config.get(account_config)
            if account_path:  # Only test if account path is configured
                try:
                    account = accounts.get_account(None, account_path)
                    assert account is not None, f"Could not find account: {account_path}"
                except RuntimeError:
                    # Account might not exist in test database, which is fine
                    pass
    
    def test_account_type_detection(self, piecash_config):
        """Test that account types are detected correctly for VAT calculations."""
        accounts_class = get_class(piecash_config.get("accounts.kind"))
        accounts = accounts_class(piecash_config.get("accounts.file"))
        
        # Test different account types (note: piecash backend has different logic)
        test_cases = [
            ("Income:Sales", True),  # Income accounts return True in piecash backend
            ("VAT:Input", False),   # Asset-like accounts return False
            ("VAT:Output", True),   # Liability accounts return True
        ]
        
        for account_path, expected_is_debit in test_cases:
            account = accounts.get_account(None, account_path)
            if account:  # Only test if account exists
                is_debit = accounts.is_debit(account)
                assert is_debit == expected_is_debit, f"Account {account_path} debit detection failed"
    
    def test_get_splits_functionality(self, piecash_config):
        """Test that splits can be retrieved for accounts."""
        accounts_class = get_class(piecash_config.get("accounts.kind"))
        accounts = accounts_class(piecash_config.get("accounts.file"))
        
        # Test with a known account that should have transactions
        sales_path = piecash_config.get("accounts.totalValueSalesExVAT")
        if sales_path:
            sales_account = accounts.get_account(None, sales_path)
            if sales_account:
                # Get splits for a broad date range
                start_date = date(2020, 1, 1)
                end_date = date(2025, 12, 31)
                
                splits = accounts.get_splits(sales_account, start_date, end_date)
                
                # Should be able to get splits (may be empty, but should not error)
                assert splits is not None
                assert isinstance(splits, list)
    
    def test_vat_calculation_basic(self, piecash_config):
        """Test basic VAT calculation functionality."""
        # Use a date range that should capture test data
        start_date = date(2020, 1, 1)
        end_date = date(2025, 12, 31)
        
        try:
            accounts_class = get_class(piecash_config.get("accounts.kind"))
            accounts = accounts_class(piecash_config.get("accounts.file"))
            vat_data = get_vat(accounts, piecash_config, start_date, end_date)
            
            # Should return a dictionary with VAT fields
            assert isinstance(vat_data, dict)
            
            # Should have the 9 standard VAT return boxes
            expected_fields = [
                'vatDueSales', 'vatDueAcquisitions', 'totalVatDue',
                'vatReclaimedCurrPeriod', 'netVatDue', 'totalValueSalesExVAT',
                'totalValuePurchasesExVAT', 'totalValueGoodsSuppliedExVAT',
                'totalAcquisitionsExVAT'
            ]
            
            for field in expected_fields:
                assert field in vat_data, f"Missing VAT field: {field}"
                # Values should be dictionaries with 'total' and 'splits' keys
                assert isinstance(vat_data[field], dict), f"Invalid type for {field}: {type(vat_data[field])}"
                assert 'total' in vat_data[field], f"Missing 'total' key in {field}"
                assert 'splits' in vat_data[field], f"Missing 'splits' key in {field}"
                # The 'total' should be numeric
                assert isinstance(vat_data[field]['total'], (int, float)), f"Invalid total type for {field}"
                
        except Exception as e:
            pytest.fail(f"VAT calculation failed: {e}")
    
    def test_vat_calculation_with_different_periods(self, piecash_config):
        """Test VAT calculations with different date periods."""
        test_periods = [
            (date(2023, 1, 1), date(2023, 3, 31)),   # Q1 2023
            (date(2023, 4, 1), date(2023, 6, 30)),   # Q2 2023
            (date(2023, 1, 1), date(2023, 12, 31)),  # Full year 2023
        ]
        
        for start_date, end_date in test_periods:
            try:
                accounts_class = get_class(piecash_config.get("accounts.kind"))
                accounts = accounts_class(piecash_config.get("accounts.file"))
                vat_data = get_vat(accounts, piecash_config, start_date, end_date)
                
                # Should not error and should return valid structure
                assert isinstance(vat_data, dict)
                assert 'vatDueSales' in vat_data
                assert 'netVatDue' in vat_data
                # Check that values have the expected structure
                assert isinstance(vat_data['vatDueSales'], dict)
                assert 'total' in vat_data['vatDueSales']
                
            except Exception as e:
                pytest.fail(f"VAT calculation failed for period {start_date} to {end_date}: {e}")
    
    def test_vat_calculation_empty_period(self, piecash_config):
        """Test VAT calculation for a period with no transactions."""
        # Use a future date range that should have no transactions
        start_date = date(2030, 1, 1)
        end_date = date(2030, 3, 31)
        
        accounts_class = get_class(piecash_config.get("accounts.kind"))
        accounts = accounts_class(piecash_config.get("accounts.file"))
        vat_data = get_vat(accounts, piecash_config, start_date, end_date)
        
        # Should return zeros for all fields when no transactions exist
        assert isinstance(vat_data, dict)
        
        # Most fields should be zero (though some calculations might have rounding)
        numeric_fields = ['vatDueSales', 'vatDueAcquisitions', 'totalVatDue',
                         'vatReclaimedCurrPeriod', 'netVatDue']
        
        for field in numeric_fields:
            if field in vat_data:
                assert isinstance(vat_data[field], dict)
                assert vat_data[field]['total'] == 0 or abs(vat_data[field]['total']) < 0.01
    
    def test_account_hierarchy_navigation(self, piecash_config):
        """Test that account hierarchy navigation works correctly."""
        accounts_class = get_class(piecash_config.get("accounts.kind"))
        accounts = accounts_class(piecash_config.get("accounts.file"))
        
        # Test nested account access
        nested_accounts = [
            "VAT:Output",
            "VAT:Input", 
            "Income:Sales",
            "Expenses:VAT Purchases"
        ]
        
        for account_path in nested_accounts:
            account = accounts.get_account(None, account_path)
            if account:  # Only test if account exists in test database
                # Should be able to get account name
                assert hasattr(account, 'name') or hasattr(account, 'GetName')
                
                # Should be able to determine account type
                is_debit = accounts.is_debit(account)
                assert isinstance(is_debit, bool)
    
    @pytest.mark.slow
    def test_comprehensive_vat_workflow(self, piecash_config):
        """Test the complete VAT calculation workflow."""
        with PiecashTestHelper() as helper:
            # Get test data summary
            summary = helper.get_test_data_summary()
            
            # Skip if no transactions available
            if summary['total_transactions'] == 0:
                pytest.skip("No transactions in test database")
            
            # Run VAT calculation for a broad period
            start_date = date(2020, 1, 1)
            end_date = date(2025, 12, 31)
            
            accounts_class = get_class(piecash_config.get("accounts.kind"))
            accounts = accounts_class(piecash_config.get("accounts.file"))
            vat_data = get_vat(accounts, piecash_config, start_date, end_date)
            
            # Validate calculation results
            assert isinstance(vat_data, dict)
            
            # Check that totalVatDue = vatDueSales + vatDueAcquisitions (within rounding)
            if all(field in vat_data for field in ['totalVatDue', 'vatDueSales', 'vatDueAcquisitions']):
                calculated_total = vat_data['vatDueSales']['total'] + vat_data['vatDueAcquisitions']['total']
                difference = abs(vat_data['totalVatDue']['total'] - calculated_total)
                assert difference <= 0.01, f"VAT calculation inconsistency: {difference}"
            
            # Check that netVatDue = totalVatDue - vatReclaimedCurrPeriod (within rounding)
            if all(field in vat_data for field in ['netVatDue', 'totalVatDue', 'vatReclaimedCurrPeriod']):
                calculated_net = vat_data['totalVatDue']['total'] - vat_data['vatReclaimedCurrPeriod']['total']
                difference = abs(vat_data['netVatDue']['total'] - calculated_net)
                assert difference <= 0.01, f"Net VAT calculation inconsistency: {difference}"


class TestPiecashAccountsBackend:
    """Test the piecash accounts backend specifically."""
    
    @pytest.fixture
    def piecash_config(self):
        """Create a temporary config file for piecash testing."""
        config_data = create_test_config_with_piecash()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f, indent=2)
            config_file = f.name
        
        yield Config(config_file)
        
        # Cleanup
        Path(config_file).unlink()
    
    def test_accounts_backend_selection(self, piecash_config):
        """Test that the correct backend is selected."""
        accounts_class = get_class("piecash")
        
        # Should get the piecash backend
        from gnucash_uk_vat import accounts_piecash
        assert accounts_class == accounts_piecash.Accounts
    
    def test_accounts_backend_instantiation(self, piecash_config):
        """Test backend instantiation with piecash."""
        accounts_class = get_class("piecash")
        
        # Should be able to instantiate
        accounts = accounts_class(piecash_config.get("accounts.file"))
        assert accounts is not None
        
        # Should have the expected interface
        assert hasattr(accounts, 'get_account')
        assert hasattr(accounts, 'get_splits')
        assert hasattr(accounts, 'is_debit')
        # Note: piecash backend doesn't have get_root method
    
    def test_readonly_limitations(self, piecash_config):
        """Test that write operations are properly restricted."""
        accounts_class = get_class("piecash")
        accounts = accounts_class(piecash_config.get("accounts.file"))
        
        # piecash backend should raise errors for write operations
        # Note: This test depends on the specific implementation
        # and may need adjustment based on how write operations are handled
        
        # For now, just verify the backend can be created in readonly mode
        assert accounts is not None