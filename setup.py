import setuptools
import re

with open("README.md", "r") as fh:
    long_description = fh.read()

productVersion = "1.5.2"
configFilename = "gnucash_uk_vat/config.py"

# Inject the product_version into configFilename
fin = open(configFilename, "rt")
data = fin.read()
data = re.sub("product_version[ ]*=[ ]*\"[0-9\.]+\"", "product_version = \"%s\"" % productVersion, data, count=1)
fin.close()
fin = open(configFilename, "wt")
fin.write(data)
fin.close()

setuptools.setup(
    name="gnucash-uk-vat",
    version=productVersion,
    author="Cybermaggedon",
    author_email="mark@cyberapocalypse.co.uk",
    description="UK HMRC VAT submission bridge for GnuCash users",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cybermaggedon/gnucash-uk-vat",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    download_url = "https://github.com/cybermaggedon/gnucash-uk-vat/archive/refs/tags/v%s.tar.gz" % productVersion,
    install_requires=[
        'aiohttp',
        'py-dmidecode',
        'requests',
        'piecash',
        'netifaces',
        'tabulate',
    ],
    scripts=[
        "scripts/gnucash-uk-vat",
        "scripts/vat-test-service"
    ]
)
