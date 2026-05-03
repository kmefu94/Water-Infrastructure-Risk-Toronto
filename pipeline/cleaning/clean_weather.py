import sys
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.standardize_columns import col_to_snake

DATA_PATH = ROOT / "data/raw_data/weather-toronto"
OUTPUT_PATH = ROOT / "data/cleaned_data/weather"
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)


def load_all():
    files = sorted(DATA_PATH.glob("weather_????.csv"))
    frames = []
    for f in files:
        try:
            frames.append(pd.read_csv(f, dtype=str, low_memory=False))
        except Exception as e:
            print(f"  WARNING: could not read {f.name}: {e}")
    return pd.concat(frames, ignore_index=True)


def clean(df):
    df = col_to_snake(df)
    before = len(df)
    df = df.drop_duplicates()
    dupes = before - len(df)
    return df, dupes


def main():
    print("Loading weather CSVs...")
    raw = load_all()
    print(f"  Loaded {len(raw):,} rows from {len(list(DATA_PATH.glob('weather_????.csv')))} files")

    clean_df, dupes = clean(raw)
    print(f"  {len(raw):,} -> {len(clean_df):,} rows  |  dupes removed: {dupes:,}")

    clean_df.to_csv(OUTPUT_PATH / "weather_clean.csv", index=False)
    print(f"\nOutput -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
