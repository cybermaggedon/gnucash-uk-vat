"""
Integration tests for VAT operations.

These tests verify the complete VAT data workflows including retrieving
obligations, submitting returns, and fetching liabilities and payments.
"""

import pytest
import asyncio
from datetime import date, datetime

from gnucash_uk_vat.config import Config
from gnucash_uk_vat.auth import Auth
from gnucash_uk_vat.hmrc import VatLocalTest
from gnucash_uk_vat.model import Return, Obligation, Liability, Payment


@pytest.mark.asyncio
class TestVatOperationsIntegration:
    """Test VAT operations end-to-end"""
    
    async def test_retrieve_obligations(self, vat_test_service, integration_test_env):
        """Test retrieving VAT obligations"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Retrieve obligations for the test VRN
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        obligations = await vat_client.get_obligations(start_date, end_date)
        
        # Verify we got obligations
        assert len(obligations) >= 1
        
        # Verify obligation structure
        for obligation in obligations:
            assert isinstance(obligation, Obligation)
            assert obligation.periodKey is not None
            assert obligation.status in ['O', 'F']  # Open or Fulfilled
            assert isinstance(obligation.start, date)
            assert isinstance(obligation.end, date)
            assert isinstance(obligation.due, date)
    
    async def test_retrieve_open_obligations_only(self, vat_test_service, integration_test_env):
        """Test retrieving only open VAT obligations"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Retrieve only open obligations
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        obligations = await vat_client.get_obligations(start_date, end_date, status='O')
        
        # Verify all returned obligations are open
        assert len(obligations) >= 1
        for obligation in obligations:
            assert obligation.status == 'O'
            assert obligation.received is None  # Open obligations have no received date
    
    async def test_retrieve_liabilities(self, vat_test_service, integration_test_env):
        """Test retrieving VAT liabilities"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Retrieve liabilities
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        liabilities = await vat_client.get_liabilities(start_date, end_date)
        
        # Verify we got liabilities
        assert len(liabilities) >= 1
        
        # Verify liability structure
        for liability in liabilities:
            assert isinstance(liability, Liability)
            assert liability.typ == "Net VAT"
            assert isinstance(liability.original, (int, float))
            assert liability.original > 0
            assert isinstance(liability.start, date)
            assert isinstance(liability.end, date)
            assert isinstance(liability.due, date)
    
    async def test_retrieve_payments(self, vat_test_service, integration_test_env):
        """Test retrieving VAT payments"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Retrieve payments
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        payments = await vat_client.get_payments(start_date, end_date)
        
        # Verify we got payments
        assert len(payments) >= 1
        
        # Verify payment structure
        for payment in payments:
            assert isinstance(payment, Payment)
            assert isinstance(payment.amount, (int, float))
            assert payment.amount > 0
            assert isinstance(payment.received, date)
    
    async def test_submit_vat_return(self, vat_test_service, integration_test_env):
        """Test submitting a VAT return"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Create a test VAT return
        vat_return = Return()
        vat_return.periodKey = "#003"  # Use an open period from test data
        vat_return.vatDueSales = 1000.00
        vat_return.vatDueAcquisitions = 100.00
        vat_return.totalVatDue = 1100.00
        vat_return.vatReclaimedCurrPeriod = 300.00
        vat_return.netVatDue = 800.00
        vat_return.totalValueSalesExVAT = 10000
        vat_return.totalValuePurchasesExVAT = 5000
        vat_return.totalValueGoodsSuppliedExVAT = 0
        vat_return.totalAcquisitionsExVAT = 0
        vat_return.finalised = True
        
        # Submit the return
        response = await vat_client.submit_vat_return(vat_return)
        
        # Verify successful submission
        assert response is not None
        assert "processingDate" in response
        assert "formBundleNumber" in response
        
        # Verify processing date format
        processing_date = response["processingDate"]
        assert isinstance(processing_date, str)
        # Should be ISO format datetime
        parsed_date = datetime.fromisoformat(processing_date.replace('Z', '+00:00'))
        assert isinstance(parsed_date, datetime)
    
    async def test_retrieve_submitted_return(self, vat_test_service, integration_test_env):
        """Test retrieving a previously submitted VAT return"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Retrieve a return that exists in test data
        period_key = "#001"
        
        vat_return = await vat_client.get_vat_return(period_key)
        
        # Verify return structure
        assert isinstance(vat_return, Return)
        assert vat_return.periodKey == period_key
        assert vat_return.finalised == True
        
        # Verify all VAT fields are present
        assert isinstance(vat_return.vatDueSales, (int, float))
        assert isinstance(vat_return.vatDueAcquisitions, (int, float))
        assert isinstance(vat_return.totalVatDue, (int, float))
        assert isinstance(vat_return.vatReclaimedCurrPeriod, (int, float))
        assert isinstance(vat_return.netVatDue, (int, float))
        assert isinstance(vat_return.totalValueSalesExVAT, int)
        assert isinstance(vat_return.totalValuePurchasesExVAT, int)
        assert isinstance(vat_return.totalValueGoodsSuppliedExVAT, int)
        assert isinstance(vat_return.totalAcquisitionsExVAT, int)
    
    async def test_invalid_vrn_handling(self, vat_test_service, integration_test_env):
        """Test handling of invalid VRN"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        # Set an invalid VRN
        config.set("identity.vrn", "invalid-vrn")
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Try to retrieve obligations with invalid VRN
        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)
        
        with pytest.raises(Exception):  # Should raise an exception for invalid VRN
            await vat_client.get_obligations(start_date, end_date)
    
    async def test_fraud_headers_inclusion(self, vat_test_service, integration_test_env):
        """Test that fraud prevention headers are included in requests"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Build fraud headers
        headers = vat_client.build_fraud_headers()
        
        # Verify required fraud prevention headers are present
        required_headers = [
            'Gov-Client-Connection-Method',
            'Gov-Client-Device-ID',
            'Gov-Client-User-Ids',
            'Gov-Client-Timezone',
            'Gov-Client-Local-IPs',
            'Gov-Client-Local-IPs-Timestamp',
            'Gov-Client-MAC-Addresses',
            'Gov-Client-User-Agent',
            'Gov-Vendor-Version',
            'Gov-Vendor-Product-Name',
            'Gov-Vendor-License-Ids',
            'Gov-Client-Multi-Factor',
            'Authorization'
        ]
        
        for header in required_headers:
            assert header in headers, f"Missing required fraud header: {header}"
        
        # Verify Authorization header format
        assert headers['Authorization'].startswith('Bearer ')
        
        # Verify some header values
        assert headers['Gov-Client-Connection-Method'] == 'OTHER_DIRECT'
        assert headers['Gov-Client-Device-ID'] == 'test-device-12345'
        assert 'test-user' in headers['Gov-Client-User-Ids']
    
    async def test_date_range_validation(self, vat_test_service, integration_test_env):
        """Test date range validation in API calls"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Test with invalid date range (end before start)
        start_date = date(2023, 12, 31)
        end_date = date(2023, 1, 1)
        
        with pytest.raises(Exception):  # Should raise exception for invalid date range
            await vat_client.get_obligations(start_date, end_date)
    
    async def test_api_error_responses(self, vat_test_service, integration_test_env):
        """Test handling of API error responses"""
        config = Config(integration_test_env['config'])
        auth = Auth(integration_test_env['auth'])
        
        vat_client = VatLocalTest(config, auth, None)
        
        # Try to retrieve a return that doesn't exist
        period_key = "#999"  # Non-existent period
        
        with pytest.raises(Exception):  # Should raise exception for not found
            await vat_client.get_vat_return(period_key)