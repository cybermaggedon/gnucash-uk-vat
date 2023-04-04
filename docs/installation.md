
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

## Windows 8
Installing on:
* Windows 8 
* Python 3.11
causes a rebuild and VC 14 to throw a linker error when building the aiohttp dependancy:
      _http_parser.obj : error LNK2001: unresolved external symbol _PyUnicode_Ready

Using Python 3.8 seems to resolve the problem.
