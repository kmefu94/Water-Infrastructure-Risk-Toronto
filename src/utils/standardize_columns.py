import re
import pandas as pd


def col_to_snake(df):
    def _snake(col):
        col = col.strip()
        col = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", col)
        col = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", col)
        col = re.sub(r"[\s\-]+", "_", col)
        col = re.sub(r"[^\w]", "", col)
        col = re.sub(r"_+", "_", col)
        return col.strip("_").lower()
    df.columns = [_snake(c) for c in df.columns]
    return df


def _resolve(df, columns):
    cols = df.columns.tolist() if columns is None else ([columns] if isinstance(columns, str) else list(columns))
    return [c for c in cols if c in df.columns]


def col_to_int(df=None, columns=None):
    for col in _resolve(df, columns):
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    return df


def col_to_float(df=None, columns=None):
    for col in _resolve(df, columns):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def col_to_str(df=None, columns=None):
    for col in _resolve(df, columns):
        df[col] = df[col].astype(str).str.strip().replace("", pd.NA)
    return df


def col_to_date(df=None, columns=None, **kwargs):
    kwargs.setdefault("format", "mixed")
    for col in _resolve(df, columns):
        df[col] = pd.to_datetime(df[col], errors="coerce", **kwargs).dt.normalize()
    return df


def col_to_bool(df=None, columns=None):
    for col in _resolve(df, columns):
        df[col] = df[col].astype(bool)
    return df


def col_to_cat(df=None, columns=None):
    for col in _resolve(df, columns):
        df[col] = df[col].astype("category")
    return df
