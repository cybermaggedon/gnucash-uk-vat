import pytest
from unittest.mock import MagicMock, patch
from datetime import date

from gnucash_uk_vat import vat
from gnucash_uk_vat.model import vat_fields, Return


class TestGetVat:
    """Test get_vat function"""
    
    def test_get_vat_single_string_account(self):
        """Test VAT calculation with single string account locator"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        
        # Mock splits data
        test_splits = [
            {"amount": 100.0, "date": date(2023, 1, 15), "description": "Sale 1"},
            {"amount": 50.0, "date": date(2023, 2, 10), "description": "Sale 2"}
        ]
        mock_accounts.get_splits.return_value = test_splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Sales:VAT",
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify all VAT fields are present
        for field in vat_fields:
            assert field in result
            assert "splits" in result[field]
            assert "total" in result[field]
        
        # Verify splits are preserved
        assert result["vatDueSales"]["splits"] == test_splits
        assert result["vatDueSales"]["total"] == 150.0
        
        # Verify accounts.get_account was called for each field
        assert mock_accounts.get_account.call_count == 9
        assert mock_accounts.get_splits.call_count == 9
    
    def test_get_vat_list_account_locators(self):
        """Test VAT calculation with list of account locators"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account1 = MagicMock()
        mock_account2 = MagicMock()
        mock_accounts.get_account.side_effect = [mock_account1, mock_account2] * 9  # 9 VAT fields
        mock_accounts.is_debit.return_value = False
        
        # Mock splits data for multiple accounts
        splits1 = [{"amount": 100.0, "date": date(2023, 1, 15), "description": "Account 1"}]
        splits2 = [{"amount": 50.0, "date": date(2023, 2, 10), "description": "Account 2"}]
        mock_accounts.get_splits.side_effect = [splits1, splits2] * 9
        
        # Mock config with list locators
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": ["Sales:VAT:Output", "Sales:VAT:Standard"],
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify splits from multiple accounts are combined
        assert len(result["vatDueSales"]["splits"]) == 2
        assert result["vatDueSales"]["total"] == 150.0  # 100 + 50
        
        # Verify that for the list field, get_account was called twice
        # Plus 8 more times for other fields (total 10 calls: 2 + 8)
        assert mock_accounts.get_account.call_count == 10
    
    def test_get_vat_debit_account_adjustment(self):
        """Test that debit accounts have amounts negated"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = True  # This is a debit account
        
        # Mock splits data - amounts will be negated for debit accounts
        test_splits = [
            {"amount": 100.0, "date": date(2023, 1, 15), "description": "Debit entry"},
            {"amount": 50.0, "date": date(2023, 2, 10), "description": "Debit entry 2"}
        ]
        mock_accounts.get_splits.return_value = test_splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Expenses:VAT",  # Debit account
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify amounts were negated for debit account
        assert result["vatDueSales"]["splits"][0]["amount"] == -100.0
        assert result["vatDueSales"]["splits"][1]["amount"] == -50.0
        assert result["vatDueSales"]["total"] == -150.0  # Negated total
    
    def test_get_vat_pence_rounding(self):
        """Test that pence boxes (0-4) are rounded to 2 decimal places"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        
        # Mock splits with precise decimal amounts
        test_splits = [{"amount": 123.456789, "date": date(2023, 1, 15), "description": "Precise amount"}]
        mock_accounts.get_splits.return_value = test_splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Sales:VAT",
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify pence boxes (0-4) are rounded to 2 decimal places
        pence_fields = ["vatDueSales", "vatDueAcquisitions", "totalVatDue", "vatReclaimedCurrPeriod", "netVatDue"]
        for field in pence_fields:
            assert result[field]["total"] == 123.46  # Rounded to 2 decimal places
    
    def test_get_vat_pounds_rounding(self):
        """Test that pound boxes (5-8) are rounded to whole numbers"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        
        # Mock splits with decimal amounts
        test_splits = [{"amount": 1234.56, "date": date(2023, 1, 15), "description": "Amount with pence"}]
        mock_accounts.get_splits.return_value = test_splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Sales:VAT",
            "vatDueAcquisitions": "Purchases:VAT", 
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify pound boxes (5-8) are rounded to whole numbers
        pound_fields = ["totalValueSalesExVAT", "totalValuePurchasesExVAT", 
                       "totalValueGoodsSuppliedExVAT", "totalAcquisitionsExVAT"]
        for field in pound_fields:
            assert result[field]["total"] == 1235  # Rounded to whole number
    
    def test_get_vat_net_vat_due_absolute_value(self):
        """Test that netVatDue (box 4) is always positive"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        
        # Mock splits with negative amount (refund scenario)
        test_splits = [{"amount": -150.0, "date": date(2023, 1, 15), "description": "VAT refund"}]
        mock_accounts.get_splits.return_value = test_splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Sales:VAT",
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify netVatDue is absolute value (positive)
        assert result["netVatDue"]["total"] == 150.0  # Absolute value of -150.0
    
    def test_get_vat_invalid_locator_type(self):
        """Test error when account locator is neither string nor list"""
        # Mock accounts
        mock_accounts = MagicMock()
        
        # Mock config with invalid locator type
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": 123,  # Invalid type (should be string or list)
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        with pytest.raises(RuntimeError) as exc_info:
            vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        assert "Accounts should be strings or lists" in str(exc_info.value)
    
    def test_get_vat_empty_splits(self):
        """Test VAT calculation when no splits are found"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        mock_accounts.get_splits.return_value = []  # No splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Sales:VAT",
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify all fields have empty splits and zero totals
        for field in vat_fields:
            assert result[field]["splits"] == []
            assert result[field]["total"] == 0


class TestPostVatBill:
    """Test post_vat_bill function"""
    
    def test_post_vat_bill_success(self):
        """Test successful VAT bill posting"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_vendor = MagicMock()
        mock_bill = MagicMock()
        mock_liability_account = MagicMock()
        mock_bill_account = MagicMock()
        
        mock_accounts.create_bill.return_value = mock_bill
        mock_accounts.get_account.side_effect = [mock_liability_account, mock_bill_account]
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "accounts.liabilities": "Liabilities:VAT",
            "accounts.bills": "Accounts Payable"
        }[key]
        
        # Mock VAT return
        mock_vat_return = MagicMock()
        mock_vat_return.totalVatDue = 1200.0
        mock_vat_return.vatReclaimedCurrPeriod = 300.0
        
        billing_id = "VAT-2023-Q1"
        bill_date = date(2023, 4, 15)
        due_date = date(2023, 5, 15)
        notes = "VAT return for Q1 2023"
        memo = "Quarterly VAT payment"
        
        with patch('gnucash_uk_vat.vat.get_vat_vendor', return_value=mock_vendor):
            vat.post_vat_bill(mock_accounts, mock_config, billing_id, bill_date, 
                             due_date, mock_vat_return, notes, memo)
        
        # Verify bill creation
        mock_accounts.create_bill.assert_called_once_with(None, mock_vendor, bill_date, notes)
        
        # Verify account retrieval
        assert mock_accounts.get_account.call_count == 2
        mock_accounts.get_account.assert_any_call(mock_accounts.root, "Liabilities:VAT")
        mock_accounts.get_account.assert_any_call(mock_accounts.root, "Accounts Payable")
        
        # Verify bill entries creation
        assert mock_accounts.create_bill_entry.call_count == 2
        
        # First entry: VAT due
        mock_accounts.create_bill_entry.assert_any_call(
            mock_bill, bill_date, "VAT from sales and acquisitions",
            mock_liability_account, 1.0, 1200.0
        )
        
        # Second entry: VAT rebate (negative)
        mock_accounts.create_bill_entry.assert_any_call(
            mock_bill, bill_date, "VAT rebate on acquisitions",
            mock_liability_account, 1.0, -300.0
        )
        
        # Verify bill posting
        mock_accounts.post_bill.assert_called_once_with(
            mock_bill, mock_bill_account, bill_date, due_date, memo
        )
        
        # Verify save
        mock_accounts.save.assert_called_once()


class TestGetVatVendor:
    """Test get_vat_vendor function"""
    
    def test_get_vat_vendor_existing(self):
        """Test getting existing VAT vendor"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_vendor = MagicMock()
        mock_accounts.get_vendor.return_value = mock_vendor  # Vendor exists
        
        result = vat.get_vat_vendor(mock_accounts)
        
        # Verify vendor retrieval
        mock_accounts.get_vendor.assert_called_once_with("hmrc-vat")
        assert result == mock_vendor
        
        # Verify no creation or save calls
        mock_accounts.create_vendor.assert_not_called()
        mock_accounts.save.assert_not_called()
    
    def test_get_vat_vendor_create_new(self):
        """Test creating new VAT vendor when it doesn't exist"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_accounts.get_vendor.return_value = None  # Vendor doesn't exist
        
        mock_currency = MagicMock()
        mock_accounts.get_currency.return_value = mock_currency
        
        mock_new_vendor = MagicMock()
        mock_accounts.create_vendor.return_value = mock_new_vendor
        
        result = vat.get_vat_vendor(mock_accounts)
        
        # Verify vendor creation process
        mock_accounts.get_vendor.assert_called_once_with("hmrc-vat")
        mock_accounts.get_currency.assert_called_once_with("GBP")
        mock_accounts.create_vendor.assert_called_once_with(
            "hmrc-vat", mock_currency, "HM Revenue and Customs - VAT"
        )
        
        # Verify address setting
        mock_accounts.set_address.assert_called_once_with(
            mock_new_vendor,
            "VAT Written Enquiries",
            "123 St Vincent Street", 
            "Glasgow City",
            "Glasgow G2 5EA",
            "UK"
        )
        
        # Verify save
        mock_accounts.save.assert_called_once()
        
        assert result == mock_new_vendor


class TestIntegration:
    """Integration tests for vat module"""
    
    def test_complete_vat_workflow(self):
        """Test complete workflow from VAT calculation to bill posting"""
        # Mock accounts
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        
        # Mock splits representing a quarter's worth of VAT transactions
        test_splits = [
            {"amount": 200.0, "date": date(2023, 1, 15), "description": "VAT on sales"},
            {"amount": 100.0, "date": date(2023, 2, 10), "description": "VAT on sales"},
            {"amount": 150.0, "date": date(2023, 3, 20), "description": "VAT on sales"}
        ]
        mock_accounts.get_splits.return_value = test_splits
        
        # Mock config
        mock_config = MagicMock()
        mock_config.get.return_value = {
            "vatDueSales": "Sales:VAT",
            "vatDueAcquisitions": "Purchases:VAT",
            "totalVatDue": "VAT:Total",
            "vatReclaimedCurrPeriod": "VAT:Reclaimed",
            "netVatDue": "VAT:Net",
            "totalValueSalesExVAT": "Sales:ExVAT",
            "totalValuePurchasesExVAT": "Purchases:ExVAT",
            "totalValueGoodsSuppliedExVAT": "Sales:Goods",
            "totalAcquisitionsExVAT": "Purchases:Acquisitions"
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        # Step 1: Calculate VAT
        vat_result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify VAT calculation worked
        assert vat_result["vatDueSales"]["total"] == 450.0
        assert len(vat_result["vatDueSales"]["splits"]) == 3
        
        # Step 2: Create VAT return object from calculated data
        vat_return = Return()
        vat_return.totalVatDue = vat_result["totalVatDue"]["total"]
        vat_return.vatReclaimedCurrPeriod = vat_result["vatReclaimedCurrPeriod"]["total"]
        
        # Step 3: Post VAT bill (mocking additional setup)
        mock_vendor = MagicMock()
        mock_bill = MagicMock()
        mock_liability_account = MagicMock()
        mock_bill_account = MagicMock()
        
        mock_accounts.create_bill.return_value = mock_bill
        mock_accounts.get_account.side_effect = [mock_liability_account, mock_bill_account]
        mock_config.get.side_effect = lambda key: {
            "accounts.liabilities": "Liabilities:VAT",
            "accounts.bills": "Accounts Payable"
        }[key]
        
        bill_date = date(2023, 4, 15)
        due_date = date(2023, 5, 15)
        
        with patch('gnucash_uk_vat.vat.get_vat_vendor', return_value=mock_vendor):
            vat.post_vat_bill(mock_accounts, mock_config, "VAT-2023-Q1", 
                             bill_date, due_date, vat_return, 
                             "VAT Q1 2023", "Quarterly VAT payment")
        
        # Verify the complete workflow worked
        assert mock_accounts.create_bill.called
        assert mock_accounts.create_bill_entry.call_count == 2
        assert mock_accounts.post_bill.called
        assert mock_accounts.save.called
    
    def test_vat_field_coverage(self):
        """Test that all VAT fields are properly handled"""
        # Verify that get_vat processes all 9 VAT fields
        mock_accounts = MagicMock()
        mock_account = MagicMock()
        mock_accounts.get_account.return_value = mock_account
        mock_accounts.is_debit.return_value = False
        mock_accounts.get_splits.return_value = []
        
        # Mock config with all 9 fields
        mock_config = MagicMock()
        config_dict = {}
        for i, field in enumerate(vat_fields):
            config_dict[field] = f"Account:VAT:{i}"
        mock_config.get.return_value = config_dict
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 3, 31)
        
        result = vat.get_vat(mock_accounts, mock_config, start_date, end_date)
        
        # Verify all 9 VAT fields are present in result
        assert len(result) == 9
        for field in vat_fields:
            assert field in result
            assert "splits" in result[field]
            assert "total" in result[field]
        
        # Verify correct number of account lookups (9 fields)
        assert mock_accounts.get_account.call_count == 9