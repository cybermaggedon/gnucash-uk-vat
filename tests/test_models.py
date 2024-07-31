
import datetime

example_start = datetime.date.fromisoformat("2019-04-06")
example_end = datetime.date.fromisoformat("2023-12-29")
example_period_key = "K1234"
example_status = "X"
example_received = datetime.date.fromisoformat("2029-11-30")
example_due = datetime.date.fromisoformat("2020-06-09")

example_box_1 = 0.51
example_box_2 = 125.51
example_box_3 = 90851.15
example_box_4 = 985615915.23
example_box_5 = 2789313.77
example_box_6 = 21873
example_box_7 = 18954
example_box_8 = 1239087123
example_box_9 = 1023123093

def test_vat_fields():

    import gnucash_uk_vat.model as m

    assert(len(m.vat_fields) == 9)

    assert(m.vat_fields[8] == "totalAcquisitionsExVAT")

    assert(
        m.vat_descriptions[m.vat_fields[8]] == "Total acquisitions ex. VAT"
    )

def test_obligation_model():

    from gnucash_uk_vat.model import Obligation

    input = {
        "periodKey": example_period_key,
        "start": str(example_start),
        "end": str(example_end),
        "status": example_status,
        "received": str(example_received),
        "due": str(example_due),
    }

    obl = Obligation.from_dict(input)

    assert(obl.periodKey == example_period_key)
    assert(obl.status == example_status)
    assert(obl.start == example_start)
    assert(obl.end == example_end)
    assert(obl.received == example_received)
    assert(obl.due == example_due)

def test_return_model():

    from gnucash_uk_vat.model import Return

    input = {
        "periodKey": example_period_key,
        "vatDueSales": example_box_1,
        "vatDueAcquisitions": example_box_2,
        "totalVatDue": example_box_3,
        "vatReclaimedCurrPeriod": example_box_4,
        "netVatDue": example_box_5,
        "totalValueSalesExVAT": example_box_6,
        "totalValuePurchasesExVAT": example_box_7,
        "totalValueGoodsSuppliedExVAT": example_box_8,
        "totalAcquisitionsExVAT": example_box_9,
        "finalised": True,
    }

    rtn = Return.from_dict(input)

    assert(rtn.periodKey == example_period_key)
    assert(rtn.vatDueSales == example_box_1)
    assert(rtn.vatDueAcquisitions == example_box_2)
    assert(rtn.totalVatDue == example_box_3)
    assert(rtn.vatReclaimedCurrPeriod == example_box_4)
    assert(rtn.netVatDue == example_box_5)
    assert(rtn.totalValueSalesExVAT == example_box_6)
    assert(rtn.totalValuePurchasesExVAT == example_box_7)
    assert(rtn.totalValueGoodsSuppliedExVAT == example_box_8)
    assert(rtn.totalAcquisitionsExVAT == example_box_9)
    assert(rtn.finalised == True)

