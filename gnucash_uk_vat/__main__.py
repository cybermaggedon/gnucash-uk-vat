#!/usr/bin/env python3

"""
Allow running gnucash_uk_vat as a module: python -m gnucash_uk_vat
"""

from .cli import main

if __name__ == "__main__":
    main()