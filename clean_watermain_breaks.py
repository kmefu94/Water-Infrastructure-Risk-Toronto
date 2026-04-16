import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "data/raw_data/watermain-breaks/watermain-breaks-1990-to-2016-excel.xlsx"
OUTPUT_PATH = ROOT / "data/cleaned_data/watermain_breaks"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


def clean(df):
    changes = {}

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    changes["duplicates_removed"] = before - len(df)

    # Parse break date
    df["BREAK DATE"] = pd.to_datetime(df["BREAK DATE"], errors="coerce")
    changes["BREAK DATE"] = "parsed to datetime"

    # Cast types
    df["BREAK YEAR"] = pd.to_numeric(df["BREAK YEAR"], errors="coerce").astype("Int64")
    df["X COORD"] = pd.to_numeric(df["X COORD"], errors="coerce")
    df["Y COORD"] = pd.to_numeric(df["Y COORD"], errors="coerce")
    changes["cast_to_int"] = ["BREAK YEAR"]
    changes["cast_to_float"] = ["X COORD", "Y COORD"]

    changes["rows_raw"] = before
    changes["rows_clean"] = len(df)
    changes["missing_per_col"] = {
        col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0
    }

    return df, changes


def write_report(changes, out_path):
    lines = ["WATERMAIN BREAKS — CLEANING REPORT", "=" * 50, ""]
    lines.append(f"Rows: {changes['rows_raw']:,} raw -> {changes['rows_clean']:,} clean")
    lines.append(f"Duplicates removed   : {changes['duplicates_removed']:,}")
    lines.append(f"BREAK DATE           : {changes['BREAK DATE']}")
    lines.append(f"Columns cast to int  : {changes['cast_to_int']}")
    lines.append(f"Columns cast to float: {changes['cast_to_float']}")
    lines.append("")
    if changes["missing_per_col"]:
        lines.append("Missing values (NaN) per column after cleaning:")
        for col, n in changes["missing_per_col"].items():
            lines.append(f"  {col}: {n:,}")
    (out_path / "watermain_breaks_cleaning_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("Loading watermain-breaks-1990-to-2016-excel.xlsx...")
    raw = pd.read_excel(INPUT_PATH)
    print(f"  {len(raw):,} rows, {len(raw.columns)} columns")

    print("Cleaning...")
    cleaned, changes = clean(raw)

    cleaned.to_csv(OUTPUT_PATH / "watermain_breaks_clean.csv", index=False)
    write_report(changes, OUTPUT_PATH)

    print(f"  Duplicates removed: {changes['duplicates_removed']:,}")
    print(f"  Total rows        : {len(cleaned):,}")
    print(f"Output -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
