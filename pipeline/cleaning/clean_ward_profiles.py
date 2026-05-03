import sys
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DATA_PATH = ROOT / "data/raw_data/ward-profiles-25-ward-model"
SOURCE_FILE = DATA_PATH / "2023-wardprofiles-2011-2021-censusdata_rev0719_modified.xlsx"


def load_sheets():
    """Return dict of {sheet_name_lower: DataFrame} with variable column cleaned."""
    xls = pd.ExcelFile(SOURCE_FILE)
    sheets = {}
    for sheet in xls.sheet_names:
        df = pd.read_excel(SOURCE_FILE, sheet_name=sheet, header=1)
        df = df.rename(columns={"Unnamed: 0": "variable"})
        df = df.dropna(subset=["variable"])
        df["variable"] = df["variable"].str.strip()
        sheets[sheet.lower()] = df
    return sheets
