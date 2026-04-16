import zipfile
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data/raw_data/311-service-requests-customer-initiated"
OUTPUT_PATH = ROOT / "data/cleaned_data/311"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2010, 2019))
STRING_COLS = [
    "Status",
    "First 3 Chars of Postal Code",
    "Intersection Street 1",
    "Intersection Street 2",
    "Ward",
    "Service Request Type",
    "Division",
    "Section",
]


def load_year(year):
    zpath = DATA_PATH / f"311-service-requests-{year}.zip"
    with zipfile.ZipFile(zpath) as z:
        with z.open(z.namelist()[0]) as f:
            return pd.read_csv(f, dtype=str, low_memory=False)


def clean(df):
    changes = {}

    # Remove duplicates
    before = len(df)
    df = df.drop_duplicates()
    changes["duplicates_removed"] = before - len(df)

    # Parse Creation Date
    df["Creation Date"] = pd.to_datetime(df["Creation Date"], errors="coerce")
    changes["Creation Date"] = "parsed to datetime"

    # Strip whitespace and replace empty strings with NaN on string columns
    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].str.strip().replace("", pd.NA)

    # Fill remaining NaN
    missing_before = df.isna().sum()
    df[STRING_COLS] = df[STRING_COLS].fillna(pd.NA)
    missing_after = df.isna().sum()
    changes["missing_filled"] = {
        col: int(missing_before[col])
        for col in df.columns
        if missing_before[col] > 0
    }

    return df, changes


def write_report(all_changes, total_rows, out_path):
    lines = ["311 SERVICE REQUESTS — CLEANING REPORT", "=" * 50, ""]
    for year, ch in all_changes.items():
        lines.append(f"Year {year} ({ch['rows_raw']:,} raw rows -> {ch['rows_clean']:,} clean rows)")
        lines.append(f"  Duplicates removed : {ch['duplicates_removed']:,}")
        if ch["missing_filled"]:
            lines.append("  Missing values (NaN) per column:")
            for col, n in ch["missing_filled"].items():
                lines.append(f"    {col}: {n:,}")
        lines.append(f"  Creation Date      : {ch['Creation Date']}")
        lines.append("")
    lines.append(f"COMBINED TOTAL: {total_rows:,} rows")
    (out_path / "311_cleaning_report.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    frames = []
    all_changes = {}

    for year in YEARS:
        raw = load_year(year)
        cleaned, changes = clean(raw)
        changes["rows_raw"] = len(raw)
        changes["rows_clean"] = len(cleaned)
        all_changes[year] = changes
        frames.append(cleaned)
        print(f"  {year}: {len(raw):,} -> {len(cleaned):,} rows  |  dupes removed: {changes['duplicates_removed']:,}")

    combined = pd.concat(frames, ignore_index=True)

    # Combined output
    combined.to_csv(OUTPUT_PATH / "311_requests_clean.csv", index=False)

    # 3-year block outputs
    blocks = {"2010_2012": (2010, 2012), "2013_2015": (2013, 2015), "2016_2018": (2016, 2018)}
    for label, (start, end) in blocks.items():
        block = pd.concat(
            [f for y, f in zip(YEARS, frames) if start <= y <= end],
            ignore_index=True,
        )
        block.to_csv(OUTPUT_PATH / f"311_requests_{label}.csv", index=False)
        print(f"  Block {label}: {len(block):,} rows")

    write_report(all_changes, len(combined), OUTPUT_PATH)
    print(f"\nTotal rows: {len(combined):,}")
    print(f"Output -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
