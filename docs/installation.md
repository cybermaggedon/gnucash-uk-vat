
# Installing `gnucash-uk-vat`

```
pip3 install git+https://github.com/cybermaggedon/gnucash-uk-vat
```

This installs dependencies.  If you want to use the fully automated
`--assist` mode, you need` to install `pygtk2` also, which is not included in
the dependency list.

There is a dependency on the `gnucash` Python module, which cannot be installed
from PyPI.  See <https://wiki.gnucash.org/wiki/Python_Bindings> for
installation.  On Linux (Debian, Ubuntu, Fedora), the Python modules are
available on package repositories.

There are instructions for MacOS installation which I have not tested on the
wiki page.

