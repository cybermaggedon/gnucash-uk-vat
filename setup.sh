#!/bin/bash

# HACKY WINDOWS GIT BASH CONSOLE ONLY: Check for Admin privs using the help output from an admin-only windows command
if [[ $(sfc 2>&1 | tr -d '\0') =~ SCANNOW ]]; then 
	if [[ -f $(dirname $(which python))/scripts/gnucash-uk-vat ]]; then
	  echo "Update gnucash-uk-vat"
#	  python -m pip install --upgrade --force-reinstall . 2>&1 | tee setup.log 
	  python -m pip install --upgrade . 2>&1 | tee setup.log 
	else
	  echo "Install gnucash-uk-vat"
	  python -m pip install . 2>&1 | tee setup.log 
	fi
else 
  echo "ERROR: setup.sh must be run in a console with Administrator priviledges"
  exit 1
fi
