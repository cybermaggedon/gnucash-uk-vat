#!/usr/bin/env python3

import piecash
import random
import shutil
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleTestGenerator:
    """Simple test data generator for initial testing"""
    
    def __init__(self, gnucash_file: str):
        self.gnucash_file = gnucash_file
        self.accounts = {}
        self.gbp = None
        
    def _load_accounts(self, book):
        """Load and cache accounts from book"""
        self.accounts = {}
        for account in book.accounts:
            self.accounts[account.fullname] = account
        
        # Find GBP commodity
        for commodity in book.commodities:
            if commodity.mnemonic == 'GBP':
                self.gbp = commodity
                break
                
        logger.info(f"Loaded {len(self.accounts)} accounts")
    
    def _create_split(self, account, amount: Decimal, transaction, memo: str = ""):
        """Helper to create properly formatted splits"""
        return piecash.Split(
            account=account,
            value=amount,
            quantity=amount,
            memo=memo,
            transaction=transaction
        )
    
    def generate_simple_test(self, output_file: str = "simple_test_data.gnucash"):
        """Generate a few simple test transactions"""
        # Copy existing file
        shutil.copy2(self.gnucash_file, output_file)
        
        # Open for modification
        book = piecash.open_book(output_file, readonly=False)
        self._load_accounts(book)
        
        # Get key accounts
        sales_account = self.accounts.get("Income:Sales:UK")
        bank_account = self.accounts.get("Bank Accounts:Current Account")
        vat_output = self.accounts.get("VAT:Output:Sales")
        
        if not all([sales_account, bank_account, self.gbp]):
            logger.error("Required accounts not found")
            book.close()
            return
        
        logger.info("Creating test transactions...")
        
        try:
            # Create a simple sale transaction
            txn = piecash.Transaction(
                currency=self.gbp,
                description="Test Sale - TechCorp Solutions Ltd",
                post_date=date(2023, 6, 15),
                enter_date=datetime.now()
            )
            
            net_amount = Decimal('1000.00')
            vat_amount = Decimal('200.00')
            gross_amount = Decimal('1200.00')
            
            # Sales split (credit)
            self._create_split(sales_account, -net_amount, txn, "Software services")
            
            # VAT output split (credit)
            if vat_output:
                self._create_split(vat_output, -vat_amount, txn, "VAT 20%")
            
            # Bank receipt (debit)
            self._create_split(bank_account, gross_amount, txn, "Payment received")
            
            logger.info("Created test sale transaction")
            
            # Save and close
            book.save()
            book.close()
            
            logger.info(f"Simple test data saved to: {output_file}")
            
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            book.close()
            raise

def main():
    generator = SimpleTestGenerator('accounts/accounts2.gnucash')
    generator.generate_simple_test()

if __name__ == "__main__":
    main()