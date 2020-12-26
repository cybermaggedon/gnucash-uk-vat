
import json
from datetime import datetime, timedelta

class Obligation:
    def __init__(self, pKey, status, start, end, received=None, due=None):
        self.periodKey = pKey
        self.status = status
        self.start = start
        self.end = end
        self.received = received
        self.due = due
    @staticmethod
    def from_dict(d):
        status  =  d["status"]
        periodKey  =  d["periodKey"]
        start  =  datetime.fromisoformat(d["start"]).date()
        end  =  datetime.fromisoformat(d["end"]).date()
        if "due" in d:
            due  =  datetime.fromisoformat(d["due"]).date()
        else:
            due = None
        if "received" in d:
            received  =  datetime.fromisoformat(d["received"]).date()
        else:
            received = None
        return Obligation(periodKey, status, start, end, received, due)
    def to_dict(self):
        obj = {
            "status": self.status,
            "periodKey": self.periodKey,
            "start": self.start.isoformat(),
            "end": self.end.isoformat()
        }
        if self.received != None:
            obj["received"] = self.due.isoformat()
        if self.due != None:
            obj["due"] = self.due.isoformat()
        return obj
    def in_range(self, start, end):
        if self.start >= start and self.start < end:
            return True
        if self.end >= start and self.end < end:
            return True
        if self.start <= start and self.end > end:
            return True
        return False

class Liability:
    def __init__(self, start, end, typ, original, outstanding=None, due=None):
        self.start = start
        self.end = end
        self.typ = typ
        self.original = original
        self.outstanding = outstanding
        self.due = due
    @staticmethod
    def from_dict(d):
        start  =  datetime.fromisoformat(d["taxPeriod"]["from"]).date()
        end  =  datetime.fromisoformat(d["taxPeriod"]["to"]).date()
        typ  =  d["type"]
        orig  =  d["originalAmount"]
        if "outstandingAmount" in  d:
            outs = d["outstandingAmount"]
        else:
            outs = None
        if "due" in d:
            due  =  datetime.fromisoformat(d["due"]).date()
        else:
            due = None
        return Liability(start, end, typ, orig, outs, due)
    def to_dict(self):
        obj = {
            "type": self.typ,
            "originalAmount": self.original,
            "outstandingAmount": self.outstanding,
        }

        if self.start and self.end:
            obj["taxPeriod"] = {
                "from": self.start.isoformat(),
                "to": self.end.isoformat()
            }
        if self.due:
            obj["due"] = self.due.isoformat()
        return obj
    def in_range(self, start, end):
        if self.start >= start and self.start < end:
            return True
        if self.end >= start and self.end < end:
            return True
        if self.start <= start and self.end > end:
            return True
        return False

class Payment:
    def __init__(self, amount, received):
        self.amount = amount
        self.received = received
    @staticmethod
    def from_dict(d):
        amount  =  d["amount"]
        received  =  datetime.fromisoformat(d["received"]).date()
        return Payment(amount, received)
    def to_dict(self):
        return {
            "amount": self.amount,
            "received": self.received.isoformat()
        }
    def in_range(self, start, end):
        if self.received >= start and self.received < end:
            return True
        return False

class Return:
    def __init__(self):
        self.periodKey = None
        self.vatDueSales = None
        self.vatDueAcquisitions = None
        self.totalVatDue = None
        self.vatReclaimedCurrPeriod = None
        self.netVatDue = None
        self.totalValueSalesExVAT = None
        self.totalValuePurchasesExVAT = None
        self.totalValueGoodsSuppliedExVAT = None
        self.totalAcquisitionsExVAT = None
    @staticmethod
    def from_dict(d):
        r = Return()
        r.periodKey = d["periodKey"]
        r.vatDueSales = d["vatDueSales"]
        r.vatDueAcquisitions = d["vatDueAcquisitions"]
        r.totalVatDue = d["totalVatDue"]
        r.vatReclaimedCurrPeriod = d["vatReclaimedCurrPeriod"]
        r.netVatDue = d["netVatDue"]
        r.totalValueSalesExVAT = d["totalValueSalesExVAT"]
        r.totalValuePurchasesExVAT = d["totalValuePurchasesExVAT"]
        r.totalValueGoodsSuppliedExVAT = d["totalValueGoodsSuppliedExVAT"]
        r.totalAcquisitionsExVAT = d["totalAcquisitionsExVAT"]
        return r
    def to_dict(self):
        return {
            "periodKey": self.periodKey,
            "vatDueSales": self.vatDueSales,
            "vatDueAcquisitions": self.vatDueAcquisitions,
            "totalVatDue": self.totalVatDue,
            "vatReclaimedCurrPeriod": self.vatReclaimedCurrPeriod,
            "netVatDue": self.netVatDue,
            "totalValueSalesExVAT": self.totalValueSalesExVAT,
            "totalValuePurchasesExVAT": self.totalValuePurchasesExVAT,
            "totalValueGoodsSuppliedExVAT": self.totalValueGoodsSuppliedExVAT,
            "totalAcquisitionsExVAT": self.totalAcquisitionsExVAT,
        }

class VATUser:
    def __init__(self):
        self.obligations = []
        self.returns = []
        self.liabilities = []
        self.payments = []
    @staticmethod
    def from_dict(d):
        v = VATUser()
        v.obligations = [
            Obligation.from_dict(v)
            for v in d["obligations"]
        ]
        v.returns = [
            Return.from_dict(v)
            for v in d["returns"]
        ]
        v.payments = [
            Payment.from_dict(v)
            for v in d["payments"]
        ]
        v.liabilities = [
            Liability.from_dict(v)
            for v in d["liabilities"]
        ]
        return v
    def to_dict(self):
        return {
            "obligations": [ v.to_dict() for v in self.obligations ],
            "returns": [ v.to_dict() for v in self.returns ],
            "payments": [ v.to_dict() for v in self.payments ],
            "liabilities": [v.to_dict() for v in self.liabilities ]
        }
    def add_return(self, rtn):

        key = rtn.periodKey

        obl = None
        for v in self.obligations:
            if v.periodKey == key and v.status == 'O': obl = v

        if obl == None:
            raise RuntimeError("periodKey does not match an open obligation")

        v.received = datetime.utcnow().date()
        v.status = 'F'

        due =  obl.end + timedelta(days=30)

        self.liabilities.append(
            Liability(obl.start, obl.end, "Net VAT", rtn.netVatDue,
                      rtn.netVatDue, due)
        )
        
        self.returns.append(rtn)

class VATData:
    def __init__(self):
        self.data = {}
    @staticmethod
    def from_dict(d):
        v = VATData()
        for vrn in d:
            v.data[vrn] = VATUser.from_dict(d[vrn])
        return v
    def to_dict(self):
        return {
            k: self.data[k].to_dict()
            for k in self.data
        }
    @staticmethod
    def from_json(s):
        data = json.loads(s)
        return VATData.from_dict(data)
    def add_return(self, vrn, rtn):
        self.data[vrn].add_return(rtn)
