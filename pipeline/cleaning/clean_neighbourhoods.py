import sys
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.standardize_columns import col_to_snake
INPUT_PATH = ROOT / "data/raw_data/neighbourhoods/neighbourhoods-4326.csv"
OUTPUT_PATH = ROOT / "data/cleaned_data/neighbourhoods"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

STRING_COLS = ["area_name", "area_desc", "classification", "classification_code"]
INT_COLS = ["_id", "area_id", "area_attr_id", "parent_area_id", "area_short_code",
            "area_long_code", "objectid"]


def clean(df):
    changes = {}

    df = col_to_snake(df)

    # Drop geometry — spatial data, used only in transformations
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])
        changes["geometry"] = "dropped (spatial column, used only in transformations)"

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    changes["duplicates_removed"] = before - len(df)

    # Cast integer ID columns
    cast_int = []
    for col in INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
            cast_int.append(col)
    changes["cast_to_int"] = cast_int

    # Strip whitespace and replace empty strings with NaN on string columns
    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].str.strip().replace("", pd.NA)

    changes["rows_raw"] = before
    changes["rows_clean"] = len(df)
    changes["missing_per_col"] = {
        col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0
    }

    return df, changes


def write_report(changes, out_path):
    lines = ["NEIGHBOURHOODS — CLEANING REPORT", "=" * 50, ""]
    lines.append(f"Rows: {changes['rows_raw']:,} raw -> {changes['rows_clean']:,} clean")
    lines.append(f"Duplicates removed: {changes['duplicates_removed']:,}")
    lines.append(f"geometry column: {changes['geometry']}")
    lines.append("")
    lines.append(f"Columns cast to integer: {changes['cast_to_int']}")
    lines.append("")
    if changes["missing_per_col"]:
        lines.append("Missing values (NaN) per column after cleaning:")
        for col, n in changes["missing_per_col"].items():
            lines.append(f"  {col}: {n:,}")
    (out_path / "neighbourhoods_cleaning_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("Loading neighbourhoods-4326.csv...")
    raw = pd.read_csv(INPUT_PATH)
    print(f"  {len(raw):,} rows, {len(raw.columns)} columns")

    print("Cleaning...")
    cleaned, changes = clean(raw)

    cleaned.to_csv(OUTPUT_PATH / "neighbourhoods_clean.csv", index=False)
    write_report(changes, OUTPUT_PATH)

    print(f"  Duplicates removed : {changes['duplicates_removed']:,}")
    print(f"  Columns dropped    : geometry")
    print(f"  Columns cast to int: {len(changes['cast_to_int'])}")
    print(f"Output -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
