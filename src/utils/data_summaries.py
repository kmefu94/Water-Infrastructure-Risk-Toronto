import pandas as pd

#.Quick summary, or full summary, loads the dataframe and pulls the dtypes, % missing data, and # unique values
def quick_summary(df):
    summary = pd.DataFrame({
        "dtype": df.dtypes,
        "col_index": range(len(df.columns)),
        "missing_pct": df.isnull().mean(),
        "n_unique": df.nunique()
    })
    return summary[["dtype", "col_index", "missing_pct", "n_unique"]]

def full_summary(data):
    for name, df in data.items():
        print(f"\nSummary for: {name}")
        print(quick_summary(df))
    return


def compare_columns(data):
    """
    Return a boolean table showing which columns appear in which DataFrames.

    Parameters:
        data (dict[str, pd.DataFrame])

    Returns:
        pd.DataFrame: rows = all columns, columns = table names, values = bool
    """
    all_cols = sorted(set().union(*[df.columns for df in data.values()]))
    table = pd.DataFrame(index=all_cols)
    for name, df in data.items():
        table[name] = table.index.isin(df.columns)
    return table


def column_presence(data):
    """
    Return each column's presence score and the source tables it appears in.

    Parameters:
        data (dict[str, pd.DataFrame])

    Returns:
        pd.DataFrame: columns = [column, presence_score, present_in_tables]
    """
    all_cols = sorted(set().union(*[set(df.columns) for df in data.values()]))
    n_tables = len(data)
    rows = []
    for col in all_cols:
        present_in = [name for name, df in data.items() if col in df.columns]
        rows.append({
            "column": col,
            "presence_score": len(present_in) / n_tables,
            "present_in_tables": present_in
        })
    return pd.DataFrame(rows).sort_values(
        ["presence_score", "column"],
        ascending=[False, True]
    ).reset_index(drop=True)


def search_df(df, term=None, col_index=None, col_name=None):
    """
    Search a column by index or name and return matching rows.
    If neither col_index nor col_name is provided, return full dataframe.

    Parameters:
        df (pd.DataFrame)
        term (str): search term or regex pattern
        col_index (int, optional): column position to search
        col_name (str, optional): column name to search; takes precedence over col_index

    Returns:
        pd.DataFrame
    """
    if col_name is not None:
        col = df[col_name].astype(str)
    elif col_index is not None:
        col = df.iloc[:, col_index].astype(str)
    else:
        return df
    mask = col.str.contains(term, case=False, na=False, regex=True)
    return df[mask]


def check_duplicates(df=None, col_name=None):
    """
    Return duplicated rows from a DataFrame.

    Parameters:
        df (pd.DataFrame): input DataFrame
        col_name (str or list[str], optional): column(s) to check for duplicates; checks all columns if None

    Returns:
        pd.DataFrame: rows that are duplicated
    """
    if df is None:
        return pd.DataFrame()

    if col_name is not None:
        subset = [col_name] if isinstance(col_name, str) else list(col_name)
    else:
        subset = None

    return df[df.duplicated(subset=subset, keep=False)]