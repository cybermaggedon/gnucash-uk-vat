import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gnucash-uk-vat",
    version="1.5.1",
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
    download_url = "https://github.com/cybermaggedon/gnucash-uk-vat/archive/refs/tags/v1.5.1.tar.gz",
    install_requires=[
        'aiohttp',
        'py-dmidecode',
        'requests',
        'piecash',
        'tabulate',
    ],
    scripts=[
        "scripts/gnucash-uk-vat",
        "scripts/vat-test-service"
    ]
)
