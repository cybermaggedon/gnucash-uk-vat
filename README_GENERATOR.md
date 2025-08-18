# GnuCash UK Business Test Data Generator

A comprehensive command-line utility for generating realistic UK business transaction data for testing VAT reporting, accounting scenarios, and multi-year business operations.

## Quick Start

```bash
# Basic usage - generate 3 years of data (2021-2023)
python gnucash_test_generator.py --input accounts/accounts2.gnucash --output test_business.gnucash

# Custom business scenario
python gnucash_test_generator.py \
  --input accounts/accounts2.gnucash \
  --output startup_2021-2024.gnucash \
  --start-year 2021 --end-year 2024 \
  --revenue 15000 --growth 35 \
  --international 50 \
  --transactions-per-month 15

# High-volume testing with reproducible results
python gnucash_test_generator.py \
  --input accounts/accounts2.gnucash \
  --output volume_test.gnucash \
  --transactions-per-month 50 \
  --seed 12345 --no-seasonal
```

## Features

### Realistic UK Business Transactions
- **Sales**: UK (20% VAT), EU (reverse charge), International (zero-rated exports)
- **Purchases**: Office expenses, professional services, software, travel, telecoms
- **EU Reverse VAT**: Proper input/output VAT handling for EU suppliers
- **Seasonal Variations**: Q4 busy periods, August quieter periods
- **Growth Modeling**: Configurable annual growth with realistic patterns

### UK VAT Compliance
- Standard rate VAT (20%) on domestic sales/purchases
- Zero-rated exports to international customers
- EU reverse charge mechanism for B2B services
- Proper VAT account allocations (Input/Output/Sales/EU)

### Business Scenarios
- Multi-year growth trajectories (startup to established)
- Staff expansion modeling (2-8+ employees)
- Seasonal business patterns
- International trading (configurable percentage)
- Asset purchases and depreciation

## Command-Line Options

### Required Parameters
- `--input, -i`: Input GnuCash file with account structure
- `--output, -o`: Output file for generated test data

### Business Configuration
- `--start-year`: Start year (default: 2021)
- `--end-year`: End year (default: 2023)
- `--revenue`: Monthly revenue base in £ (default: 25,000)
- `--growth`: Annual growth rate % (default: 20%)
- `--international`: International sales % (default: 40%)

### Transaction Generation
- `--transactions-per-month`: Base transactions per month (default: 25)
- `--no-seasonal`: Disable seasonal variations
- `--seed`: Random seed for reproducible results

### Staff & Operations
- `--initial-staff`: Starting staff count (default: 2)
- `--final-staff`: Final staff count (default: 8)
- `--include-payroll`: Include payroll transactions
- `--include-assets`: Include asset purchases

### Utility Options
- `--verbose, -v`: Detailed logging
- `--dry-run`: Preview configuration without generating files
- `--save-config FILE`: Save configuration to JSON file

## Example Scenarios

### Software Consultancy (Default)
```bash
python gnucash_test_generator.py \
  --input accounts/accounts2.gnucash \
  --output consultancy_2021-2023.gnucash
```
- £25K/month starting revenue, 20% annual growth
- 40% international sales (zero-rated VAT)
- Seasonal Q4 growth pattern
- Staff growth from 2 to 8 people

### Tech Startup
```bash
python gnucash_test_generator.py \
  --input accounts/accounts2.gnucash \
  --output tech_startup.gnucash \
  --start-year 2020 --end-year 2024 \
  --revenue 8000 --growth 45 \
  --international 60 \
  --initial-staff 1 --final-staff 12
```
- £8K/month starting revenue, aggressive 45% growth
- 60% international customer base
- Rapid staff expansion (1 to 12 people)

### Established Business
```bash
python gnucash_test_generator.py \
  --input accounts/accounts2.gnucash \
  --output established_business.gnucash \
  --revenue 75000 --growth 8 \
  --international 25 \
  --transactions-per-month 40
```
- £75K/month mature revenue, steady 8% growth
- 25% international sales
- Higher transaction volume (40/month)

### Compliance Testing
```bash
python gnucash_test_generator.py \
  --input accounts/accounts2.gnucash \
  --output vat_compliance_test.gnucash \
  --transactions-per-month 100 \
  --seed 54321 --no-seasonal
```
- High transaction volume for stress testing
- Reproducible results with fixed seed
- No seasonal variation for consistent testing

## Generated Transaction Types

### Sales Transactions (50%)
- **UK B2B Services**: 20% VAT, realistic customer names
- **EU B2B Services**: 0% VAT (reverse charge), EU company names  
- **International Exports**: 0% VAT, global customer names
- Amount ranges: £500-£25,000 depending on customer type

### Purchase Transactions (35%)
- **Office Expenses**: Supplies, utilities, cleaning (20% VAT)
- **Professional Services**: Accountancy, legal, marketing (20% VAT)
- **Software & Telecoms**: Subscriptions, cloud services (20% VAT)
- **Travel & Accommodation**: Business travel (mixed VAT rates)
- **EU Reverse VAT**: Equipment from EU suppliers
- Amount ranges: £50-£3,000 depending on expense type

### Other Transactions (15%)
- Bank transfers and interest
- Asset purchases with depreciation
- Payroll with PAYE/NICs calculations
- Corporation tax payments
- Dividend distributions

## Account Structure Requirements

The input GnuCash file must contain these accounts:
- `Income:Sales:UK` - UK sales revenue
- `Income:Sales:EU:Services` - EU reverse charge sales  
- `Income:Sales:World` - International exports
- `VAT:Input` - Purchase VAT recoverable
- `VAT:Output:Sales` - Sales VAT payable
- `VAT:Output:EU` - EU reverse charge VAT
- `Bank Accounts:Current Account` - Main bank account
- `Expenses:VAT Purchases:*` - Various expense categories

## Output

### Generated Files
- **GnuCash File**: Complete transaction data ready for import
- **Configuration JSON**: Saved parameters for reproducible generation

### Transaction Quality
- Proper double-entry bookkeeping (all transactions balance)
- Realistic company/supplier names
- Accurate VAT calculations (rounded to pence)
- Chronological date ordering
- Seasonal business patterns
- Growth trajectories over time

## Performance

- **Small Dataset** (1 year, 5 trans/month): ~60 transactions, <1 second
- **Medium Dataset** (3 years, 25 trans/month): ~900 transactions, ~2 seconds  
- **Large Dataset** (5 years, 50 trans/month): ~3000 transactions, ~10 seconds
- **Generated File Size**: ~300KB per 1000 transactions

## Validation

Verify generated data:
```bash
# Check transaction count
python -c "
import piecash
book = piecash.open_book('test_output.gnucash', readonly=True)
print(f'Total transactions: {len(book.transactions)}')
book.close()
"

# Validate VAT calculations
python -c "
import piecash
book = piecash.open_book('test_output.gnucash', readonly=True)
for txn in book.transactions[-5:]:
    total = sum(split.value for split in txn.splits)
    print(f'{txn.description}: Balance = £{total} (should be 0)')
book.close()
"
```

## Dependencies

- `piecash` >= 1.1.0 - GnuCash file manipulation
- `python-dateutil` - Date handling
- Python 3.8+ standard library

Install dependencies:
```bash
pip install piecash python-dateutil
```