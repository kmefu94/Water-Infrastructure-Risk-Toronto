import sys
import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.standardize_columns import col_to_snake
from pipeline.cleaning.clean_ward_profiles import load_sheets

OUTPUT_PATH = ROOT / "data/cleaned_data/ward_census"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

CATEGORY_FIXES = {"enthic": "ethnic"}


def parse_sheet_name(name):
    m = re.match(r"(\d{4})(.*)", name)
    year = int(m.group(1))
    category = CATEGORY_FIXES.get(m.group(2), m.group(2))
    return year, category


def melt_sheet(df, year, category):
    long = df.melt(id_vars="variable", var_name="geography", value_name="value")
    long["year"] = year
    long["category"] = category
    return long


def main():
    sheets = load_sheets()
    print(f"Loaded {len(sheets)} sheets")

    groups = {}
    for name, df in sheets.items():
        year, category = parse_sheet_name(name)
        long = melt_sheet(df, year, category)
        groups.setdefault(category, []).append(long)

    for category, frames in sorted(groups.items()):
        combined = pd.concat(frames, ignore_index=True)
        combined = col_to_snake(combined)
        out_file = OUTPUT_PATH / f"{category}_long.csv"
        combined.to_csv(out_file, index=False)
        years = sorted(combined["year"].unique())
        print(f"  {category}_long.csv  {years}  ({len(combined):,} rows)")

    print(f"\nOutput -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
