#!/usr/bin/env python3

"""
CLI interface for gnucash-uk-vat
"""

import os
import sys
import argparse
import json
import asyncio
import types
from typing import Optional, List

import datetime

from .config import Config, initialise_config
from .auth import Auth
from .operations import authenticate, show_open_obligations, show_obligations, submit_vat_return, post_vat_bill, show_account_data, show_vat_return, show_liabilities, show_payments

from . import hmrc
from . import accounts

def now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)
    
default_start = str(now().date() - datetime.timedelta(days=356))
default_end = str(now().date())

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for gnucash-uk-vat CLI."""
    # Command-line argument parser
    parser = argparse.ArgumentParser(description="Gnucash to HMRC VAT API")
    parser.add_argument('--json', '-j',
                action='store_true',
                        help='Print output as json for automated testing (default: False)')
    parser.add_argument('--userfile', '-u',
                default='user.json',
                        help='MTD test user file returned by ./get-test-user (default: user.json)')
    parser.add_argument('--config', '-c',
                default='config.json',
                        help='Configuration file (default: config.json)')
    parser.add_argument('--auth', '-a',
                default='auth.json',
                        help='File to store auth credentials (default: auth.json)')
    parser.add_argument('--init-config', action='store_true',
                        help='Initialise configuration file with template')
    parser.add_argument('--authenticate', action='store_true',
                        help='Perform authentication process')
    parser.add_argument('--show-open-obligations', action='store_true',
                        help='Show VAT obligations')
    parser.add_argument('--show-obligations', action='store_true',
                        help='Show all VAT obligations in start/end period')
    parser.add_argument('--start',
                        default=default_start,
                        help='Start of working range (default: %s)' % default_start
                        )
    parser.add_argument('--end',
                        default=default_end,
                        help='End of working range (default: %s)' % default_end
                        )
    parser.add_argument('--due-date',
                        help='Show VAT due on specified due date (YYYY-MM-DD)')
    parser.add_argument('--show-vat-return', action='store_true',
                        help='Show VAT return for the specified due date')
    parser.add_argument('--show-liabilities', action='store_true',
                        help='Show VAT liabilities in start/end period')
    parser.add_argument('--show-payments', action='store_true',
                        help='Show VAT payments in start/end period')
    parser.add_argument('--show-account-data', action='store_true',
                        help='Show account data used in VAT return submission')
    parser.add_argument('--submit-vat-return', action='store_true',
                        help='Submit VAT return for the specified due date')
    parser.add_argument('--post-vat-bill', action='store_true',
                        help='Post VAT bill entry to accounting ledger')
    parser.add_argument('--version', action='store_true',
                        help='Show version number')

    return parser

async def run() -> None:
    """Main async entry point for gnucash-uk-vat CLI."""
    
    parser = create_parser()
    args = parser.parse_args()

    if args.version:
        from .version import version
        print(f"gnucash-uk-vat {version}")
        sys.exit(0)

    # Load user from file
    user: Optional[Config] = None
    if os.path.exists(args.userfile):
        user = Config(args.userfile)
    else:
        user = None

    # Initialise configuration operation.  This goes here as configuration
    # can be initialised if no auth has been performed
    if args.init_config:
        # NOTE: user may be none 
        initialise_config(args.config, user)
        sys.exit(0)

    # Create configuration object
    config = Config(args.config)

    # Create auth object
    auth = Auth(args.auth)

    # Perform authentication
    if args.authenticate:
        await authenticate(config, auth, user)
        sys.exit(0)

    # Create VAT service wrapper
    vat = hmrc.create(config, auth, user)

    # Parse date arguments
    start_date = datetime.datetime.fromisoformat(args.start).date()
    end_date = datetime.datetime.fromisoformat(args.end).date()

    # Show open obligations
    if args.show_open_obligations:
        await show_open_obligations(vat, config, args.json)

    # Show all obligations in date range
    if args.show_obligations:
        await show_obligations(vat, config, start_date, end_date, args.json)

    # Show VAT return
    if args.show_vat_return:
        if not args.due_date:
            print("Error: --due-date required with --show-vat-return", file=sys.stderr)
            sys.exit(1)
        due_date = datetime.datetime.fromisoformat(args.due_date).date()
        await show_vat_return(vat, config, due_date, args.json)

    # Show liabilities
    if args.show_liabilities:
        await show_liabilities(vat, config, start_date, end_date, args.json)

    # Show payments
    if args.show_payments:
        await show_payments(vat, config, start_date, end_date, args.json)

    # Show account data
    if args.show_account_data:
        if not args.due_date:
            print("Error: --due-date required with --show-account-data", file=sys.stderr)
            sys.exit(1)
        due_date = datetime.datetime.fromisoformat(args.due_date).date()
        await show_account_data(vat, config, due_date, args.json)

    # Submit VAT return
    if args.submit_vat_return:
        if not args.due_date:
            print("Error: --due-date required with --submit-vat-return", file=sys.stderr)
            sys.exit(1)
        due_date = datetime.datetime.fromisoformat(args.due_date).date()
        await submit_vat_return(vat, config, due_date, args.json)

    # Post VAT bill
    if args.post_vat_bill:
        if not args.due_date:
            print("Error: --due-date required with --post-vat-bill", file=sys.stderr)
            sys.exit(1)
        due_date = datetime.datetime.fromisoformat(args.due_date).date()
        await post_vat_bill(vat, config, due_date, args.json)

def asyncrun(coro):
    """Run async coroutine with proper event loop handling."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        # If we're already in an event loop, we can't use asyncio.run()
        # This shouldn't happen in CLI usage, but handle it gracefully
        raise RuntimeError("Cannot run CLI from within an existing event loop")
    else:
        return asyncio.run(coro)

def main() -> None:
    """Main CLI entry point."""
    asyncrun(run())

if __name__ == "__main__":
    main()