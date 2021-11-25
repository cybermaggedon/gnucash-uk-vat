
# Installing `gnucash-uk-vat`

```
pip3 install git+https://github.com/cybermaggedon/gnucash-uk-vat
```

This installs dependencies.  If you want to use the fully automated
`--assist` mode, you need` to install `pygtk2` also, which is not included in
the dependency list.

There is a dependency on either the `gnucash` Python module, or the
`piecash` module.  `gnucash` can only be used on Linux and cannot be
installed from PyPI.  ` See
<https://wiki.gnucash.org/wiki/Python_Bindings> for installation.  On
Linux (Debian, Ubuntu, Fedora), the `gnucash` Python modules are
available on package repositories.  `piecash` is pure Python and will
run anywhere, but only knows how to access Sqlite or Postgres
databases.

There are instructions for MacOS installation which I have not tested on the
wiki page.

