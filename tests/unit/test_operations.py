import pytest
import json
import io
import sys
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from contextlib import redirect_stdout, redirect_stderr

from gnucash_uk_vat import operations
from gnucash_uk_vat.model import Obligation, Return


class TestAuthenticate:
    """Test authenticate function"""
    
    @pytest.mark.asyncio
    async def test_authenticate_success(self):
        """Test successful authentication flow"""
        # Mock HMRC service
        mock_hmrc = AsyncMock()
        mock_hmrc.get_code.return_value = "test_auth_code"
        
        # Mock auth object
        mock_auth = MagicMock()
        mock_auth.file = "test_auth.json"
        
        # Capture stderr output
        stderr_capture = io.StringIO()
        
        with redirect_stderr(stderr_capture):
            await operations.authenticate(mock_hmrc, mock_auth)
        
        # Verify calls were made in correct order
        mock_hmrc.get_code.assert_called_once()
        mock_hmrc.get_auth.assert_called_once_with("test_auth_code")
        mock_auth.write.assert_called_once()
        
        # Verify stderr messages
        stderr_output = stderr_capture.getvalue()
        assert "Got one-time code." in stderr_output
        assert "Got authentication key." in stderr_output
        assert "Wrote test_auth.json." in stderr_output


class TestShowOpenObligations:
    """Test show_open_obligations function"""
    
    @pytest.mark.asyncio
    async def test_show_open_obligations_no_matches(self):
        """Test when no obligations match"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_open_obligations(mock_hmrc, mock_config, False)
        
        mock_hmrc.get_open_obligations.assert_called_once_with("123456789")
        assert "No obligations matched." in stdout_capture.getvalue()
    
    @pytest.mark.asyncio
    async def test_show_open_obligations_table_format(self):
        """Test obligations display in table format"""
        # Create test obligations
        obl1 = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        obl2 = Obligation("#002", "O", date(2023, 4, 1), date(2023, 6, 30), due=date(2023, 7, 31))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl1, obl2]
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_open_obligations(mock_hmrc, mock_config, False)
        
        output = stdout_capture.getvalue()
        assert "Start" in output
        assert "End" in output
        assert "Due" in output
        assert "Status" in output
        assert "2023-01-01" in output
        assert "2023-03-31" in output
    
    @pytest.mark.asyncio
    async def test_show_open_obligations_json_format(self):
        """Test obligations display in JSON format"""
        obl = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl]
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_open_obligations(mock_hmrc, mock_config, True)
        
        output = stdout_capture.getvalue()
        parsed_json = json.loads(output)
        
        assert len(parsed_json) == 1
        assert parsed_json[0]["start"] == "2023-01-01"
        assert parsed_json[0]["end"] == "2023-03-31"
        assert parsed_json[0]["due"] == "2023-04-30"
        assert parsed_json[0]["status"] == "O"


class TestShowObligations:
    """Test show_obligations function"""
    
    @pytest.mark.asyncio
    async def test_show_obligations_no_matches(self):
        """Test when no obligations match in time period"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_obligations.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_obligations(start_date, end_date, mock_hmrc, mock_config, False)
        
        mock_hmrc.get_obligations.assert_called_once_with("123456789", start_date, end_date)
        assert "No obligations matched." in stdout_capture.getvalue()
    
    @pytest.mark.asyncio
    async def test_show_obligations_with_received_date(self):
        """Test obligations display with received date"""
        obl = Obligation("#001", "F", date(2023, 1, 1), date(2023, 3, 31), 
                        received=date(2023, 4, 15), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_obligations.return_value = [obl]
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_obligations(start_date, end_date, mock_hmrc, mock_config, True)
        
        output = stdout_capture.getvalue()
        parsed_json = json.loads(output)
        
        assert parsed_json[0]["received"] == "2023-04-15"
        assert parsed_json[0]["status"] == "F"


class TestSubmitVatReturn:
    """Test submit_vat_return function"""
    
    @pytest.mark.asyncio
    async def test_submit_vat_return_no_matching_obligation(self):
        """Test when due date doesn't match any obligations"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        due_date = date(2023, 4, 30)
        
        with pytest.raises(RuntimeError) as exc_info:
            await operations.submit_vat_return(due_date, mock_hmrc, mock_config)
        
        assert "Due date '2023-04-30' does not match any obligations" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_vat_return_user_says_no(self):
        """Test when user refuses to submit"""
        # Create test obligation
        obl = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl]
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.vrn": "123456789",
            "accounts.kind": "test",
            "accounts.file": "test.gnucash"
        }[key]
        
        # Mock accounts and VAT data
        mock_accounts_class = MagicMock()
        mock_accounts_instance = MagicMock()
        mock_accounts_class.return_value = mock_accounts_instance
        
        mock_vat_data = {
            "vatDueSales": {"total": 100.0},
            "vatDueAcquisitions": {"total": 20.0},
            "totalVatDue": {"total": 120.0},
            "vatReclaimedCurrPeriod": {"total": 30.0},
            "netVatDue": {"total": 90.0},
            "totalValueSalesExVAT": {"total": 1000},
            "totalValuePurchasesExVAT": {"total": 500},
            "totalValueGoodsSuppliedExVAT": {"total": 0},
            "totalAcquisitionsExVAT": {"total": 0}
        }
        
        due_date = date(2023, 4, 30)
        
        with patch('gnucash_uk_vat.operations.accounts.get_class', return_value=mock_accounts_class), \
             patch('gnucash_uk_vat.operations.vat.get_vat', return_value=mock_vat_data), \
             patch('builtins.input', return_value="no"):
            
            with pytest.raises(RuntimeError) as exc_info:
                await operations.submit_vat_return(due_date, mock_hmrc, mock_config)
            
            assert "Submission was not accepted." in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_submit_vat_return_success(self):
        """Test successful VAT return submission"""
        # Create test obligation
        obl = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl]
        mock_hmrc.submit_vat_return.return_value = {
            "processingDate": "2023-04-15T10:30:00Z",
            "paymentIndicator": "BANK",
            "formBundleNumber": "12345",
            "chargeRefNumber": "67890"
        }
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.vrn": "123456789",
            "accounts.kind": "test",
            "accounts.file": "test.gnucash"
        }[key]
        
        # Mock accounts and VAT data
        mock_accounts_class = MagicMock()
        mock_accounts_instance = MagicMock()
        mock_accounts_class.return_value = mock_accounts_instance
        
        mock_vat_data = {
            "vatDueSales": {"total": 100.0},
            "vatDueAcquisitions": {"total": 20.0},
            "totalVatDue": {"total": 120.0},
            "vatReclaimedCurrPeriod": {"total": 30.0},
            "netVatDue": {"total": 90.0},
            "totalValueSalesExVAT": {"total": 1000},
            "totalValuePurchasesExVAT": {"total": 500},
            "totalValueGoodsSuppliedExVAT": {"total": 0},
            "totalAcquisitionsExVAT": {"total": 0}
        }
        
        due_date = date(2023, 4, 30)
        
        stdout_capture = io.StringIO()
        
        with patch('gnucash_uk_vat.operations.accounts.get_class', return_value=mock_accounts_class), \
             patch('gnucash_uk_vat.operations.vat.get_vat', return_value=mock_vat_data), \
             patch('builtins.input', return_value="yes"), \
             redirect_stdout(stdout_capture):
            
            await operations.submit_vat_return(due_date, mock_hmrc, mock_config)
        
        # Verify HMRC API was called correctly
        mock_hmrc.submit_vat_return.assert_called_once()
        call_args = mock_hmrc.submit_vat_return.call_args
        assert call_args[0][0] == "123456789"  # VRN
        
        submitted_return = call_args[0][1]
        assert submitted_return.periodKey == "#001"
        assert submitted_return.finalised == True
        assert submitted_return.vatDueSales == 100.0
        assert submitted_return.netVatDue == 90.0
        
        # Verify output contains success messages
        output = stdout_capture.getvalue()
        assert "Submitted." in output
        assert "Processing date" in output
        assert "Payment indicator" in output


class TestPostVatBill:
    """Test post_vat_bill function"""
    
    @pytest.mark.asyncio
    async def test_post_vat_bill_no_matching_obligation(self):
        """Test when due date doesn't match any obligation"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_obligations.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        due_date = date(2023, 4, 30)
        
        with pytest.raises(RuntimeError) as exc_info:
            await operations.post_vat_bill(start_date, end_date, due_date, mock_hmrc, mock_config)
        
        assert "Due date '2023-04-30' does not match any obligation" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_post_vat_bill_success(self):
        """Test successful VAT bill posting"""
        # Create test obligation
        obl = Obligation("#001", "F", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_obligations.return_value = [obl]
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.vrn": "123456789",
            "accounts.kind": "test",
            "accounts.file": "test.gnucash"
        }[key]
        
        # Mock accounts and VAT data
        mock_accounts_class = MagicMock()
        mock_accounts_instance = MagicMock()
        mock_accounts_class.return_value = mock_accounts_instance
        
        mock_vat_data = {
            "vatDueSales": {"total": 100.0},
            "vatDueAcquisitions": {"total": 20.0},
            "totalVatDue": {"total": 120.0},
            "vatReclaimedCurrPeriod": {"total": 30.0},
            "netVatDue": {"total": 90.0},
            "totalValueSalesExVAT": {"total": 1000},
            "totalValuePurchasesExVAT": {"total": 500},
            "totalValueGoodsSuppliedExVAT": {"total": 0},
            "totalAcquisitionsExVAT": {"total": 0}
        }
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        due_date = date(2023, 4, 30)
        
        stdout_capture = io.StringIO()
        
        with patch('gnucash_uk_vat.operations.accounts.get_class', return_value=mock_accounts_class), \
             patch('gnucash_uk_vat.operations.vat.get_vat', return_value=mock_vat_data), \
             patch('gnucash_uk_vat.operations.vat.post_vat_bill') as mock_post_vat_bill, \
             redirect_stdout(stdout_capture):
            
            await operations.post_vat_bill(start_date, end_date, due_date, mock_hmrc, mock_config)
        
        # Verify vat.post_vat_bill was called
        mock_post_vat_bill.assert_called_once()
        call_args = mock_post_vat_bill.call_args[0]
        
        assert call_args[0] == mock_accounts_instance  # accounts
        assert call_args[1] == mock_config  # config
        assert call_args[2] == "2023-04-30"  # due date as string
        assert call_args[3] == date(2023, 3, 31)  # end date
        # call_args[4] is calculated due date (end + 28 + 7 days)
        # call_args[5] is the Return object
        # call_args[6] is the return string
        assert "VAT payment for due date 2023-04-30" in call_args[7]  # description
        
        assert "Bill posted." in stdout_capture.getvalue()


class TestShowAccountData:
    """Test show_account_data function"""
    
    @pytest.mark.asyncio
    async def test_show_account_data_no_matching_obligation(self):
        """Test when due date doesn't match any obligations"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        due_date = date(2023, 4, 30)
        
        with pytest.raises(RuntimeError) as exc_info:
            await operations.show_account_data(mock_hmrc, mock_config, due_date)
        
        assert "Due date '2023-04-30' does not match any obligations" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_show_account_data_summary(self):
        """Test account data display in summary mode"""
        # Create test obligation
        obl = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl]
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.vrn": "123456789",
            "accounts.kind": "test",
            "accounts.file": "test.gnucash"
        }[key]
        
        # Mock accounts and VAT data
        mock_accounts_class = MagicMock()
        mock_accounts_instance = MagicMock()
        mock_accounts_class.return_value = mock_accounts_instance
        
        mock_vat_data = {
            "vatDueSales": {"total": 100.0, "splits": []},
            "vatDueAcquisitions": {"total": 20.0, "splits": []},
            "totalVatDue": {"total": 120.0, "splits": []},
            "vatReclaimedCurrPeriod": {"total": 30.0, "splits": []},
            "netVatDue": {"total": 90.0, "splits": []},
            "totalValueSalesExVAT": {"total": 1000, "splits": []},
            "totalValuePurchasesExVAT": {"total": 500, "splits": []},
            "totalValueGoodsSuppliedExVAT": {"total": 0, "splits": []},
            "totalAcquisitionsExVAT": {"total": 0, "splits": []}
        }
        
        due_date = date(2023, 4, 30)
        
        stdout_capture = io.StringIO()
        
        with patch('gnucash_uk_vat.operations.accounts.get_class', return_value=mock_accounts_class), \
             patch('gnucash_uk_vat.operations.vat.get_vat', return_value=mock_vat_data), \
             redirect_stdout(stdout_capture):
            
            await operations.show_account_data(mock_hmrc, mock_config, due_date, detail=False)
        
        output = stdout_capture.getvalue()
        assert "Found Obligation that is due on '2023-04-30'" in output
        assert "VAT due on sales: 100.00" in output
        assert "VAT due on acquisitions: 20.00" in output
        assert "VAT due: 90.00" in output
    
    @pytest.mark.asyncio
    async def test_show_account_data_detail(self):
        """Test account data display in detail mode with transactions"""
        # Create test obligation
        obl = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl]
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.vrn": "123456789",
            "accounts.kind": "test",
            "accounts.file": "test.gnucash"
        }[key]
        
        # Mock accounts and VAT data with transactions
        mock_accounts_class = MagicMock()
        mock_accounts_instance = MagicMock()
        mock_accounts_class.return_value = mock_accounts_instance
        
        test_splits = [
            {"date": date(2023, 1, 15), "amount": 50.0, "description": "Sale transaction 1"},
            {"date": date(2023, 2, 10), "amount": 50.0, "description": "Sale transaction 2"}
        ]
        
        mock_vat_data = {
            "vatDueSales": {"total": 100.0, "splits": test_splits},
            "vatDueAcquisitions": {"total": 0.0, "splits": []},
            "totalVatDue": {"total": 100.0, "splits": []},
            "vatReclaimedCurrPeriod": {"total": 0.0, "splits": []},
            "netVatDue": {"total": 100.0, "splits": []},
            "totalValueSalesExVAT": {"total": 1000, "splits": []},
            "totalValuePurchasesExVAT": {"total": 0, "splits": []},
            "totalValueGoodsSuppliedExVAT": {"total": 0, "splits": []},
            "totalAcquisitionsExVAT": {"total": 0, "splits": []}
        }
        
        due_date = date(2023, 4, 30)
        
        stdout_capture = io.StringIO()
        
        with patch('gnucash_uk_vat.operations.accounts.get_class', return_value=mock_accounts_class), \
             patch('gnucash_uk_vat.operations.vat.get_vat', return_value=mock_vat_data), \
             redirect_stdout(stdout_capture):
            
            await operations.show_account_data(mock_hmrc, mock_config, due_date, detail=True)
        
        output = stdout_capture.getvalue()
        assert "VAT due on sales: 100.00" in output
        assert "Sale transaction 1" in output
        assert "Sale transaction 2" in output
        assert "50.00" in output


class TestShowVatReturn:
    """Test show_vat_return function"""
    
    @pytest.mark.asyncio
    async def test_show_vat_return_no_matching_obligation(self):
        """Test when due date doesn't match any obligation"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_obligations.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        due_date = date(2023, 4, 30)
        
        with pytest.raises(RuntimeError) as exc_info:
            await operations.show_vat_return(start_date, end_date, due_date, mock_hmrc, mock_config)
        
        assert "Due date '2023-04-30' does not match any obligation" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_show_vat_return_success(self):
        """Test successful VAT return display"""
        # Create test obligation
        obl = Obligation("#001", "F", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        # Create test return
        test_return = Return()
        test_return.periodKey = "#001"
        test_return.vatDueSales = 100.0
        test_return.vatDueAcquisitions = 20.0
        test_return.totalVatDue = 120.0
        test_return.vatReclaimedCurrPeriod = 30.0
        test_return.netVatDue = 90.0
        test_return.totalValueSalesExVAT = 1000
        test_return.totalValuePurchasesExVAT = 500
        test_return.totalValueGoodsSuppliedExVAT = 0
        test_return.totalAcquisitionsExVAT = 0
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_obligations.return_value = [obl]
        mock_hmrc.get_vat_return.return_value = test_return
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        due_date = date(2023, 4, 30)
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_vat_return(start_date, end_date, due_date, mock_hmrc, mock_config)
        
        # Verify HMRC API calls
        mock_hmrc.get_obligations.assert_called_once_with("123456789", start_date, end_date)
        mock_hmrc.get_vat_return.assert_called_once_with("123456789", "#001")
        
        # Verify output contains VAT return data
        output = stdout_capture.getvalue()
        assert "VAT due on sales" in output
        assert "100.00" in output
        assert "90.00" in output


class TestShowLiabilities:
    """Test show_liabilities function"""
    
    @pytest.mark.asyncio
    async def test_show_liabilities_empty(self):
        """Test when no liabilities are returned"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_vat_liabilities.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_liabilities(start_date, end_date, mock_hmrc, mock_config)
        
        mock_hmrc.get_vat_liabilities.assert_called_once_with("123456789", start_date, end_date)
        
        # Should still show table headers even with no data
        output = stdout_capture.getvalue()
        assert "Period End" in output
        assert "Type" in output
        assert "Amount" in output


class TestShowPayments:
    """Test show_payments function"""
    
    @pytest.mark.asyncio 
    async def test_show_payments_empty(self):
        """Test when no payments are returned"""
        mock_hmrc = AsyncMock()
        mock_hmrc.get_vat_payments.return_value = []
        
        mock_config = MagicMock()
        mock_config.get.return_value = "123456789"
        
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        stdout_capture = io.StringIO()
        
        with redirect_stdout(stdout_capture):
            await operations.show_payments(start_date, end_date, mock_hmrc, mock_config)
        
        mock_hmrc.get_vat_payments.assert_called_once_with("123456789", start_date, end_date)
        
        # Should still show table headers even with no data
        output = stdout_capture.getvalue()
        assert "Amount" in output
        assert "Received" in output


class TestIntegration:
    """Integration tests for operations module"""
    
    @pytest.mark.asyncio
    async def test_user_input_retry_logic(self):
        """Test user input retry logic in submit_vat_return"""
        # Create test obligation
        obl = Obligation("#001", "O", date(2023, 1, 1), date(2023, 3, 31), due=date(2023, 4, 30))
        
        mock_hmrc = AsyncMock()
        mock_hmrc.get_open_obligations.return_value = [obl]
        mock_hmrc.submit_vat_return.return_value = {"processingDate": "2023-04-15T10:30:00Z"}
        
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key: {
            "identity.vrn": "123456789",
            "accounts.kind": "test", 
            "accounts.file": "test.gnucash"
        }[key]
        
        # Mock accounts and VAT data
        mock_accounts_class = MagicMock()
        mock_vat_data = {
            "vatDueSales": {"total": 100.0},
            "vatDueAcquisitions": {"total": 0.0},
            "totalVatDue": {"total": 100.0},
            "vatReclaimedCurrPeriod": {"total": 0.0},
            "netVatDue": {"total": 100.0},
            "totalValueSalesExVAT": {"total": 1000},
            "totalValuePurchasesExVAT": {"total": 0},
            "totalValueGoodsSuppliedExVAT": {"total": 0},
            "totalAcquisitionsExVAT": {"total": 0}
        }
        
        due_date = date(2023, 4, 30)
        
        # Simulate user entering invalid input, then "yes"
        inputs = ["maybe", "invalid", "yes"]
        
        stdout_capture = io.StringIO()
        
        with patch('gnucash_uk_vat.operations.accounts.get_class', return_value=mock_accounts_class), \
             patch('gnucash_uk_vat.operations.vat.get_vat', return_value=mock_vat_data), \
             patch('builtins.input', side_effect=inputs), \
             redirect_stdout(stdout_capture):
            
            await operations.submit_vat_return(due_date, mock_hmrc, mock_config)
        
        # Should eventually succeed after retries
        output = stdout_capture.getvalue()
        assert "Answer not recognised." in output
        assert "Submitted." in output