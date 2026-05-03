import re
import sys
import zipfile
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.standardize_columns import col_to_snake, col_to_date, col_to_cat
from src.utils.ward_map import apply_ward_25

DATA_PATH = ROOT / "data/raw_data/311-service-requests-customer-initiated"
OUTPUT_PATH = ROOT / "data/cleaned_data/311"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

YEARS = list(range(2010, 2019))

STRING_COLS = [
    "status",
    "first_3_chars_of_postal_code",
    "intersection_street_1",
    "intersection_street_2",
    "ward",
    "service_request_type",
    "division",
    "section",
]

FLOOD_HIGH = [
    "Catch Basin - Blocked / Flooding",
    "Driveway - Damaged / Ponding",
    "Road Water Ponding",
    "Sidewalk Water Ponding",
    "Watercourses-Blocked/Flooding",
    "Watercourses-Erosion/Washout",
    "Watercourses-Outfalls/Inlets",
    "West Nile Virus - Standing water / Roadway",
    "West Nile Virus-Standing water / Roadside",
    "Storm Event-Flooding",
]
FLOOD_MEDIUM = [
    "Watermain-Possible Break",
    "Watermain Valve - Turn On",
    "Salting-Winter (WSL/HYDT/VALVE/Watermain Break Locations etc.)",
    "Hydrant-Leaking",
    "Water Valve-Leaking",
    "Water Service Line-Damaged Water Service Box",
]
FLOOD_TYPES = set(FLOOD_HIGH + FLOOD_MEDIUM)


def load_year(year):
    zpath = DATA_PATH / f"311-service-requests-{year}.zip"
    with zipfile.ZipFile(zpath) as z:
        with z.open(z.namelist()[0]) as f:
            return pd.read_csv(f, dtype=str, low_memory=False)


def clean(df):
    changes = {}

    df = col_to_snake(df)

    before = len(df)
    df = df.drop_duplicates()
    changes["duplicates_removed"] = before - len(df)

    df["creation_date"] = pd.to_datetime(df["creation_date"], errors="coerce")
    changes["creation_date"] = "parsed to datetime"

    for col in STRING_COLS:
        if col in df.columns:
            df[col] = df[col].str.strip().replace("", pd.NA)

    missing_before = df.isna().sum()
    df[STRING_COLS] = df[STRING_COLS].fillna(pd.NA)
    changes["missing_filled"] = {
        col: int(missing_before[col])
        for col in df.columns
        if missing_before[col] > 0
    }

    df = apply_ward_25(df, ward_col="ward", out_col="ward_25")
    changes["ward_25"] = "mapped from 44-ward string via ward_map lookup"

    return df, changes


def transform(df):
    df = df.drop(columns=["first_3_chars_of_postal_code", "intersection_street_1", "intersection_street_2"], errors="ignore")

    df = df[df["service_request_type"].isin(FLOOD_TYPES)].copy()

    tier_map = {t: "HIGH" for t in FLOOD_HIGH}
    tier_map.update({t: "MEDIUM" for t in FLOOD_MEDIUM})
    df["flood_tier"] = df["service_request_type"].map(tier_map)

    df = df.drop_duplicates(subset=["creation_date", "status", "ward", "service_request_type"], keep="first")
    df = df.drop_duplicates(subset=["creation_date", "ward", "service_request_type"], keep=False)

    df = df[df["status"] != "Cancelled"].reset_index(drop=True)

    def _merge_ward(row):
        if pd.isna(row["ward_25"]):
            return row["ward"]
        return re.sub(r"\(\d+\)", f"({int(row['ward_25'])})", str(row["ward"]))

    df["ward"] = df.apply(_merge_ward, axis=1)
    df = df.drop(columns="ward_25")

    col_to_date(df=df, columns="creation_date")
    col_to_cat(df=df, columns=["status", "ward", "service_request_type", "division", "section", "flood_tier"])

    return df


def write_report(all_changes, total_explore, total_clean, out_path):
    lines = ["311 SERVICE REQUESTS — CLEANING REPORT", "=" * 50, ""]
    for year, ch in all_changes.items():
        lines.append(f"Year {year} ({ch['rows_raw']:,} raw -> {ch['rows_clean']:,} clean)")
        lines.append(f"  Duplicates removed : {ch['duplicates_removed']:,}")
        if ch["missing_filled"]:
            lines.append("  Missing values (NaN) per column:")
            for col, n in ch["missing_filled"].items():
                lines.append(f"    {col}: {n:,}")
        lines.append(f"  creation_date      : {ch['creation_date']}")
        lines.append(f"  ward_25            : {ch['ward_25']}")
        lines.append("")
    lines.append(f"explore_311 total : {total_explore:,} rows")
    lines.append(f"311_requests_clean: {total_clean:,} rows (flood/water filtered)")
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
        print(f"  {year}: {len(raw):,} -> {len(cleaned):,} rows  |  dupes: {changes['duplicates_removed']:,}")

    explore = pd.concat(frames, ignore_index=True)
    explore.to_csv(OUTPUT_PATH / "explore_311.csv", index=False)
    print(f"\nexplore_311: {len(explore):,} rows")

    clean_df = transform(explore.copy())
    clean_df.to_csv(OUTPUT_PATH / "311_requests_clean.csv", index=False)
    print(f"311_requests_clean: {len(clean_df):,} rows")

    write_report(all_changes, len(explore), len(clean_df), OUTPUT_PATH)
    print(f"\nOutput -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
