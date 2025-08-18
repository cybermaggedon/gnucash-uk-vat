#!/usr/bin/env python3
"""
GnuCash File Dumper

A command-line utility to analyze and dump the contents of GnuCash files.
Useful for inspecting account structures, transactions, and data validation.

Usage:
    python gnucash_dumper.py --help
    python gnucash_dumper.py --file accounts.gnucash --accounts
    python gnucash_dumper.py --file accounts.gnucash --transactions --limit 10
    python gnucash_dumper.py --file accounts.gnucash --summary --export summary.json
"""

import argparse
import sys
import os
import json
import csv
from datetime import datetime, date
from decimal import Decimal
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

import piecash

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)

class GnuCashDumper:
    """GnuCash file analyzer and dumper"""
    
    def __init__(self, gnucash_file: str):
        self.gnucash_file = gnucash_file
        self.book = None
        self.logger = logging.getLogger(__name__)
    
    def open_book(self):
        """Open GnuCash file for reading"""
        if not os.path.exists(self.gnucash_file):
            raise FileNotFoundError(f"File not found: {self.gnucash_file}")
        
        try:
            self.book = piecash.open_book(self.gnucash_file, readonly=True)
            self.logger.info(f"Opened GnuCash file: {self.gnucash_file}")
        except Exception as e:
            raise RuntimeError(f"Cannot open GnuCash file: {e}")
    
    def close_book(self):
        """Close GnuCash file"""
        if self.book:
            self.book.close()
            self.book = None
    
    def get_file_info(self) -> Dict[str, Any]:
        """Get basic file information"""
        if not self.book:
            self.open_book()
        
        file_stat = os.stat(self.gnucash_file)
        
        info = {
            'file_path': self.gnucash_file,
            'file_size_bytes': file_stat.st_size,
            'file_size_mb': round(file_stat.st_size / (1024 * 1024), 2),
            'modified_time': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            'gnucash_version': getattr(self.book, 'version', 'Unknown'),
            'default_currency': None,
            'account_count': len(list(self.book.accounts)),
            'transaction_count': len(list(self.book.transactions)),
            'commodity_count': len(list(self.book.commodities))
        }
        
        # Find default currency
        for commodity in self.book.commodities:
            if commodity.mnemonic in ['GBP', 'USD', 'EUR']:
                info['default_currency'] = commodity.mnemonic
                break
        
        return info
    
    def dump_accounts(self, show_balances: bool = False, output_format: str = 'text') -> List[Dict[str, Any]]:
        """Dump account structure"""
        if not self.book:
            self.open_book()
        
        accounts_data = []
        
        def process_account(account, level=0):
            balance = None
            if show_balances:
                try:
                    balance = float(account.get_balance())
                except:
                    balance = 0.0
            
            # Handle account type safely
            try:
                account_type = account.account_type.name if hasattr(account, 'account_type') and account.account_type else 'Unknown'
            except:
                account_type = 'Unknown'
            
            account_info = {
                'level': level,
                'name': account.name,
                'fullname': account.fullname,
                'account_type': account_type,
                'code': account.code or '',
                'description': account.description or '',
                'currency': account.commodity.mnemonic if account.commodity else 'N/A',
                'balance': balance,
                'parent': account.parent.name if account.parent else None,
                'children_count': len(account.children)
            }
            accounts_data.append(account_info)
            
            # Process children recursively
            for child in sorted(account.children, key=lambda x: x.name):
                process_account(child, level + 1)
        
        # Start with root account children
        for account in sorted(self.book.root_account.children, key=lambda x: x.name):
            process_account(account)
        
        if output_format == 'text':
            self._print_accounts_text(accounts_data)
        
        return accounts_data
    
    def _print_accounts_text(self, accounts_data: List[Dict[str, Any]]):
        """Print accounts in text format"""
        print("\n" + "="*80)
        print("ACCOUNT STRUCTURE")
        print("="*80)
        
        for acc in accounts_data:
            indent = "  " * acc['level']
            type_str = f"({acc['account_type']})" if acc['account_type'] != 'Unknown' else ''
            balance_str = f" - Balance: {acc['currency']} {acc['balance']:.2f}" if acc['balance'] is not None else ''
            code_str = f" [{acc['code']}]" if acc['code'] else ''
            
            print(f"{indent}{acc['name']}{code_str} {type_str}{balance_str}")
            if acc['description']:
                print(f"{indent}  └─ {acc['description']}")
    
    def dump_transactions(self, limit: Optional[int] = None, 
                         start_date: Optional[date] = None,
                         end_date: Optional[date] = None,
                         account_filter: Optional[str] = None,
                         output_format: str = 'text') -> List[Dict[str, Any]]:
        """Dump transaction data"""
        if not self.book:
            self.open_book()
        
        transactions = list(self.book.transactions)
        
        # Apply filters
        if start_date:
            transactions = [t for t in transactions if t.post_date >= start_date]
        if end_date:
            transactions = [t for t in transactions if t.post_date <= end_date]
        if account_filter:
            transactions = [t for t in transactions if any(account_filter.lower() in split.account.fullname.lower() for split in t.splits)]
        
        # Sort by date (most recent first)
        transactions.sort(key=lambda x: x.post_date, reverse=True)
        
        # Apply limit
        if limit:
            transactions = transactions[:limit]
        
        transactions_data = []
        
        for txn in transactions:
            splits_data = []
            for split in txn.splits:
                splits_data.append({
                    'account': split.account.fullname,
                    'account_name': split.account.name,
                    'value': float(split.value),
                    'quantity': float(split.quantity) if split.quantity else float(split.value),
                    'memo': split.memo or ''
                })
            
            txn_balance = sum(s['value'] for s in splits_data)
            
            txn_data = {
                'description': txn.description,
                'post_date': txn.post_date.isoformat(),
                'enter_date': txn.enter_date.isoformat() if txn.enter_date else None,
                'currency': txn.currency.mnemonic if txn.currency else 'N/A',
                'splits_count': len(splits_data),
                'splits': splits_data,
                'balance': txn_balance,  # Should be 0 for valid transactions
                'is_balanced': abs(txn_balance) < 0.01
            }
            transactions_data.append(txn_data)
        
        if output_format == 'text':
            self._print_transactions_text(transactions_data)
        
        return transactions_data
    
    def _print_transactions_text(self, transactions_data: List[Dict[str, Any]]):
        """Print transactions in text format"""
        print("\n" + "="*80)
        print("TRANSACTIONS")
        print("="*80)
        
        for i, txn in enumerate(transactions_data):
            print(f"\n{i+1}. {txn['description']} ({txn['post_date']})")
            print(f"   Currency: {txn['currency']}, Splits: {txn['splits_count']}, Balance: {txn['balance']:.2f}")
            
            if not txn['is_balanced']:
                print(f"   ⚠️  UNBALANCED TRANSACTION!")
            
            for split in txn['splits']:
                value_str = f"{split['value']:>10.2f}"
                print(f"   {value_str} → {split['account']}")
                if split['memo']:
                    print(f"              ({split['memo']})")
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Generate summary statistics"""
        if not self.book:
            self.open_book()
        
        transactions = list(self.book.transactions)
        accounts = list(self.book.accounts)
        
        # Basic counts
        stats = {
            'file_info': self.get_file_info(),
            'accounts': {
                'total_count': len(accounts),
                'by_type': {},
                'with_balances': 0,
                'currencies_used': set()
            },
            'transactions': {
                'total_count': len(transactions),
                'date_range': {},
                'by_month': {},
                'by_account': {},
                'balance_issues': 0
            },
            'commodities': []
        }
        
        # Account analysis
        for account in accounts:
            try:
                acc_type = account.account_type.name if hasattr(account, 'account_type') and account.account_type else 'Unknown'
            except:
                acc_type = 'Unknown'
            stats['accounts']['by_type'][acc_type] = stats['accounts']['by_type'].get(acc_type, 0) + 1
            
            if account.commodity:
                stats['accounts']['currencies_used'].add(account.commodity.mnemonic)
            
            try:
                balance = account.get_balance()
                if balance != 0:
                    stats['accounts']['with_balances'] += 1
            except:
                pass
        
        # Convert set to list for JSON serialization
        stats['accounts']['currencies_used'] = list(stats['accounts']['currencies_used'])
        
        # Transaction analysis
        if transactions:
            dates = [t.post_date for t in transactions]
            stats['transactions']['date_range'] = {
                'earliest': min(dates).isoformat(),
                'latest': max(dates).isoformat()
            }
            
            # Group by month
            for txn in transactions:
                month_key = txn.post_date.strftime('%Y-%m')
                stats['transactions']['by_month'][month_key] = stats['transactions']['by_month'].get(month_key, 0) + 1
                
                # Check transaction balance
                total = sum(float(split.value) for split in txn.splits)
                if abs(total) > 0.01:  # Allow for small rounding errors
                    stats['transactions']['balance_issues'] += 1
                
                # Count by account
                for split in txn.splits:
                    acc_name = split.account.fullname
                    stats['transactions']['by_account'][acc_name] = stats['transactions']['by_account'].get(acc_name, 0) + 1
        
        # Commodity analysis
        for commodity in self.book.commodities:
            stats['commodities'].append({
                'mnemonic': commodity.mnemonic,
                'fullname': commodity.fullname or '',
                'fraction': commodity.fraction,
                'namespace': commodity.namespace
            })
        
        return stats
    
    def print_summary(self, stats: Dict[str, Any]):
        """Print summary statistics"""
        print("\n" + "="*80)
        print("GNUCASH FILE SUMMARY")
        print("="*80)
        
        # File info
        info = stats['file_info']
        print(f"File: {info['file_path']}")
        print(f"Size: {info['file_size_mb']} MB ({info['file_size_bytes']:,} bytes)")
        print(f"Modified: {info['modified_time']}")
        print(f"Currency: {info['default_currency'] or 'Not detected'}")
        
        # Accounts
        print(f"\nAccounts: {stats['accounts']['total_count']}")
        print("  By type:")
        for acc_type, count in sorted(stats['accounts']['by_type'].items()):
            print(f"    {acc_type}: {count}")
        print(f"  With non-zero balances: {stats['accounts']['with_balances']}")
        print(f"  Currencies: {', '.join(stats['accounts']['currencies_used'])}")
        
        # Transactions
        print(f"\nTransactions: {stats['transactions']['total_count']}")
        if stats['transactions']['date_range']:
            print(f"  Date range: {stats['transactions']['date_range']['earliest']} to {stats['transactions']['date_range']['latest']}")
        if stats['transactions']['balance_issues'] > 0:
            print(f"  ⚠️  Unbalanced transactions: {stats['transactions']['balance_issues']}")
        
        # Top accounts by transaction count
        if stats['transactions']['by_account']:
            print("  Most active accounts:")
            sorted_accounts = sorted(stats['transactions']['by_account'].items(), key=lambda x: x[1], reverse=True)
            for acc_name, count in sorted_accounts[:5]:
                print(f"    {acc_name}: {count} transactions")
        
        # Commodities
        print(f"\nCommodities: {len(stats['commodities'])}")
        for commodity in stats['commodities']:
            print(f"  {commodity['mnemonic']}: {commodity['fullname']}")
    
    def export_data(self, data: Any, output_file: str, format_type: str = 'json'):
        """Export data to file"""
        output_path = Path(output_file)
        
        try:
            if format_type.lower() == 'json':
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                self.logger.info(f"Data exported to JSON: {output_file}")
            
            elif format_type.lower() == 'csv' and isinstance(data, list):
                if not data:
                    self.logger.warning("No data to export")
                    return
                
                # Flatten nested structures for CSV
                flattened_data = []
                for item in data:
                    if isinstance(item, dict):
                        flat_item = {}
                        for key, value in item.items():
                            if isinstance(value, (list, dict)):
                                flat_item[key] = json.dumps(value)
                            else:
                                flat_item[key] = value
                        flattened_data.append(flat_item)
                    else:
                        flattened_data.append(item)
                
                if flattened_data:
                    with open(output_path, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=flattened_data[0].keys())
                        writer.writeheader()
                        writer.writerows(flattened_data)
                    self.logger.info(f"Data exported to CSV: {output_file}")
            
            else:
                raise ValueError(f"Unsupported export format: {format_type}")
                
        except Exception as e:
            self.logger.error(f"Failed to export data: {e}")
            raise

def parse_date(date_str: str) -> date:
    """Parse date string in YYYY-MM-DD format"""
    return datetime.strptime(date_str, '%Y-%m-%d').date()

def main():
    """Main command-line interface"""
    parser = argparse.ArgumentParser(
        description='Analyze and dump GnuCash file contents',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Show file summary
  %(prog)s --file accounts.gnucash --summary

  # List all accounts with balances
  %(prog)s --file accounts.gnucash --accounts --balances

  # Show recent transactions
  %(prog)s --file accounts.gnucash --transactions --limit 20

  # Filter transactions by date range
  %(prog)s --file accounts.gnucash --transactions --start-date 2023-01-01 --end-date 2023-12-31

  # Export account structure to JSON
  %(prog)s --file accounts.gnucash --accounts --export accounts.json

  # Find transactions involving VAT accounts
  %(prog)s --file accounts.gnucash --transactions --account-filter "VAT"

  # Full analysis with export
  %(prog)s --file accounts.gnucash --summary --accounts --transactions --limit 50 --export full_dump.json
        '''
    )
    
    # Required arguments
    parser.add_argument('--file', '-f', required=True,
                       help='GnuCash file to analyze')
    
    # Analysis options
    parser.add_argument('--summary', '-s', action='store_true',
                       help='Show file summary and statistics')
    parser.add_argument('--accounts', '-a', action='store_true',
                       help='Dump account structure')
    parser.add_argument('--transactions', '-t', action='store_true',
                       help='Dump transaction data')
    
    # Account options
    parser.add_argument('--balances', '-b', action='store_true',
                       help='Include account balances (slower)')
    
    # Transaction options
    parser.add_argument('--limit', '-l', type=int,
                       help='Limit number of transactions to show')
    parser.add_argument('--start-date', type=str,
                       help='Start date for transactions (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str,
                       help='End date for transactions (YYYY-MM-DD)')
    parser.add_argument('--account-filter', type=str,
                       help='Filter transactions by account name (partial match)')
    
    # Export options
    parser.add_argument('--export', '-e', type=str,
                       help='Export data to file (JSON or CSV)')
    parser.add_argument('--format', choices=['json', 'csv'], default='json',
                       help='Export format (default: json)')
    
    # Control options
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Minimal output (export only)')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose and not args.quiet)
    
    # Validate arguments
    if not any([args.summary, args.accounts, args.transactions]):
        parser.error("Must specify at least one of: --summary, --accounts, --transactions")
    
    # Parse dates if provided
    start_date = None
    end_date = None
    if args.start_date:
        try:
            start_date = parse_date(args.start_date)
        except ValueError:
            parser.error(f"Invalid start date format: {args.start_date} (use YYYY-MM-DD)")
    
    if args.end_date:
        try:
            end_date = parse_date(args.end_date)
        except ValueError:
            parser.error(f"Invalid end date format: {args.end_date} (use YYYY-MM-DD)")
    
    if start_date and end_date and start_date > end_date:
        parser.error("Start date must be before or equal to end date")
    
    # Initialize dumper
    try:
        dumper = GnuCashDumper(args.file)
        dumper.open_book()
        
        export_data = {}
        
        # Generate summary
        if args.summary:
            stats = dumper.get_summary_stats()
            if not args.quiet:
                dumper.print_summary(stats)
            export_data['summary'] = stats
        
        # Dump accounts
        if args.accounts:
            accounts_data = dumper.dump_accounts(
                show_balances=args.balances,
                output_format='text' if not args.quiet else 'data'
            )
            export_data['accounts'] = accounts_data
        
        # Dump transactions
        if args.transactions:
            transactions_data = dumper.dump_transactions(
                limit=args.limit,
                start_date=start_date,
                end_date=end_date,
                account_filter=args.account_filter,
                output_format='text' if not args.quiet else 'data'
            )
            export_data['transactions'] = transactions_data
        
        # Export data if requested
        if args.export:
            # If only one type of data, export that directly
            if len(export_data) == 1:
                data_to_export = list(export_data.values())[0]
            else:
                data_to_export = export_data
            
            dumper.export_data(data_to_export, args.export, args.format)
        
        dumper.close_book()
        
        if not args.quiet:
            logger.info("Analysis completed successfully")
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()