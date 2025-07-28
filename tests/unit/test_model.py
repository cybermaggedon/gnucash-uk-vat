import pytest
import json
from datetime import datetime, date, timedelta, timezone
from unittest.mock import patch

from gnucash_uk_vat.model import (
    Obligation, Liability, Payment, Return, VATUser, VATData,
    vat_fields, vat_descriptions
)


class TestObligation:
    """Test the Obligation class"""
    
    def test_init(self):
        """Test Obligation initialization"""
        start = date(2023, 1, 1)
        end = date(2023, 3, 31)
        received = date(2023, 4, 15)
        due = date(2023, 5, 7)
        
        obl = Obligation("18A1", "F", start, end, received, due)
        
        assert obl.periodKey == "18A1"
        assert obl.status == "F"
        assert obl.start == start
        assert obl.end == end
        assert obl.received == received
        assert obl.due == due
    
    def test_init_optional_fields(self):
        """Test Obligation initialization with optional fields"""
        start = date(2023, 1, 1)
        end = date(2023, 3, 31)
        
        obl = Obligation("18A1", "O", start, end)
        
        assert obl.periodKey == "18A1"
        assert obl.status == "O"
        assert obl.start == start
        assert obl.end == end
        assert obl.received is None
        assert obl.due is None
    
    def test_from_dict_complete(self):
        """Test creating Obligation from complete dictionary"""
        data = {
            "status": "F",
            "periodKey": "18A1",
            "start": "2023-01-01",
            "end": "2023-03-31",
            "received": "2023-04-15",
            "due": "2023-05-07"
        }
        
        obl = Obligation.from_dict(data)
        
        assert obl.periodKey == "18A1"
        assert obl.status == "F"
        assert obl.start == date(2023, 1, 1)
        assert obl.end == date(2023, 3, 31)
        assert obl.received == date(2023, 4, 15)
        assert obl.due == date(2023, 5, 7)
    
    def test_from_dict_minimal(self):
        """Test creating Obligation from minimal dictionary"""
        data = {
            "status": "O",
            "periodKey": "18A2",
            "start": "2023-04-01",
            "end": "2023-06-30"
        }
        
        obl = Obligation.from_dict(data)
        
        assert obl.periodKey == "18A2"
        assert obl.status == "O"
        assert obl.start == date(2023, 4, 1)
        assert obl.end == date(2023, 6, 30)
        assert obl.received is None
        assert obl.due is None
    
    def test_to_dict_complete(self):
        """Test converting complete Obligation to dictionary"""
        obl = Obligation(
            "18A1", "F",
            date(2023, 1, 1), date(2023, 3, 31),
            date(2023, 4, 15), date(2023, 5, 7)
        )
        
        result = obl.to_dict()
        
        assert result == {
            "status": "F",
            "periodKey": "18A1",
            "start": "2023-01-01",
            "end": "2023-03-31",
            "received": "2023-04-15",
            "due": "2023-05-07"
        }
    
    def test_to_dict_minimal(self):
        """Test converting minimal Obligation to dictionary"""
        obl = Obligation(
            "18A2", "O",
            date(2023, 4, 1), date(2023, 6, 30)
        )
        
        result = obl.to_dict()
        
        assert result == {
            "status": "O",
            "periodKey": "18A2",
            "start": "2023-04-01",
            "end": "2023-06-30"
        }
    
    def test_in_range(self):
        """Test Obligation in_range method"""
        obl = Obligation(
            "18A1", "F",
            date(2023, 1, 1), date(2023, 3, 31)
        )
        
        # End date within range
        assert obl.in_range(date(2023, 3, 1), date(2023, 4, 30)) == True
        assert obl.in_range(date(2023, 3, 31), date(2023, 4, 30)) == True
        
        # End date outside range
        assert obl.in_range(date(2023, 4, 1), date(2023, 6, 30)) == False
        assert obl.in_range(date(2022, 1, 1), date(2022, 12, 31)) == False


class TestLiability:
    """Test the Liability class"""
    
    def test_init(self):
        """Test Liability initialization"""
        start = date(2023, 1, 1)
        end = date(2023, 3, 31)
        
        liab = Liability(start, end, "VAT", 1000.0, 500.0, date(2023, 5, 7))
        
        assert liab.start == start
        assert liab.end == end
        assert liab.typ == "VAT"
        assert liab.original == 1000.0
        assert liab.outstanding == 500.0
        assert liab.due == date(2023, 5, 7)
    
    def test_from_dict(self):
        """Test creating Liability from dictionary"""
        data = {
            "taxPeriod": {
                "from": "2023-01-01",
                "to": "2023-03-31"
            },
            "type": "VAT",
            "originalAmount": 1000.0,
            "outstandingAmount": 500.0,
            "due": "2023-05-07"
        }
        
        liab = Liability.from_dict(data)
        
        assert liab.start == date(2023, 1, 1)
        assert liab.end == date(2023, 3, 31)
        assert liab.typ == "VAT"
        assert liab.original == 1000.0
        assert liab.outstanding == 500.0
        assert liab.due == date(2023, 5, 7)
    
    def test_from_dict_minimal(self):
        """Test creating Liability from minimal dictionary"""
        data = {
            "taxPeriod": {
                "from": "2023-01-01",
                "to": "2023-03-31"
            },
            "type": "VAT",
            "originalAmount": 1000.0
        }
        
        liab = Liability.from_dict(data)
        
        assert liab.start == date(2023, 1, 1)
        assert liab.end == date(2023, 3, 31)
        assert liab.typ == "VAT"
        assert liab.original == 1000.0
        assert liab.outstanding is None
        assert liab.due is None
    
    def test_to_dict(self):
        """Test converting Liability to dictionary"""
        liab = Liability(
            date(2023, 1, 1), date(2023, 3, 31),
            "VAT", 1000.0, 500.0, date(2023, 5, 7)
        )
        
        result = liab.to_dict()
        
        assert result == {
            "type": "VAT",
            "originalAmount": 1000.0,
            "outstandingAmount": 500.0,
            "taxPeriod": {
                "from": "2023-01-01",
                "to": "2023-03-31"
            },
            "due": "2023-05-07"
        }
    
    def test_in_range(self):
        """Test Liability in_range method"""
        liab = Liability(
            date(2023, 1, 1), date(2023, 3, 31),
            "VAT", 1000.0
        )
        
        # Start date within range
        assert liab.in_range(date(2022, 12, 1), date(2023, 2, 1)) == True
        
        # End date within range
        assert liab.in_range(date(2023, 3, 1), date(2023, 4, 30)) == True
        
        # Liability period encompasses range
        assert liab.in_range(date(2023, 2, 1), date(2023, 2, 28)) == True
        
        # No overlap
        assert liab.in_range(date(2023, 4, 1), date(2023, 6, 30)) == False
        assert liab.in_range(date(2022, 1, 1), date(2022, 12, 31)) == False


class TestPayment:
    """Test the Payment class"""
    
    def test_init(self):
        """Test Payment initialization"""
        payment = Payment(1500.50, date(2023, 5, 7))
        
        assert payment.amount == 1500.50
        assert payment.received == date(2023, 5, 7)
    
    def test_from_dict(self):
        """Test creating Payment from dictionary"""
        data = {
            "amount": 2000.75,
            "received": "2023-05-15"
        }
        
        payment = Payment.from_dict(data)
        
        assert payment.amount == 2000.75
        assert payment.received == date(2023, 5, 15)
    
    def test_to_dict(self):
        """Test converting Payment to dictionary"""
        payment = Payment(1234.56, date(2023, 6, 1))
        
        result = payment.to_dict()
        
        assert result == {
            "amount": 1234.56,
            "received": "2023-06-01"
        }
    
    def test_in_range(self):
        """Test Payment in_range method"""
        payment = Payment(1000.0, date(2023, 5, 15))
        
        # Received date within range
        assert payment.in_range(date(2023, 5, 1), date(2023, 5, 31)) == True
        assert payment.in_range(date(2023, 5, 15), date(2023, 5, 15)) == True
        
        # Received date outside range
        assert payment.in_range(date(2023, 4, 1), date(2023, 4, 30)) == False
        assert payment.in_range(date(2023, 6, 1), date(2023, 6, 30)) == False


class TestReturn:
    """Test the Return class"""
    
    def test_init(self):
        """Test Return initialization"""
        ret = Return()
        
        # All fields should be None initially
        assert ret.periodKey is None
        assert ret.vatDueSales is None
        assert ret.vatDueAcquisitions is None
        assert ret.totalVatDue is None
        assert ret.vatReclaimedCurrPeriod is None
        assert ret.netVatDue is None
        assert ret.totalValueSalesExVAT is None
        assert ret.totalValuePurchasesExVAT is None
        assert ret.totalValueGoodsSuppliedExVAT is None
        assert ret.totalAcquisitionsExVAT is None
        assert ret.finalised is None
    
    def test_from_dict_complete(self):
        """Test creating Return from complete dictionary"""
        data = {
            "periodKey": "18A1",
            "vatDueSales": 100.50,
            "vatDueAcquisitions": 50.25,
            "totalVatDue": 150.75,
            "vatReclaimedCurrPeriod": 75.00,
            "netVatDue": 75.75,
            "totalValueSalesExVAT": 502,
            "totalValuePurchasesExVAT": 375,
            "totalValueGoodsSuppliedExVAT": 100,
            "totalAcquisitionsExVAT": 50,
            "finalised": True
        }
        
        ret = Return.from_dict(data)
        
        assert ret.periodKey == "18A1"
        assert ret.vatDueSales == 100.50
        assert ret.vatDueAcquisitions == 50.25
        assert ret.totalVatDue == 150.75
        assert ret.vatReclaimedCurrPeriod == 75.00
        assert ret.netVatDue == 75.75
        assert ret.totalValueSalesExVAT == 502
        assert ret.totalValuePurchasesExVAT == 375
        assert ret.totalValueGoodsSuppliedExVAT == 100
        assert ret.totalAcquisitionsExVAT == 50
        assert ret.finalised == True
    
    def test_from_dict_without_finalised(self):
        """Test creating Return from dictionary without finalised field"""
        data = {
            "periodKey": "18A1",
            "vatDueSales": 100.50,
            "vatDueAcquisitions": 50.25,
            "totalVatDue": 150.75,
            "vatReclaimedCurrPeriod": 75.00,
            "netVatDue": 75.75,
            "totalValueSalesExVAT": 502,
            "totalValuePurchasesExVAT": 375,
            "totalValueGoodsSuppliedExVAT": 100,
            "totalAcquisitionsExVAT": 50
        }
        
        ret = Return.from_dict(data)
        
        assert ret.periodKey == "18A1"
        assert ret.finalised is None
    
    def test_to_dict_with_finalised(self):
        """Test converting Return to dictionary with finalised=True"""
        ret = Return()
        ret.periodKey = "18A1"
        ret.vatDueSales = 100.50
        ret.vatDueAcquisitions = 50.25
        ret.totalVatDue = 150.75
        ret.vatReclaimedCurrPeriod = 75.00
        ret.netVatDue = 75.75
        ret.totalValueSalesExVAT = 502
        ret.totalValuePurchasesExVAT = 375
        ret.totalValueGoodsSuppliedExVAT = 100
        ret.totalAcquisitionsExVAT = 50
        ret.finalised = True
        
        result = ret.to_dict()
        
        assert result["periodKey"] == "18A1"
        assert result["vatDueSales"] == 100.50
        assert result["finalised"] == True
        assert len(result) == 11  # All fields including finalised
    
    def test_to_dict_without_finalised(self):
        """Test converting Return to dictionary without finalised"""
        ret = Return()
        ret.periodKey = "18A1"
        ret.vatDueSales = 100.50
        ret.vatDueAcquisitions = 50.25
        ret.totalVatDue = 150.75
        ret.vatReclaimedCurrPeriod = 75.00
        ret.netVatDue = 75.75
        ret.totalValueSalesExVAT = 502
        ret.totalValuePurchasesExVAT = 375
        ret.totalValueGoodsSuppliedExVAT = 100
        ret.totalAcquisitionsExVAT = 50
        ret.finalised = False
        
        result = ret.to_dict()
        
        assert "finalised" not in result
        assert len(result) == 10  # All fields except finalised
    
    def test_to_string_with_key(self):
        """Test Return to_string method with period key"""
        ret = Return()
        ret.periodKey = "18A1"
        ret.vatDueSales = 100.50
        ret.vatDueAcquisitions = 0
        ret.totalVatDue = 100.50
        ret.vatReclaimedCurrPeriod = 50.25
        ret.netVatDue = 50.25
        ret.totalValueSalesExVAT = 502
        ret.totalValuePurchasesExVAT = 251
        ret.totalValueGoodsSuppliedExVAT = 0
        ret.totalAcquisitionsExVAT = 0
        
        result = ret.to_string(show_key=True, indent=True)
        
        assert "Period Key" in result
        assert "18A1" in result
        assert "VAT due on sales" in result
        assert "100.50" in result
    
    def test_to_string_without_key(self):
        """Test Return to_string method without period key"""
        ret = Return()
        ret.periodKey = "18A1"
        ret.vatDueSales = 100.50
        ret.vatDueAcquisitions = None  # Test None handling
        ret.totalVatDue = 100.50
        ret.vatReclaimedCurrPeriod = 50.25
        ret.netVatDue = 50.25
        ret.totalValueSalesExVAT = 502
        ret.totalValuePurchasesExVAT = 251
        ret.totalValueGoodsSuppliedExVAT = 0
        ret.totalAcquisitionsExVAT = 0
        
        result = ret.to_string(show_key=False, indent=False)
        
        assert "Period Key" not in result
        assert "VAT due on sales: 100.50" in result
        assert "VAT due on acquisitions: 0.00" in result  # None becomes 0.00


class TestVATUser:
    """Test the VATUser class"""
    
    def test_init(self):
        """Test VATUser initialization"""
        user = VATUser()
        
        assert user.obligations == []
        assert user.returns == []
        assert user.liabilities == []
        assert user.payments == []
    
    def test_from_dict(self):
        """Test creating VATUser from dictionary"""
        data = {
            "obligations": [
                {
                    "status": "F",
                    "periodKey": "18A1",
                    "start": "2023-01-01",
                    "end": "2023-03-31"
                }
            ],
            "returns": [
                {
                    "periodKey": "18A1",
                    "vatDueSales": 100.0,
                    "vatDueAcquisitions": 0,
                    "totalVatDue": 100.0,
                    "vatReclaimedCurrPeriod": 50.0,
                    "netVatDue": 50.0,
                    "totalValueSalesExVAT": 500,
                    "totalValuePurchasesExVAT": 250,
                    "totalValueGoodsSuppliedExVAT": 0,
                    "totalAcquisitionsExVAT": 0
                }
            ],
            "payments": [
                {
                    "amount": 50.0,
                    "received": "2023-05-07"
                }
            ],
            "liabilities": [
                {
                    "taxPeriod": {
                        "from": "2023-01-01",
                        "to": "2023-03-31"
                    },
                    "type": "VAT",
                    "originalAmount": 50.0
                }
            ]
        }
        
        user = VATUser.from_dict(data)
        
        assert len(user.obligations) == 1
        assert len(user.returns) == 1
        assert len(user.payments) == 1
        assert len(user.liabilities) == 1
        
        assert user.obligations[0].periodKey == "18A1"
        assert user.returns[0].vatDueSales == 100.0
        assert user.payments[0].amount == 50.0
        assert user.liabilities[0].original == 50.0
    
    def test_to_dict(self):
        """Test converting VATUser to dictionary"""
        user = VATUser()
        
        # Add test data
        user.obligations.append(
            Obligation("18A1", "F", date(2023, 1, 1), date(2023, 3, 31))
        )
        user.payments.append(
            Payment(100.0, date(2023, 5, 7))
        )
        
        result = user.to_dict()
        
        assert "obligations" in result
        assert "returns" in result
        assert "payments" in result
        assert "liabilities" in result
        
        assert len(result["obligations"]) == 1
        assert result["obligations"][0]["periodKey"] == "18A1"
        assert len(result["payments"]) == 1
        assert result["payments"][0]["amount"] == 100.0
    
    def test_add_return(self):
        """Test adding a return to VATUser"""
        user = VATUser()
        
        # Add an open obligation
        obl = Obligation("18A1", "O", date(2023, 1, 1), date(2023, 3, 31))
        user.obligations.append(obl)
        
        # Create a return
        ret = Return()
        ret.periodKey = "18A1"
        ret.netVatDue = 150.0
        
        with patch('gnucash_uk_vat.model.datetime') as mock_datetime:
            mock_datetime.now.return_value.date.return_value = date(2023, 4, 15)
            mock_datetime.UTC = timezone.utc
            user.add_return(ret)
        
        # Check obligation was updated
        assert obl.status == "F"
        assert obl.received == date(2023, 4, 15)
        
        # Check liability was created
        assert len(user.liabilities) == 1
        liab = user.liabilities[0]
        assert liab.start == date(2023, 1, 1)
        assert liab.end == date(2023, 3, 31)
        assert liab.typ == "Net VAT"
        assert liab.original == 150.0
        assert liab.outstanding == 150.0
        assert liab.due == date(2023, 4, 30)  # 30 days after period end
        
        # Check return was added
        assert len(user.returns) == 1
        assert user.returns[0] == ret
    
    def test_add_return_no_matching_obligation(self):
        """Test adding a return with no matching obligation"""
        user = VATUser()
        
        # Create a return with no matching obligation
        ret = Return()
        ret.periodKey = "18A1"
        
        with pytest.raises(RuntimeError) as exc_info:
            user.add_return(ret)
        
        assert "periodKey does not match an open obligation" in str(exc_info.value)


class TestVATData:
    """Test the VATData class"""
    
    def test_init(self):
        """Test VATData initialization"""
        data = VATData()
        assert data.data == {}
    
    def test_from_dict(self):
        """Test creating VATData from dictionary"""
        data_dict = {
            "123456789": {
                "obligations": [],
                "returns": [],
                "payments": [],
                "liabilities": []
            },
            "987654321": {
                "obligations": [
                    {
                        "status": "O",
                        "periodKey": "18A1",
                        "start": "2023-01-01",
                        "end": "2023-03-31"
                    }
                ],
                "returns": [],
                "payments": [],
                "liabilities": []
            }
        }
        
        vat_data = VATData.from_dict(data_dict)
        
        assert "123456789" in vat_data.data
        assert "987654321" in vat_data.data
        assert isinstance(vat_data.data["123456789"], VATUser)
        assert isinstance(vat_data.data["987654321"], VATUser)
        assert len(vat_data.data["987654321"].obligations) == 1
    
    def test_to_dict(self):
        """Test converting VATData to dictionary"""
        vat_data = VATData()
        
        # Add test users
        user1 = VATUser()
        user1.obligations.append(
            Obligation("18A1", "O", date(2023, 1, 1), date(2023, 3, 31))
        )
        vat_data.data["123456789"] = user1
        
        user2 = VATUser()
        vat_data.data["987654321"] = user2
        
        result = vat_data.to_dict()
        
        assert "123456789" in result
        assert "987654321" in result
        assert len(result["123456789"]["obligations"]) == 1
        assert len(result["987654321"]["obligations"]) == 0
    
    def test_from_json(self):
        """Test creating VATData from JSON string"""
        json_data = json.dumps({
            "123456789": {
                "obligations": [],
                "returns": [],
                "payments": [],
                "liabilities": []
            }
        })
        
        vat_data = VATData.from_json(json_data)
        
        assert "123456789" in vat_data.data
        assert isinstance(vat_data.data["123456789"], VATUser)


class TestConstants:
    """Test module constants"""
    
    def test_vat_fields(self):
        """Test vat_fields list contains expected fields"""
        expected_fields = [
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
        
        assert vat_fields == expected_fields
    
    def test_vat_descriptions(self):
        """Test vat_descriptions contains all expected mappings"""
        assert len(vat_descriptions) == 9
        assert vat_descriptions["vatDueSales"] == "VAT due on sales"
        assert vat_descriptions["netVatDue"] == "VAT due"
        assert vat_descriptions["totalValueSalesExVAT"] == "Sales before VAT"