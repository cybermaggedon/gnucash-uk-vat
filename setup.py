
import setuptools
import importlib

with open("README.md", "r") as fh:
    long_description = fh.read()

# Load a version number module?!
spec = importlib.util.spec_from_file_location(
    'version', 'gnucash_uk_vat/version.py'
)
version_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(version_module)

version = version_module.version

setuptools.setup(
    name="gnucash-uk-vat",
    version=version,
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
    download_url = "https://github.com/cybermaggedon/gnucash-uk-vat/archive/refs/tags/v%s.tar.gz" % version,
    install_requires=[
        'aiohttp',
        'py-dmidecode',
        'piecash',
        'netifaces',
        'tabulate',
    ],
    scripts=[
        "scripts/gnucash-uk-vat",
        "scripts/vat-test-service"
    ]
)
