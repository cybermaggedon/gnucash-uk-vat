#!/usr/bin/env python3

import piecash
import random
import json
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from dateutil.relativedelta import relativedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BusinessConfig:
    """Configuration for realistic business data generation"""
    start_year: int = 2021
    end_year: int = 2023
    financial_year_end: str = "31-03"  # DD-MM format
    
    # Business growth parameters
    monthly_revenue_base: int = 25000  # Starting monthly revenue in £
    annual_growth_rate: float = 20.0   # Percentage
    international_percentage: float = 40.0  # % of revenue from international sales
    
    # Staff and costs
    initial_staff: int = 2
    final_staff: int = 8
    director_salary_annual: int = 8788  # Optimal for NICs
    
    # Asset purchases by period
    major_asset_purchases: Dict[str, Dict[str, int]] = field(default_factory=lambda: {
        '2021-Q2': {'office_equipment': 15000},
        '2022-Q1': {'company_car': 25000},
        '2023-Q3': {'server_infrastructure': 8000}
    })
    
    # VAT and tax configuration
    vat_standard_rate: float = 20.0
    vat_registration_threshold: int = 85000
    
    # Realistic business data
    business_type: str = 'software_consultancy'
    random_seed: Optional[int] = 42  # For reproducible results

@dataclass
class CompanyData:
    """Realistic company and supplier names"""
    customers: List[str] = field(default_factory=lambda: [
        'TechCorp Solutions Ltd', 'Digital Dynamics UK', 'InnovateTech Europe',
        'Global Systems Inc', 'MegaData Corporation', 'CloudFirst Technologies',
        'DataDriven Analytics', 'SmartFlow Systems', 'NextGen Digital',
        'Enterprise Solutions Group', 'ConnectedWorld Ltd', 'AgileCore Systems'
    ])
    
    uk_suppliers: List[str] = field(default_factory=lambda: [
        'Office Essentials Ltd', 'TechSupply UK', 'London Cleaning Services',
        'Thames Telecom', 'Capital Accounting', 'Metropolitan Insurance',
        'UK Travel Solutions', 'Professional Training Co', 'Elite Recruitment'
    ])
    
    eu_suppliers: List[str] = field(default_factory=lambda: [
        'Berlin Tech GmbH', 'Amsterdam Software BV', 'Paris Digital SARL',
        'Stockholm Systems AB', 'Milan Innovation Srl', 'Munich Hardware GmbH'
    ])
    
    international_suppliers: List[str] = field(default_factory=lambda: [
        'Silicon Valley Solutions', 'Tokyo Tech Corp', 'Sydney Software',
        'Canadian Cloud Co', 'Singapore Systems', 'New York Analytics'
    ])

class TestDataGenerator:
    """Generate realistic multi-year UK business test data"""
    
    def __init__(self, gnucash_file: str, config: Optional[BusinessConfig] = None):
        self.gnucash_file = gnucash_file
        self.config = config or BusinessConfig()
        self.company_data = CompanyData()
        self.book = None
        self.accounts = {}
        self.gbp = None
        
        if self.config.random_seed:
            random.seed(self.config.random_seed)
    
    def _open_book(self):
        """Open GnuCash book and cache account references"""
        self.book = piecash.open_book(self.gnucash_file, readonly=True)
        # Find GBP commodity
        self.gbp = None
        for commodity in self.book.commodities:
            if commodity.mnemonic == 'GBP':
                self.gbp = commodity
                break
        
        if not self.gbp:
            raise ValueError("GBP commodity not found in source book")
        
        # Cache commonly used accounts
        for account in self.book.accounts:
            self.accounts[account.fullname] = account
        
        logger.info(f"Loaded {len(self.accounts)} accounts from {self.gnucash_file}")
    
    def _create_new_book(self, output_file: str):
        """Create new book by copying existing structure"""
        import shutil
        
        # Copy the existing file and work with that
        shutil.copy2(self.gnucash_file, output_file)
        logger.info(f"Copied existing book structure to: {output_file}")
        
        # Open the copied book for modification
        new_book = piecash.open_book(output_file, readonly=False)
        return new_book
    
    def _get_account(self, account_path: str):
        """Get account by full path"""
        return self.accounts.get(account_path)
    
    def _calculate_vat(self, net_amount: Decimal, vat_rate: float = 20.0) -> Tuple[Decimal, Decimal]:
        """Calculate VAT amount and gross total"""
        vat_amount = (net_amount * Decimal(vat_rate) / Decimal(100)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        gross_amount = net_amount + vat_amount
        return vat_amount, gross_amount
    
    def _create_split(self, account, amount: Decimal, transaction, memo: str = ""):
        """Helper to create properly formatted splits"""
        return piecash.Split(
            account=account,
            value=amount,
            quantity=amount,
            memo=memo,
            transaction=transaction
        )
    
    def _generate_date_range(self, start_year: int, end_year: int) -> List[date]:
        """Generate realistic transaction dates with seasonal patterns"""
        dates = []
        
        for year in range(start_year, end_year + 1):
            for month in range(1, 13):
                # More transactions in Q4 (busy period) and fewer in August
                if month in [10, 11, 12]:  # Q4 busy period
                    transactions_this_month = random.randint(25, 40)
                elif month == 8:  # August quiet period
                    transactions_this_month = random.randint(8, 15)
                else:
                    transactions_this_month = random.randint(15, 25)
                
                for _ in range(transactions_this_month):
                    day = random.randint(1, 28)  # Avoid month-end issues
                    dates.append(date(year, month, day))
        
        return sorted(dates)
    
    def _calculate_monthly_revenue(self, transaction_date: date) -> int:
        """Calculate revenue for given month with growth"""
        years_elapsed = transaction_date.year - self.config.start_year
        months_elapsed = years_elapsed * 12 + (transaction_date.month - 1)
        
        # Apply annual growth rate
        growth_factor = (1 + self.config.annual_growth_rate / 100) ** (months_elapsed / 12)
        monthly_revenue = int(self.config.monthly_revenue_base * growth_factor)
        
        # Add seasonal variation
        seasonal_factors = {
            1: 0.9, 2: 0.95, 3: 1.1,   # Q1: Slow start, strong March
            4: 1.0, 5: 1.05, 6: 1.1,   # Q2: Steady growth
            7: 0.95, 8: 0.8, 9: 1.0,   # Q3: August slowdown
            10: 1.15, 11: 1.2, 12: 1.3 # Q4: Strong finish
        }
        
        monthly_revenue = int(monthly_revenue * seasonal_factors[transaction_date.month])
        return monthly_revenue
    
    def _generate_sales_transaction(self, transaction_date: date, new_book) -> Optional[piecash.Transaction]:
        """Generate realistic sales transaction"""
        # Determine transaction type and customer
        rand_val = random.random()
        
        if rand_val < 0.6:  # 60% UK sales
            customer = random.choice(self.company_data.customers)
            net_amount = Decimal(random.randint(500, 8000))
            vat_rate = 20.0
            sales_account_path = "Income:Sales:UK"
            vat_output_path = "VAT:Output:Sales"
            description = f"Services to {customer}"
            
        elif rand_val < 0.8:  # 20% EU sales (reverse charge)
            customer = random.choice(self.company_data.eu_suppliers)
            net_amount = Decimal(random.randint(1000, 15000))
            vat_rate = 0.0  # Reverse charge
            sales_account_path = "Income:Sales:EU:Services"
            vat_output_path = None
            description = f"Consultancy services to {customer}"
            
        else:  # 20% International sales
            customer = random.choice(self.company_data.international_suppliers)
            net_amount = Decimal(random.randint(2000, 25000))
            vat_rate = 0.0  # Zero-rated export
            sales_account_path = "Income:Sales:World"
            vat_output_path = None
            description = f"Software license to {customer}"
        
        # Get accounts
        sales_account = self._get_account(sales_account_path)
        bank_account = self._get_account("Bank Accounts:Current Account")
        
        if not sales_account or not bank_account:
            logger.warning(f"Missing accounts for sales transaction: {sales_account_path}")
            return None
        
        # Calculate VAT
        vat_amount, gross_amount = self._calculate_vat(net_amount, vat_rate)
        
        # Create transaction
        try:
            txn = piecash.Transaction(
                currency=self.gbp,
                description=description,
                post_date=transaction_date,
                enter_date=datetime.now()
            )
            
            # Sales split (credit)
            piecash.Split(
                account=sales_account,
                value=-net_amount,
                quantity=-net_amount,
                memo="",
                transaction=txn
            )
            
            # VAT output split if applicable
            if vat_output_path and vat_amount > 0:
                vat_account = self._get_account(vat_output_path)
                if vat_account:
                    piecash.Split(
                        account=vat_account,
                        value=-vat_amount,
                        transaction=txn
                    )
            
            # Bank receipt (debit)
            piecash.Split(
                account=bank_account,
                value=gross_amount,
                transaction=txn
            )
            
            return txn
            
        except Exception as e:
            logger.error(f"Failed to create sales transaction: {e}")
            return None
    
    def _generate_purchase_transaction(self, transaction_date: date, new_book) -> Optional[piecash.Transaction]:
        """Generate realistic purchase transaction"""
        rand_val = random.random()
        
        # Determine purchase type
        if rand_val < 0.3:  # Office expenses
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(50, 500))
            expense_account_path = "Expenses:VAT Purchases:Office"
            description = f"Office supplies from {supplier}"
            vat_rate = 20.0
            
        elif rand_val < 0.5:  # Professional services
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(200, 2000))
            expense_account_path = "Expenses:VAT Purchases:Accountant"
            description = f"Professional services from {supplier}"
            vat_rate = 20.0
            
        elif rand_val < 0.7:  # Software/telecoms
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(100, 800))
            expense_account_path = "Expenses:VAT Purchases:Software"
            description = f"Software subscription from {supplier}"
            vat_rate = 20.0
            
        elif rand_val < 0.85:  # Travel
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(150, 1200))
            expense_account_path = "Expenses:VAT Purchases:Travel/Accom"
            description = f"Business travel via {supplier}"
            vat_rate = 20.0
            
        else:  # EU reverse VAT purchase
            supplier = random.choice(self.company_data.eu_suppliers)
            net_amount = Decimal(random.randint(300, 2500))
            expense_account_path = "Expenses:VAT Purchases:EU Reverse VAT"
            description = f"Equipment from {supplier}"
            vat_rate = 20.0  # Reverse VAT - both input and output
        
        # Get accounts
        expense_account = self._get_account(expense_account_path)
        bank_account = self._get_account("Bank Accounts:Current Account")
        vat_input_account = self._get_account("VAT:Input")
        
        if not expense_account or not bank_account:
            logger.warning(f"Missing accounts for purchase: {expense_account_path}")
            return None
        
        # Calculate VAT
        vat_amount, gross_amount = self._calculate_vat(net_amount, vat_rate)
        
        try:
            txn = piecash.Transaction(
                currency=self.gbp,
                description=description,
                post_date=transaction_date,
                enter_date=datetime.now()
            )
            
            # Expense split (debit)
            piecash.Split(
                account=expense_account,
                value=net_amount,
                transaction=txn
            )
            
            # VAT input split
            if vat_input_account and vat_amount > 0:
                piecash.Split(
                    account=vat_input_account,
                    value=vat_amount,
                    transaction=txn
                )
            
            # Handle EU reverse VAT
            if "EU Reverse VAT" in expense_account_path:
                vat_output_eu = self._get_account("VAT:Output:EU")
                if vat_output_eu:
                    piecash.Split(
                        account=vat_output_eu,
                        value=-vat_amount,
                        transaction=txn
                    )
            
            # Bank payment (credit)
            piecash.Split(
                account=bank_account,
                value=-gross_amount,
                transaction=txn
            )
            
            return txn
            
        except Exception as e:
            logger.error(f"Failed to create purchase transaction: {e}")
            return None
    
    def _generate_payroll_transaction(self, transaction_date: date, new_book) -> Optional[piecash.Transaction]:
        """Generate monthly payroll transaction"""
        # Only generate on month-end dates
        if transaction_date.day < 25:
            return None
        
        # Calculate staff count based on growth
        years_elapsed = transaction_date.year - self.config.start_year
        months_elapsed = years_elapsed * 12 + (transaction_date.month - 1)
        total_months = (self.config.end_year - self.config.start_year + 1) * 12
        
        staff_growth_factor = months_elapsed / total_months
        current_staff = int(self.config.initial_staff + 
                          (self.config.final_staff - self.config.initial_staff) * staff_growth_factor)
        
        # Director's salary (monthly)
        director_gross_monthly = Decimal(self.config.director_salary_annual) / 12
        director_tax = director_gross_monthly * Decimal('0.20')  # 20% tax
        director_nics_employee = director_gross_monthly * Decimal('0.12')  # Employee NICs
        director_nics_employer = director_gross_monthly * Decimal('0.138')  # Employer NICs
        director_net = director_gross_monthly - director_tax - director_nics_employee
        
        # Employee salaries (if any additional staff)
        employee_count = max(0, current_staff - 1)  # Excluding director
        employee_gross_monthly = Decimal(2500) * employee_count  # £2.5K per employee
        employee_tax = employee_gross_monthly * Decimal('0.20')
        employee_nics_employee = employee_gross_monthly * Decimal('0.12')
        employee_nics_employer = employee_gross_monthly * Decimal('0.138')
        employee_net = employee_gross_monthly - employee_tax - employee_nics_employee
        
        total_gross = director_gross_monthly + employee_gross_monthly
        total_tax = director_tax + employee_tax
        total_nics_employee = director_nics_employee + employee_nics_employee
        total_nics_employer = director_nics_employer + employee_nics_employer
        total_net = director_net + employee_net
        
        if total_gross == 0:
            return None
        
        # Get accounts
        director_fees_account = self._get_account("Expenses:Emoluments:Director's Fees")
        employees_account = self._get_account("Expenses:Emoluments:Employees:Net Salaries")
        tax_account = self._get_account("Expenses:Emoluments:Employees:Income Tax")
        nics_employee_account = self._get_account("Expenses:Emoluments:Employees:NICs")
        nics_employer_account = self._get_account("Expenses:Emoluments:Employer's NICs")
        bank_account = self._get_account("Bank Accounts:Current Account")
        tax_liability_account = self._get_account("Liabilities:Owed Tax/NI")
        
        try:
            txn = piecash.Transaction(
                currency=self.gbp,
                description=f"Payroll for {transaction_date.strftime('%B %Y')} - {current_staff} staff",
                post_date=transaction_date,
                enter_date=datetime.now()
            )
            
            # Director's fees
            if director_fees_account:
                piecash.Split(
                    account=director_fees_account,
                    value=director_gross_monthly,
                    transaction=txn
                )
            
            # Employee costs
            if employee_count > 0 and employees_account:
                piecash.Split(
                    account=employees_account,
                    value=employee_net,
                    transaction=txn
                )
            
            # Tax and NICs
            if tax_account and total_tax > 0:
                piecash.Split(
                    account=tax_account,
                    value=total_tax,
                    transaction=txn
                )
            
            if nics_employee_account and total_nics_employee > 0:
                piecash.Split(
                    account=nics_employee_account,
                    value=total_nics_employee,
                    transaction=txn
                )
            
            if nics_employer_account and total_nics_employer > 0:
                piecash.Split(
                    account=nics_employer_account,
                    value=total_nics_employer,
                    transaction=txn
                )
            
            # Net payments (credit bank)
            if bank_account:
                piecash.Split(
                    account=bank_account,
                    value=-total_net,
                    transaction=txn
                )
            
            # Tax liability (credit)
            if tax_liability_account:
                tax_and_nics_total = total_tax + total_nics_employee + total_nics_employer
                piecash.Split(
                    account=tax_liability_account,
                    value=-tax_and_nics_total,
                    transaction=txn
                )
            
            return txn
            
        except Exception as e:
            logger.error(f"Failed to create payroll transaction: {e}")
            return None
    
    def _generate_asset_purchase(self, asset_type: str, amount: int, transaction_date: date, new_book) -> Optional[piecash.Transaction]:
        """Generate capital asset purchase"""
        asset_account_map = {
            'office_equipment': "Assets:Capital Equipment:Computer Equipment",
            'company_car': "Assets:Capital Equipment:Other",  # No specific car account
            'server_infrastructure': "Assets:Capital Equipment:Computer Equipment"
        }
        
        asset_account_path = asset_account_map.get(asset_type)
        if not asset_account_path:
            logger.warning(f"Unknown asset type: {asset_type}")
            return None
        
        asset_account = self._get_account(asset_account_path)
        vat_input_account = self._get_account("VAT:Input")
        bank_account = self._get_account("Bank Accounts:Current Account")
        
        if not asset_account or not bank_account:
            logger.warning(f"Missing accounts for asset purchase: {asset_account_path}")
            return None
        
        net_amount = Decimal(amount)
        vat_amount, gross_amount = self._calculate_vat(net_amount, 20.0)
        
        try:
            txn = piecash.Transaction(
                currency=self.gbp,
                description=f"Purchase of {asset_type.replace('_', ' ')} - £{amount:,}",
                post_date=transaction_date,
                enter_date=datetime.now()
            )
            
            # Asset (debit)
            piecash.Split(
                account=asset_account,
                value=net_amount,
                transaction=txn
            )
            
            # VAT input (debit)
            if vat_input_account:
                piecash.Split(
                    account=vat_input_account,
                    value=vat_amount,
                    transaction=txn
                )
            
            # Bank payment (credit)
            piecash.Split(
                account=bank_account,
                value=-gross_amount,
                transaction=txn
            )
            
            return txn
            
        except Exception as e:
            logger.error(f"Failed to create asset purchase: {e}")
            return None
    
    def generate_realistic_business(self, output_file: Optional[str] = None) -> str:
        """Generate complete multi-year business data"""
        if not output_file:
            output_file = f"business_data_{self.config.start_year}-{self.config.end_year}.gnucash"
        
        logger.info(f"Generating business data from {self.config.start_year} to {self.config.end_year}")
        
        self._open_book()
        new_book = self._create_new_book(output_file)
        
        # Update account cache to use new book's accounts
        self.accounts = {}
        for account in new_book.accounts:
            self.accounts[account.fullname] = account
        
        # Update GBP reference to new book's commodity
        for commodity in new_book.commodities:
            if commodity.mnemonic == 'GBP':
                self.gbp = commodity
                break
        
        # Generate transaction dates
        transaction_dates = self._generate_date_range(
            self.config.start_year, 
            self.config.end_year
        )
        
        logger.info(f"Generating {len(transaction_dates)} transactions")
        
        transactions_created = 0
        
        for transaction_date in transaction_dates:
            # Generate different types of transactions
            transaction_type = random.random()
            
            if transaction_type < 0.4:  # 40% sales
                txn = self._generate_sales_transaction(transaction_date, new_book)
            elif transaction_type < 0.7:  # 30% purchases
                txn = self._generate_purchase_transaction(transaction_date, new_book)
            elif transaction_type < 0.75:  # 5% payroll (monthly)
                txn = self._generate_payroll_transaction(transaction_date, new_book)
            else:  # 25% other transactions (skip for now)
                continue
            
            if txn:
                transactions_created += 1
        
        # Generate scheduled asset purchases
        for period, assets in self.config.major_asset_purchases.items():
            year, quarter = period.split('-')
            quarter_month = {'Q1': 2, 'Q2': 5, 'Q3': 8, 'Q4': 11}[quarter]
            asset_date = date(int(year), quarter_month, 15)
            
            for asset_type, amount in assets.items():
                txn = self._generate_asset_purchase(asset_type, amount, asset_date, new_book)
                if txn:
                    transactions_created += 1
        
        # Save and close
        new_book.save()
        new_book.close()
        self.book.close()
        
        logger.info(f"Generated {transactions_created} transactions in {output_file}")
        return output_file

def main():
    """Example usage"""
    config = BusinessConfig(
        start_year=2021,
        end_year=2023,
        monthly_revenue_base=25000,
        annual_growth_rate=20.0,
        international_percentage=40.0,
        initial_staff=2,
        final_staff=8
    )
    
    generator = TestDataGenerator('accounts/accounts2.gnucash', config)
    output_file = generator.generate_realistic_business()
    print(f"Generated test data in: {output_file}")

if __name__ == "__main__":
    main()