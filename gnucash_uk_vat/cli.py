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
from pathlib import Path
from typing import Optional

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
                default='user.json', type=Path,
                        help='MTD test user file returned by ./get-test-user (default: user.json)')
    parser.add_argument('--config', '-c',
                default='config.json', type=Path,
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
                        help='End of working range (default: %s)' % default_end)
    parser.add_argument('--show-account-detail', action='store_true',
                        help='Show account detail for VAT obligations')
    parser.add_argument('--show-account-summary', action='store_true',
                        help='Show account summary for VAT obligations')
    parser.add_argument('--show-vat-return', action='store_true',
                        help='Show VAT return for start/end period')
    parser.add_argument('--due-date', default=None,
                        help='Define obligation by specifying due date')
    parser.add_argument('--submit-vat-return', action='store_true',
                        help='Submit VAT return for obligation due date')
    #parser.add_argument('--post-vat-bill', action='store_true',
    #                    help='Post a VAT bill to accounts for due date')
    parser.add_argument('--show-liabilities', action='store_true',
                        help='Show VAT liabilities')
    parser.add_argument('--show-payments', action='store_true',
                        help='Show VAT payments')
    parser.add_argument('--assist', action='store_true',
                        help='Launch assistant')

    return parser

async def run() -> None:
    """Main async entry point for gnucash-uk-vat CLI."""
    
    parser = create_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.assist:
        # Doing the import here so that command-line stuff still works if
        # GTK is not installed.
        import gnucash_uk_vat.assist as assist
        assist.run(args.config, args.auth)
        sys.exit(0)

    if args.userfile.exists():
        user = Config(args.userfile)
    else:
        user = None

    # Initialise configuration operation.  This goes here as configuration
    # can be initialised if no auth has been performed
    if args.init_config:
        # NOTE: user may be none 
        initialise_config(args.config, user)
        sys.exit(0)

    # Initialise config and auth.  
    config = Config(args.config)
    auth = Auth(args.auth)

    print_json = args.json
    h = hmrc.create(config, auth, user)

    # Authenticate HMRC [test]user with MTD API.
    if args.authenticate:
        await authenticate(h, auth)
        sys.exit(0)

    # All following operations require a valid token, so refresh token if
    # expired.
    await auth.maybe_refresh(h)

    # Call appropriate function to implement operations
    if args.show_open_obligations:
        await show_open_obligations(h, config, print_json)
        sys.exit(0)
    elif args.show_obligations:
        start = datetime.datetime.fromisoformat(args.start).date()
        end = datetime.datetime.fromisoformat(args.end).date()
        await show_obligations(start, end, h, config, print_json)
        sys.exit(0)
    elif args.submit_vat_return:
        if args.due_date == None:
            raise RuntimeError("--due-date must be specified")
        due = datetime.datetime.fromisoformat(args.due_date).date()
        await submit_vat_return(due, h, config)
        sys.exit(0)
#    elif args.post_vat_bill:
#        start = datetime.datetime.fromisoformat(args.start).date()
#        end = datetime.datetime.fromisoformat(args.end).date()
#        if args.due_date == None:
#            raise RuntimeError("--due-date must be specified")
#        due = datetime.datetime.fromisoformat(args.due_date).date()
#        post_vat_bill(start, end, due, h, config)
#        sys.exit(0)
    elif args.show_account_detail:
        if args.due_date == None:
            raise RuntimeError("--due-date must be specified")
        due = datetime.datetime.fromisoformat(args.due_date).date()
        await show_account_data(h, config, due, detail=True)
        sys.exit(0)
    elif args.show_account_summary:
        if args.due_date == None:
            raise RuntimeError("--due-date must be specified")
        due = datetime.datetime.fromisoformat(args.due_date).date()
        await show_account_data(h, config, due)
        sys.exit(0)
    elif args.show_vat_return:
        start = datetime.datetime.fromisoformat(args.start).date()
        end = datetime.datetime.fromisoformat(args.end).date()
        if args.due_date == None:
            raise RuntimeError("--due-date must be specified")
        due = datetime.datetime.fromisoformat(args.due_date).date()
        await show_vat_return(start, end, due, h, config)
        sys.exit(0)
    elif args.show_liabilities:
        start = datetime.datetime.fromisoformat(args.start).date()
        end = datetime.datetime.fromisoformat(args.end).date()
        await show_liabilities(start, end, h, config)
        sys.exit(0)
    elif args.show_payments:
        start = datetime.datetime.fromisoformat(args.start).date()
        end = datetime.datetime.fromisoformat(args.end).date()
        await show_payments(start, end, h, config)
        sys.exit(0)
    else:
        raise RuntimeError("No operation specified.  Try --assist option.")

def asyncrun(coro):
    """Run async coroutine with proper event loop handling."""
    if sys.platform == "win32":
        # Prevent "RuntimeError: Event loop is closed" on Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # asyncio.run introduced in Python 3.7, just use that.
    if sys.version_info >= (3, 7):
        return asyncio.run(coro)

    # Emulate asyncio.run()

    # asyncio.run() requires a coro, so require it here as well
    if not isinstance(coro, types.CoroutineType):
        raise TypeError("run() requires a coroutine object")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)

def main() -> None:
    """Main CLI entry point."""
    try:
        asyncrun(run())
    except Exception as e:
        sys.stderr.write("Exception: %s\n" % e)
        sys.exit(1)

if __name__ == "__main__":
    main()
