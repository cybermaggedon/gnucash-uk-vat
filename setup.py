import setuptools
import re
import git

PRODUCT_BASE_VERSION = "1.5"

with open("README.md", "r") as fh:
    long_description = fh.read()

uncommitted = True
try:
    # Use git commit count as a build number in product-version
    git_repo = git.Repo(search_parent_directories=True)
    uncommitted = git_repo.is_dirty()
    git_commits = list(git_repo.iter_commits('HEAD'))
    # Increment git_count as changing the productVersion in configFilename will require another commit.
    git_count = len(git_commits)
    if uncommitted:
      git_count = git_count + 1
except Exception as git_exception:
    git_count = 9999
    raise Exception("[ERROR] Couldn't calculate the GIT commit count! Is this a git checkout?")

productVersion = "%s.%s" % (PRODUCT_BASE_VERSION, git_count)
configFilename = "gnucash_uk_vat/config.py"

# Inject the product_version into configFilename
fin = open(configFilename, "rt")
data = fin.read()
fin.close()
# Only update if changed
if not re.search("product_version[ ]*=[ ]*\"%s\"" % productVersion, data):
    data = re.sub("product_version[ ]*=[ ]*\"[0-9\.]+\"", "product_version = \"%s\"" % productVersion, data, count=1)
    fout = open(configFilename, "wt")
    fout.write(data)
    fout.close()

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
        'GitPython',
    ],
    scripts=[
        "scripts/gnucash-uk-vat",
        "scripts/vat-test-service"
    ]
)
