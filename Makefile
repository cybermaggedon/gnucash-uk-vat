
VERSION=1.8.0

all:

set-version:
	echo 'version="'${VERSION}'"' > gnucash_uk_vat/version.py

dist: set-version
	rm -rf dist
	python3 setup.py sdist

test: FORCE
	pytest

FORCE:

