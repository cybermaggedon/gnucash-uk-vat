# GnuCash File Dumper

A comprehensive command-line utility for analyzing and dumping GnuCash file contents. Perfect for inspecting account structures, transactions, and data validation.

## Quick Start

```bash
# Show file summary
python gnucash_dumper.py --file accounts.gnucash --summary

# List all accounts 
python gnucash_dumper.py --file accounts.gnucash --accounts

# Show recent transactions
python gnucash_dumper.py --file accounts.gnucash --transactions --limit 10

# Export data to JSON
python gnucash_dumper.py --file accounts.gnucash --summary --export analysis.json
```

## Features

### File Analysis
- **Summary Statistics**: File size, transaction counts, account analysis
- **Account Structure**: Hierarchical account tree with types and balances
- **Transaction Details**: Full transaction data with splits and balance validation
- **Data Validation**: Identifies unbalanced transactions and data issues

### Filtering & Search
- **Date Range Filtering**: Filter transactions by start/end dates
- **Account Filtering**: Find transactions involving specific accounts
- **Transaction Limits**: Limit output for large datasets
- **Balance Calculation**: Optional account balance calculation

### Export Capabilities
- **JSON Export**: Structured data export for further analysis
- **CSV Export**: Spreadsheet-compatible transaction data
- **Quiet Mode**: Export-only operation for automation

## Command-Line Options

### Required Parameters
- `--file, -f`: GnuCash file to analyze

### Analysis Types
- `--summary, -s`: Show file summary and statistics
- `--accounts, -a`: Dump account structure
- `--transactions, -t`: Dump transaction data

### Account Options
- `--balances, -b`: Include account balances (slower but detailed)

### Transaction Filtering
- `--limit, -l NUMBER`: Limit transactions displayed
- `--start-date YYYY-MM-DD`: Filter transactions from date
- `--end-date YYYY-MM-DD`: Filter transactions to date
- `--account-filter TEXT`: Filter by account name (partial match)

### Export Options
- `--export, -e FILE`: Export data to file
- `--format {json,csv}`: Export format (default: json)
- `--quiet, -q`: Minimal output for automation
- `--verbose, -v`: Detailed logging

## Usage Examples

### Basic Analysis
```bash
# Complete file overview
python gnucash_dumper.py --file accounts.gnucash --summary --accounts --transactions --limit 20

# Account structure with balances
python gnucash_dumper.py --file accounts.gnucash --accounts --balances
```

### Transaction Analysis
```bash
# Recent transactions
python gnucash_dumper.py --file accounts.gnucash --transactions --limit 50

# Transactions for specific period
python gnucash_dumper.py --file accounts.gnucash --transactions \
  --start-date 2023-01-01 --end-date 2023-12-31

# VAT-related transactions
python gnucash_dumper.py --file accounts.gnucash --transactions --account-filter "VAT"

# Bank account activity
python gnucash_dumper.py --file accounts.gnucash --transactions --account-filter "Bank"
```

### Data Export & Automation
```bash
# Export summary to JSON
python gnucash_dumper.py --file accounts.gnucash --summary --export summary.json

# Export transactions to CSV
python gnucash_dumper.py --file accounts.gnucash --transactions \
  --export transactions.csv --format csv

# Automated analysis (no console output)
python gnucash_dumper.py --file accounts.gnucash --summary --accounts \
  --export full_analysis.json --quiet
```

### Data Validation
```bash
# Check for unbalanced transactions
python gnucash_dumper.py --file accounts.gnucash --transactions --verbose

# Comprehensive data audit
python gnucash_dumper.py --file accounts.gnucash --summary --accounts --balances \
  --transactions --export audit_$(date +%Y%m%d).json
```

## Output Examples

### Summary Output
```
GNUCASH FILE SUMMARY
================================================================================
File: accounts/test_data.gnucash
Size: 1.2 MB (1,234,567 bytes)
Modified: 2023-12-01T10:30:00
Currency: GBP

Accounts: 85
  By type:
    ASSET: 25
    LIABILITY: 15
    INCOME: 20
    EXPENSE: 25
  With non-zero balances: 45
  Currencies: GBP

Transactions: 450
  Date range: 2021-01-01 to 2023-12-31
  Most active accounts:
    Bank Accounts:Current Account: 234 transactions
    VAT:Output:Sales: 89 transactions
    Income:Sales:UK: 67 transactions
    Expenses:VAT Purchases:Office: 45 transactions

Commodities: 1
  GBP: Pound Sterling
```

### Transaction Output
```
TRANSACTIONS
================================================================================

1. Services to TechCorp Solutions Ltd (2023-12-28)
   Currency: GBP, Splits: 3, Balance: 0.00
      5000.00 → Bank Accounts:Current Account
              (Payment received)
      1000.00 → VAT:Output:Sales
              (VAT 20%)
     -6000.00 → Income:Sales:UK
              (Sales revenue)

2. Office supplies from UK Office Ltd (2023-12-27)
   Currency: GBP, Splits: 3, Balance: 0.00
       250.00 → Expenses:VAT Purchases:Office
              (Business expense)
        50.00 → VAT:Input
              (VAT 20%)
      -300.00 → Bank Accounts:Current Account
              (Payment made)
```

## Data Export Formats

### JSON Structure
```json
{
  "summary": {
    "file_info": { ... },
    "accounts": { ... },
    "transactions": { ... }
  },
  "accounts": [ ... ],
  "transactions": [ ... ]
}
```

### CSV Columns
- description, post_date, enter_date, currency
- splits_count, balance, is_balanced
- splits (JSON-encoded split details)

## Validation Features

### Transaction Validation
- **Balance Checking**: Identifies transactions that don't balance to zero
- **Date Consistency**: Validates chronological ordering
- **Account References**: Ensures all account references are valid

### Data Quality Indicators
- 🔍 **File Summary**: Quick overview of data quality
- ⚠️ **Balance Issues**: Highlights unbalanced transactions
- 📊 **Usage Statistics**: Most active accounts and time periods

## Performance Notes

- **Small Files** (<1MB): Instant analysis
- **Medium Files** (1-10MB): 1-5 seconds with --balances
- **Large Files** (>10MB): Use --limit and filtering for faster results
- **Balance Calculation**: Add ~2-3 seconds for full balance calculation

## Integration Examples

### Automated Reporting
```bash
#!/bin/bash
# Daily GnuCash file analysis
DATE=$(date +%Y%m%d)
python gnucash_dumper.py --file /path/to/accounts.gnucash \
  --summary --transactions --start-date $(date -d "30 days ago" +%Y-%m-%d) \
  --export "daily_report_${DATE}.json" --quiet

# Email summary if issues found
if grep -q '"balance_issues": [^0]' "daily_report_${DATE}.json"; then
  echo "Unbalanced transactions found!" | mail -s "GnuCash Alert" admin@company.com
fi
```

### Data Pipeline
```python
import subprocess
import json

# Generate analysis
result = subprocess.run([
    'python', 'gnucash_dumper.py', 
    '--file', 'accounts.gnucash',
    '--summary', '--export', 'temp.json', '--quiet'
], capture_output=True)

# Process results
with open('temp.json') as f:
    data = json.load(f)
    
# Extract key metrics
transaction_count = data['summary']['transactions']['total_count']
balance_issues = data['summary']['transactions']['balance_issues']
```

## Error Handling

The dumper includes comprehensive error handling:
- **File Not Found**: Clear error message with file path
- **Corrupted Files**: Graceful handling of database issues
- **Missing Accounts**: Warnings for undefined account references
- **Date Parsing**: Validation of date range parameters

## Dependencies

- `piecash` >= 1.1.0 - GnuCash file access
- Python 3.8+ standard library (json, csv, argparse, logging)

```bash
pip install piecash
```