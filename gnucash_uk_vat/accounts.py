
def get_class(kind):
    if kind == "gnucash":
        from . import accounts_gnucash as a
        return a.Accounts
    elif kind == "piecash":
        from . import accounts_piecash as a  # type: ignore[no-redef]
        return a.Accounts
    else:
        raise RuntimeError("Accounts kind '%s' not known" % kind)

