import re
import pandas as pd

# 44-ward number → 25-ward number (Toronto 2018 ward reorganization)
# Wards 27/28, 33/34, 41-44 span new boundaries — assigned to primary geographic overlap
_WARD_44_TO_25 = {
    1: 1,   2: 1,   # Etobicoke North
    3: 2,   4: 2,   # Etobicoke Centre
    5: 3,   6: 3,   # Etobicoke-Lakeshore
    7: 7,   8: 7,   # York West → Humber River-Black Creek
    9: 6,  10: 6,   # York Centre
    11: 5, 12: 5,   # York South-Weston
    13: 4, 14: 4,   # Parkdale-High Park
    15: 8, 16: 8,   # Eglinton-Lawrence
    17: 9, 18: 9,   # Davenport
    19: 10, 20: 10, # Trinity-Spadina → Spadina-Fort York
    21: 12, 22: 12, # St. Paul's → Toronto-St. Paul's
    23: 18, 24: 18, # Willowdale
    25: 15, 26: 15, # Don Valley West
    27: 11, 28: 13, # Toronto Centre-Rosedale → University-Rosedale / Toronto Centre
    29: 14, 30: 14, # Toronto-Danforth
    31: 19, 32: 19, # Beaches-East York
    33: 16, 34: 17, # Don Valley East → Don Valley East / Don Valley North
    35: 20, 36: 20, # Scarborough Southwest
    37: 21, 38: 21, # Scarborough Centre
    39: 22, 40: 22, # Scarborough-Agincourt
    41: 25, 42: 25, # Scarborough-Rouge River → Scarborough-Rouge Park
    43: 24, 44: 24, # Scarborough East → Scarborough-Guildwood
}

WARD_25_NAMES = {
    1:  "Etobicoke North",
    2:  "Etobicoke Centre",
    3:  "Etobicoke-Lakeshore",
    4:  "Parkdale-High Park",
    5:  "York South-Weston",
    6:  "York Centre",
    7:  "Humber River-Black Creek",
    8:  "Eglinton-Lawrence",
    9:  "Davenport",
    10: "Spadina-Fort York",
    11: "University-Rosedale",
    12: "Toronto-St. Paul's",
    13: "Toronto Centre",
    14: "Toronto-Danforth",
    15: "Don Valley West",
    16: "Don Valley East",
    17: "Don Valley North",
    18: "Willowdale",
    19: "Beaches-East York",
    20: "Scarborough Southwest",
    21: "Scarborough Centre",
    22: "Scarborough-Agincourt",
    23: "Scarborough North",
    24: "Scarborough-Guildwood",
    25: "Scarborough-Rouge Park",
}


# Reverse lookup: normalized name → 25-ward number (handles curly/straight apostrophes)
_WARD_25_NAME_TO_NUM = {
    name.lower().replace('\u2019', "'").replace('\u2018', "'"): num
    for num, name in WARD_25_NAMES.items()
}


def parse_ward_number(ward_str):
    """Extract numeric ward ID from 'Ward Name (NN)' format string."""
    if pd.isna(ward_str):
        return pd.NA
    m = re.search(r'\((\d+)\)', str(ward_str))
    return int(m.group(1)) if m else pd.NA


def to_ward_25_num(ward_str):
    """Return 25-ward number for a ward string.

    Handles both 25-ward entries (2018+ data, already in target system) and
    old 44-ward entries. Name is checked first; if it matches a known 25-ward
    name the number is passed through directly. Otherwise the 44→25 mapping
    is applied.
    """
    if pd.isna(ward_str):
        return pd.NA
    s = str(ward_str).strip()
    m = re.search(r'\((\d+)\)', s)
    if not m:
        return pd.NA
    num = int(m.group(1))
    name = re.sub(r'\s*\(\d+\)\s*$', '', s).strip()
    name_key = name.lower().replace('\u2019', "'").replace('\u2018', "'")
    if name_key in _WARD_25_NAME_TO_NUM:
        return _WARD_25_NAME_TO_NUM[name_key]
    return _WARD_44_TO_25.get(num, pd.NA)


def apply_ward_25(df, ward_col="ward", out_col="ward_25"):
    """Add ward_25 (int) column mapped from a 44-ward string column."""
    df[out_col] = df[ward_col].map(to_ward_25_num).astype("Int64")
    return df
