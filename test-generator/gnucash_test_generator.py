#!/usr/bin/env python3
"""
GnuCash UK Business Test Data Generator

A command-line utility to generate realistic UK business transactions for testing
VAT reporting, accounting scenarios, and multi-year business lifecycle events.

Usage:
    python gnucash_test_generator.py --help
    python gnucash_test_generator.py --input accounts/accounts2.gnucash --output test_2021-2023.gnucash
    python gnucash_test_generator.py --start-year 2021 --end-year 2023 --revenue 50000 --growth 15
"""

import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import logging
from typing import Dict, List, Optional

# Import our generator classes
from dataclasses import dataclass, field
import piecash
import random
import shutil
from decimal import ROUND_HALF_UP
from dateutil.relativedelta import relativedelta

# Configure logging
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

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
    
    # Transaction generation parameters
    transactions_per_month_base: int = 25
    seasonal_variation: bool = True
    include_payroll: bool = True
    include_assets: bool = True
    include_depreciation: bool = True

@dataclass
class CompanyData:
    """Realistic company and supplier names"""
    customers: List[str] = field(default_factory=lambda: [
        'TechCorp Solutions Ltd', 'Digital Dynamics UK', 'InnovateTech Europe',
        'Global Systems Inc', 'MegaData Corporation', 'CloudFirst Technologies',
        'DataDriven Analytics', 'SmartFlow Systems', 'NextGen Digital',
        'Enterprise Solutions Group', 'ConnectedWorld Ltd', 'AgileCore Systems',
        'Innovation Labs', 'SmartTech Consulting', 'Digital Transformation Co',
        'Future Systems Ltd', 'Advanced Analytics Group', 'TechSolutions Pro'
    ])
    
    uk_suppliers: List[str] = field(default_factory=lambda: [
        'Office Essentials Ltd', 'TechSupply UK', 'London Cleaning Services',
        'Thames Telecom', 'Capital Accounting', 'Metropolitan Insurance',
        'UK Travel Solutions', 'Professional Training Co', 'Elite Recruitment',
        'Business Systems UK', 'London Legal Services', 'Thames Valley Marketing'
    ])
    
    eu_suppliers: List[str] = field(default_factory=lambda: [
        'Berlin Tech GmbH', 'Amsterdam Software BV', 'Paris Digital SARL',
        'Stockholm Systems AB', 'Milan Innovation Srl', 'Munich Hardware GmbH',
        'Brussels Analytics SA', 'Copenhagen Cloud ApS', 'Dublin Data Ltd'
    ])
    
    international_suppliers: List[str] = field(default_factory=lambda: [
        'Silicon Valley Solutions', 'Tokyo Tech Corp', 'Sydney Software',
        'Canadian Cloud Co', 'Singapore Systems', 'New York Analytics',
        'San Francisco Innovations', 'Toronto Technologies', 'Melbourne Data'
    ])

class GnuCashTestGenerator:
    """Enhanced test data generator with command-line interface"""
    
    def __init__(self, input_file: str, config: BusinessConfig):
        self.input_file = input_file
        self.config = config
        self.company_data = CompanyData()
        self.accounts = {}
        self.gbp = None
        self.logger = logging.getLogger(__name__)
        
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)
            self.logger.info(f"Random seed set to: {self.config.random_seed}")
    
    def _validate_input_file(self) -> bool:
        """Validate input GnuCash file exists and is readable"""
        if not os.path.exists(self.input_file):
            self.logger.error(f"Input file does not exist: {self.input_file}")
            return False
        
        try:
            # Test opening the file
            book = piecash.open_book(self.input_file, readonly=True)
            book.close()
            self.logger.info(f"Input file validated: {self.input_file}")
            return True
        except Exception as e:
            self.logger.error(f"Cannot open input file {self.input_file}: {e}")
            return False
    
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
                
        if not self.gbp:
            raise ValueError("GBP commodity not found in book")
            
        self.logger.info(f"Loaded {len(self.accounts)} accounts")
        
        # Log key accounts for verification
        key_accounts = [
            "Income:Sales:UK", "VAT:Output:Sales", "Bank Accounts:Current Account",
            "Expenses:VAT Purchases:Office", "VAT:Input"
        ]
        
        missing_accounts = []
        for acc in key_accounts:
            if acc not in self.accounts:
                missing_accounts.append(acc)
        
        if missing_accounts:
            self.logger.warning(f"Missing key accounts: {missing_accounts}")
    
    def _create_split(self, account, amount: Decimal, transaction, memo: str = ""):
        """Helper to create properly formatted splits"""
        return piecash.Split(
            account=account,
            value=amount,
            quantity=amount,
            memo=memo,
            transaction=transaction
        )
    
    def _calculate_vat(self, net_amount: Decimal, vat_rate: float = 20.0) -> tuple[Decimal, Decimal]:
        """Calculate VAT amount and gross total"""
        vat_amount = (net_amount * Decimal(vat_rate) / Decimal(100)).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        gross_amount = net_amount + vat_amount
        return vat_amount, gross_amount
    
    def _generate_date_range(self) -> List[date]:
        """Generate realistic transaction dates with seasonal patterns"""
        dates = []
        
        for year in range(self.config.start_year, self.config.end_year + 1):
            for month in range(1, 13):
                base_transactions = self.config.transactions_per_month_base
                
                if self.config.seasonal_variation:
                    # More transactions in Q4 (busy period) and fewer in August
                    if month in [10, 11, 12]:  # Q4 busy period
                        transactions_this_month = random.randint(int(base_transactions * 1.2), int(base_transactions * 1.6))
                    elif month == 8:  # August quiet period
                        transactions_this_month = random.randint(int(base_transactions * 0.4), int(base_transactions * 0.7))
                    else:
                        transactions_this_month = random.randint(int(base_transactions * 0.8), int(base_transactions * 1.2))
                else:
                    transactions_this_month = base_transactions
                
                # Generate random dates in month
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
        
        if self.config.seasonal_variation:
            # Add seasonal variation
            seasonal_factors = {
                1: 0.9, 2: 0.95, 3: 1.1,   # Q1: Slow start, strong March
                4: 1.0, 5: 1.05, 6: 1.1,   # Q2: Steady growth
                7: 0.95, 8: 0.8, 9: 1.0,   # Q3: August slowdown
                10: 1.15, 11: 1.2, 12: 1.3 # Q4: Strong finish
            }
            monthly_revenue = int(monthly_revenue * seasonal_factors[transaction_date.month])
        
        return monthly_revenue
    
    def _generate_sales_transaction(self, transaction_date: date, book) -> Optional[piecash.Transaction]:
        """Generate realistic sales transaction"""
        rand_val = random.random()
        
        if rand_val < 0.6:  # 60% UK sales
            customer = random.choice(self.company_data.customers)
            net_amount = Decimal(random.randint(500, 8000))
            vat_rate = self.config.vat_standard_rate
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
        sales_account = self.accounts.get(sales_account_path)
        bank_account = self.accounts.get("Bank Accounts:Current Account")
        
        if not sales_account or not bank_account:
            self.logger.debug(f"Missing accounts for sales transaction: {sales_account_path}")
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
            
            # Sales split (credit)
            self._create_split(sales_account, -net_amount, txn, "Sales revenue")
            
            # VAT output split if applicable
            if vat_output_path and vat_amount > 0:
                vat_account = self.accounts.get(vat_output_path)
                if vat_account:
                    self._create_split(vat_account, -vat_amount, txn, f"VAT {vat_rate}%")
            
            # Bank receipt (debit)
            self._create_split(bank_account, gross_amount, txn, "Payment received")
            
            return txn
            
        except Exception as e:
            self.logger.error(f"Failed to create sales transaction: {e}")
            return None
    
    def _generate_purchase_transaction(self, transaction_date: date, book) -> Optional[piecash.Transaction]:
        """Generate realistic purchase transaction"""
        rand_val = random.random()
        
        # Determine purchase type
        if rand_val < 0.25:  # Office expenses
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(50, 800))
            expense_account_path = "Expenses:VAT Purchases:Office"
            description = f"Office supplies from {supplier}"
            vat_rate = self.config.vat_standard_rate
            
        elif rand_val < 0.4:  # Professional services
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(300, 3000))
            expense_account_path = "Expenses:VAT Purchases:Accountant"
            description = f"Professional services from {supplier}"
            vat_rate = self.config.vat_standard_rate
            
        elif rand_val < 0.55:  # Software/telecoms
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(100, 1200))
            expense_account_path = "Expenses:VAT Purchases:Software"
            description = f"Software subscription from {supplier}"
            vat_rate = self.config.vat_standard_rate
            
        elif rand_val < 0.7:  # Travel
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(150, 2000))
            expense_account_path = "Expenses:VAT Purchases:Travel/Accom"
            description = f"Business travel via {supplier}"
            vat_rate = self.config.vat_standard_rate
            
        elif rand_val < 0.85:  # Telecoms
            supplier = random.choice(self.company_data.uk_suppliers)
            net_amount = Decimal(random.randint(80, 600))
            expense_account_path = "Expenses:VAT Purchases:Telecoms"
            description = f"Telecoms services from {supplier}"
            vat_rate = self.config.vat_standard_rate
            
        else:  # EU reverse VAT purchase
            supplier = random.choice(self.company_data.eu_suppliers)
            net_amount = Decimal(random.randint(500, 3000))
            expense_account_path = "Expenses:VAT Purchases:EU Reverse VAT"
            description = f"Equipment from {supplier}"
            vat_rate = self.config.vat_standard_rate
        
        # Get accounts
        expense_account = self.accounts.get(expense_account_path)
        bank_account = self.accounts.get("Bank Accounts:Current Account")
        vat_input_account = self.accounts.get("VAT:Input")
        
        if not expense_account or not bank_account:
            self.logger.debug(f"Missing accounts for purchase: {expense_account_path}")
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
            self._create_split(expense_account, net_amount, txn, "Business expense")
            
            # VAT input split
            if vat_input_account and vat_amount > 0:
                self._create_split(vat_input_account, vat_amount, txn, f"VAT {vat_rate}%")
            
            # Handle EU reverse VAT - need to balance input and output VAT
            if "EU Reverse VAT" in expense_account_path:
                vat_output_eu = self.accounts.get("VAT:Output:EU")
                if vat_output_eu and vat_amount > 0:
                    self._create_split(vat_output_eu, -vat_amount, txn, "EU reverse VAT output")
                    # For EU reverse VAT, we don't charge the supplier VAT, so adjust the gross amount
                    gross_amount = net_amount
            
            # Bank payment (credit)
            self._create_split(bank_account, -gross_amount, txn, "Payment made")
            
            return txn
            
        except Exception as e:
            self.logger.error(f"Failed to create purchase transaction: {e}")
            return None
    
    def generate_test_data(self, output_file: str) -> bool:
        """Generate comprehensive test data"""
        self.logger.info(f"Generating test data from {self.config.start_year} to {self.config.end_year}")
        self.logger.info(f"Base monthly revenue: £{self.config.monthly_revenue_base:,}")
        self.logger.info(f"Annual growth rate: {self.config.annual_growth_rate}%")
        
        # Validate input file
        if not self._validate_input_file():
            return False
        
        try:
            # Copy input file to output location
            shutil.copy2(self.input_file, output_file)
            self.logger.info(f"Copied account structure to: {output_file}")
            
            # Open for modification
            book = piecash.open_book(output_file, readonly=False)
            self._load_accounts(book)
            
            # Generate transaction dates
            transaction_dates = self._generate_date_range()
            self.logger.info(f"Generating {len(transaction_dates)} transactions")
            
            transactions_created = 0
            transactions_failed = 0
            
            for i, transaction_date in enumerate(transaction_dates):
                if i % 100 == 0 and i > 0:
                    self.logger.info(f"Progress: {i}/{len(transaction_dates)} transactions processed")
                
                # Generate different types of transactions
                transaction_type = random.random()
                
                if transaction_type < 0.5:  # 50% sales
                    txn = self._generate_sales_transaction(transaction_date, book)
                elif transaction_type < 0.85:  # 35% purchases
                    txn = self._generate_purchase_transaction(transaction_date, book)
                else:  # 15% other transactions (skip for now)
                    continue
                
                if txn:
                    transactions_created += 1
                else:
                    transactions_failed += 1
            
            # Save and close
            book.save()
            book.close()
            
            self.logger.info(f"Successfully created {transactions_created} transactions")
            if transactions_failed > 0:
                self.logger.warning(f"Failed to create {transactions_failed} transactions")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to generate test data: {e}")
            return False

def create_config_from_args(args) -> BusinessConfig:
    """Create BusinessConfig from command line arguments"""
    config = BusinessConfig()
    
    # Date range
    config.start_year = args.start_year
    config.end_year = args.end_year
    
    # Business parameters
    config.monthly_revenue_base = args.revenue
    config.annual_growth_rate = args.growth
    config.international_percentage = args.international
    
    # Staff
    config.initial_staff = args.initial_staff
    config.final_staff = args.final_staff
    
    # Transaction generation
    config.transactions_per_month_base = args.transactions_per_month
    config.seasonal_variation = not args.no_seasonal
    config.include_payroll = args.include_payroll
    config.include_assets = args.include_assets
    
    # Reproducibility
    if args.seed is not None:
        config.random_seed = args.seed
    
    return config

def save_config(config: BusinessConfig, config_file: str):
    """Save configuration to JSON file"""
    config_dict = {
        'start_year': config.start_year,
        'end_year': config.end_year,
        'monthly_revenue_base': config.monthly_revenue_base,
        'annual_growth_rate': config.annual_growth_rate,
        'international_percentage': config.international_percentage,
        'initial_staff': config.initial_staff,
        'final_staff': config.final_staff,
        'transactions_per_month_base': config.transactions_per_month_base,
        'seasonal_variation': config.seasonal_variation,
        'include_payroll': config.include_payroll,
        'include_assets': config.include_assets,
        'random_seed': config.random_seed
    }
    
    with open(config_file, 'w') as f:
        json.dump(config_dict, f, indent=2)

def main():
    """Main command-line interface"""
    parser = argparse.ArgumentParser(
        description='Generate realistic UK business test data for GnuCash',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic usage
  %(prog)s --input accounts/accounts2.gnucash --output test_data.gnucash

  # Custom date range and revenue
  %(prog)s --input accounts.gnucash --output business_2020-2022.gnucash \\
           --start-year 2020 --end-year 2022 --revenue 50000 --growth 25

  # High-volume testing
  %(prog)s --input accounts.gnucash --output high_volume.gnucash \\
           --transactions-per-month 100 --no-seasonal --seed 12345

  # Save configuration for reuse
  %(prog)s --input accounts.gnucash --output test.gnucash \\
           --save-config my_config.json
        '''
    )
    
    # Required arguments
    parser.add_argument('--input', '-i', required=True,
                       help='Input GnuCash file with account structure')
    parser.add_argument('--output', '-o', required=True,
                       help='Output GnuCash file for generated test data')
    
    # Date range
    parser.add_argument('--start-year', type=int, default=2021,
                       help='Start year for test data (default: 2021)')
    parser.add_argument('--end-year', type=int, default=2023,
                       help='End year for test data (default: 2023)')
    
    # Business parameters
    parser.add_argument('--revenue', type=int, default=25000,
                       help='Monthly revenue base in £ (default: 25000)')
    parser.add_argument('--growth', type=float, default=20.0,
                       help='Annual growth rate percentage (default: 20.0)')
    parser.add_argument('--international', type=float, default=40.0,
                       help='Percentage of international sales (default: 40.0)')
    
    # Staff parameters
    parser.add_argument('--initial-staff', type=int, default=2,
                       help='Initial number of staff (default: 2)')
    parser.add_argument('--final-staff', type=int, default=8,
                       help='Final number of staff (default: 8)')
    
    # Transaction generation
    parser.add_argument('--transactions-per-month', type=int, default=25,
                       help='Base transactions per month (default: 25)')
    parser.add_argument('--no-seasonal', action='store_true',
                       help='Disable seasonal transaction variations')
    parser.add_argument('--include-payroll', action='store_true', default=True,
                       help='Include payroll transactions')
    parser.add_argument('--include-assets', action='store_true', default=True,
                       help='Include asset purchase transactions')
    
    # Control options
    parser.add_argument('--seed', type=int,
                       help='Random seed for reproducible results')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--save-config',
                       help='Save configuration to JSON file')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be generated without creating files')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Validate arguments
    if args.start_year > args.end_year:
        logger.error("Start year must not be after end year")
        sys.exit(1)
    
    if args.revenue <= 0:
        logger.error("Revenue must be positive")
        sys.exit(1)
    
    # Check if output file would be overwritten
    if os.path.exists(args.output) and not args.dry_run:
        response = input(f"Output file {args.output} exists. Overwrite? (y/N): ")
        if response.lower() not in ['y', 'yes']:
            logger.info("Operation cancelled")
            sys.exit(0)
    
    # Create configuration
    config = create_config_from_args(args)
    
    # Save configuration if requested
    if args.save_config:
        save_config(config, args.save_config)
        logger.info(f"Configuration saved to: {args.save_config}")
    
    # Show configuration
    years = args.end_year - args.start_year + 1
    total_months = years * 12
    estimated_transactions = total_months * args.transactions_per_month
    
    logger.info("Configuration Summary:")
    logger.info(f"  Input file: {args.input}")
    logger.info(f"  Output file: {args.output}")
    logger.info(f"  Date range: {args.start_year} to {args.end_year} ({years} years)")
    logger.info(f"  Monthly revenue: £{args.revenue:,} (growing {args.growth}% annually)")
    logger.info(f"  International sales: {args.international}%")
    logger.info(f"  Staff growth: {args.initial_staff} to {args.final_staff}")
    logger.info(f"  Estimated transactions: ~{estimated_transactions:,}")
    if args.seed:
        logger.info(f"  Random seed: {args.seed}")
    
    if args.dry_run:
        logger.info("Dry run - no files will be created")
        sys.exit(0)
    
    # Generate test data
    generator = GnuCashTestGenerator(args.input, config)
    success = generator.generate_test_data(args.output)
    
    if success:
        logger.info(f"Test data generation completed successfully")
        logger.info(f"Output file: {args.output}")
        
        # Show file size
        if os.path.exists(args.output):
            size_mb = os.path.getsize(args.output) / (1024 * 1024)
            logger.info(f"File size: {size_mb:.1f} MB")
        
        sys.exit(0)
    else:
        logger.error("Test data generation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()