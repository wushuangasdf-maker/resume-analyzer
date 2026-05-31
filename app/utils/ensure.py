def ensure_str(x):
    if isinstance(x,str):
        return x
    if isinstance(x,list):
        return x[0] if x else ""
    if x is None:
        return ""
    return str(x)