import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST_CSV = ROOT / "data/raw_data/watermains/distribution-watermain-4326.csv"
TRANS_CSV = ROOT / "data/raw_data/watermains/transmission-watermain-4326.csv"
OUTPUT_PATH = ROOT / "data/cleaned_data/watermains"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

INT_COLS = ["_id", "Watermain Type", "Watermain Diameter", "Watermain Construction Year"]
FLOAT_COLS = ["Watermain Measured Length"]


def clean(df):
    changes = {}

    # Drop geometry — spatial data, used only in transformations
    if "geometry" in df.columns:
        df = df.drop(columns=["geometry"])
        changes["geometry"] = "dropped (spatial column, used only in transformations)"

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    changes["duplicates_removed"] = before - len(df)

    # Parse install date
    df["Watermain Install Date"] = pd.to_datetime(
        df["Watermain Install Date"], errors="coerce", utc=False
    ).dt.normalize()
    changes["Watermain Install Date"] = "parsed to date (time component removed)"

    # Cast integer columns
    for col in INT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Cast float columns
    for col in FLOAT_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    changes["cast_to_int"] = [c for c in INT_COLS if c in df.columns]
    changes["cast_to_float"] = [c for c in FLOAT_COLS if c in df.columns]

    # Strip whitespace on string columns
    str_cols = ["Watermain Asset Identification", "Watermain Material", "Watermain Location Description"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].str.strip().replace("", pd.NA)

    changes["rows_raw"] = before
    changes["rows_clean"] = len(df)
    changes["missing_per_col"] = {
        col: int(df[col].isna().sum()) for col in df.columns if df[col].isna().sum() > 0
    }

    return df, changes


def write_report(dist_changes, trans_changes, combined_len, out_path):
    lines = ["WATERMAINS — CLEANING REPORT", "=" * 50, ""]
    for label, ch in [("Distribution", dist_changes), ("Transmission", trans_changes)]:
        lines.append(f"{label}: {ch['rows_raw']:,} raw rows -> {ch['rows_clean']:,} clean rows")
        lines.append(f"  Duplicates removed       : {ch['duplicates_removed']:,}")
        lines.append(f"  geometry column          : {ch['geometry']}")
        lines.append(f"  Watermain Install Date   : {ch['Watermain Install Date']}")
        lines.append(f"  Columns cast to int      : {ch['cast_to_int']}")
        lines.append(f"  Columns cast to float    : {ch['cast_to_float']}")
        if ch["missing_per_col"]:
            lines.append("  Missing values (NaN) per column:")
            for col, n in ch["missing_per_col"].items():
                lines.append(f"    {col}: {n:,}")
        lines.append("")
    lines.append(f"COMBINED TOTAL: {combined_len:,} rows")
    (out_path / "watermains_cleaning_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    print("Loading distribution watermain CSV...")
    dist_raw = pd.read_csv(DIST_CSV)
    dist_clean, dist_changes = clean(dist_raw)
    print(f"  Distribution: {len(dist_raw):,} -> {len(dist_clean):,} rows")

    print("Loading transmission watermain CSV...")
    trans_raw = pd.read_csv(TRANS_CSV)
    trans_clean, trans_changes = clean(trans_raw)
    print(f"  Transmission: {len(trans_raw):,} -> {len(trans_clean):,} rows")

    combined = pd.concat([dist_clean, trans_clean], ignore_index=True)
    combined.to_csv(OUTPUT_PATH / "watermains_clean.csv", index=False)

    write_report(dist_changes, trans_changes, len(combined), OUTPUT_PATH)

    print(f"\nCombined total: {len(combined):,} rows")
    print(f"Output -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
