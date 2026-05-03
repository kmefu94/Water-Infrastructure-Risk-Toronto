import sys
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.standardize_columns import col_to_snake
INPUT_PATH = ROOT / "data/raw_data/current-and-future-climate/climate-variables.csv"
OUTPUT_PATH = ROOT / "data/cleaned_data/climate"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

NON_NUMERIC_COLS = [
    "_id",
    "climate_scenario",
    "time_horizon",
    "distribution",
    "frost_free_season_start_date",
    "frost_free_season_end_date",
]


def clean(df):
    changes = {}

    df = col_to_snake(df)

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    changes["duplicates_removed"] = before - len(df)

    # Replace dash placeholders with NaN
    dash_counts = (df == "-").sum()
    df = df.replace("-", pd.NA)
    changes["dash_replaced_with_nan"] = {
        col: int(dash_counts[col]) for col in df.columns if dash_counts[col] > 0
    }

    # Cast numeric columns
    numeric_cols = [c for c in df.columns if c not in NON_NUMERIC_COLS]
    cast_changes = []
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        cast_changes.append(col)
    changes["cast_to_numeric"] = cast_changes

    # _id as int
    df["_id"] = pd.to_numeric(df["_id"], errors="coerce").astype("Int64")
    changes["_id"] = "cast to integer"

    changes["rows_raw"] = before
    changes["rows_clean"] = len(df)
    changes["missing_per_col"] = {
        col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0
    }

    return df, changes


def write_report(changes, out_path):
    lines = ["CURRENT AND FUTURE CLIMATE — CLEANING REPORT", "=" * 50, ""]
    lines.append(f"Rows: {changes['rows_raw']:,} raw -> {changes['rows_clean']:,} clean")
    lines.append(f"Duplicates removed: {changes['duplicates_removed']:,}")
    lines.append("")
    if changes["dash_replaced_with_nan"]:
        lines.append("Dash placeholders replaced with NaN:")
        for col, n in changes["dash_replaced_with_nan"].items():
            lines.append(f"  {col}: {n:,}")
        lines.append("")
    lines.append(f"Columns cast to numeric ({len(changes['cast_to_numeric'])}):")
    for col in changes["cast_to_numeric"]:
        lines.append(f"  {col}")
    lines.append("")
    lines.append(f"_id: {changes['_id']}")
    lines.append("")
    if changes["missing_per_col"]:
        lines.append("Missing values (NaN) per column after cleaning:")
        for col, n in changes["missing_per_col"].items():
            lines.append(f"  {col}: {n:,}")
    (out_path / "climate_cleaning_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("Loading climate-variables.csv...")
    raw = pd.read_csv(INPUT_PATH)
    print(f"  {len(raw):,} rows, {len(raw.columns)} columns")

    print("Cleaning...")
    cleaned, changes = clean(raw)

    cleaned.to_csv(OUTPUT_PATH / "climate_variables_clean.csv", index=False)
    write_report(changes, OUTPUT_PATH)

    print(f"  Duplicates removed    : {changes['duplicates_removed']:,}")
    print(f"  Dash -> NaN replacements: {sum(changes['dash_replaced_with_nan'].values())}")
    print(f"  Columns cast to numeric: {len(changes['cast_to_numeric'])}")
    print(f"Output -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
