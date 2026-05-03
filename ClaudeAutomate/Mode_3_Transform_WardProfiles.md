# Mode 3 — Transform: Ward Profiles

## Purpose
Parse the ward profile census Excel workbook and split it into individual, clean DataFrames —
one per census year/category combination. Attach ward names to ward numbers to produce
labelled, tidy output ready for loading into DuckDB.

## Trigger
Run after Mode 1 (raw data is present). This mode targets a specific known file and
does not depend on other transformation modes.

## Inputs

| File | Path | Notes |
|------|------|-------|
| Ward profiles (modified) | `data/RawData/ward-profiles-25-ward-model/2023-wardprofiles-2011-2021-censusdata_rev0719_modified.xlsx` | 16 sheets; pre-cleaned by project owner |
| Ward names lookup | `data/RawData/ward-profiles-25-ward-model/25-wardnames-numbers.xlsx` | Maps ward numbers to names |

**Excluded files** (skip these, do not load):
- `2023-wardprofiles-geographicareas.xlsx`

## Outputs
- 16 tidy DataFrames in memory, one per sheet, keyed by sheet name
- Ward names lookup DataFrame (`Ward Number` → `Ward Name`)
- These feed into Mode 5 (Load) for insertion into DuckDB

---

## Step-by-Step Logic

### Step 1: Load the modified workbook

1. Open `2023-wardprofiles-2011-2021-censusdata_rev0719_modified.xlsx` using `pd.ExcelFile`.
2. For each sheet in `xls.sheet_names`:
   - Normalize the sheet name: lowercase, replace spaces with underscores.
   - Read the sheet into a DataFrame using `pd.read_excel`.
3. Store all sheets in a dictionary: `{normalized_sheet_name: DataFrame}`.

Expected sheet keys after normalization:
```
2021population, 2021dwellings, 2021families, 2021education, 2021ethnic, 2021income,
2016population, 2016dwellings, 2016families, 2016education, 2016enthic, 2016labour, 2016income,
2011households, 2011families, 2011population
```

Note: `2016enthic` is a typo in the source data for "ethnic" — preserve as-is to match the sheet name.

### Step 2: Load the ward names lookup

1. Load `25-wardnames-numbers.xlsx` using `pull_data(files=[ward_names_file])`.
2. Extract the DataFrame from the returned dict using key `"25-wardnames-numbers"`.
3. Expected columns: `Ward Number` (int, 1–25), `Ward Name` (string).

### Step 3: Understand the sheet structure

Each of the 16 sheets has this layout:

| Row | Content |
|-----|---------|
| 0 | Category title (e.g., "Population", "Dwellings") — single value in col 0, rest NaN |
| 1 | Column headers: NaN in col 0, then "Toronto", "Ward 1", "Ward 2", ..., "Ward 25" |
| 2+ | Data rows: metric label in col 0, numeric values in cols 1–26 |

Total columns: 27 (col 0 = metric label, col 1 = Toronto aggregate, cols 2–26 = Ward 1–25)

### Step 4: Clean each sheet

For each sheet DataFrame:

1. **Extract the category title**: value at `df.iloc[0, 0]` — store as metadata.
2. **Set column headers**: use row index 1 as the header row.
   - Col 0 → rename to `"metric"`
   - Col 1 → `"Toronto"`
   - Cols 2–26 → `"Ward 1"` through `"Ward 25"` (already present in row 1)
3. **Drop header rows**: remove rows 0 and 1 from the data (they are now metadata/headers).
4. **Drop empty rows**: remove any row where `metric` is NaN or empty string.
5. **Reset index**.

### Step 5: Reshape to long format (tidy data)

For each cleaned sheet:

1. Melt from wide to long:
   - `id_vars`: `["metric"]`
   - `value_vars`: `["Toronto", "Ward 1", ..., "Ward 25"]`
   - Result columns: `metric`, `geography`, `value`
2. Parse `geography`:
   - If `geography == "Toronto"` → `ward_number = 0`, `ward_name = "Toronto"`
   - Else extract the integer from `"Ward N"` → `ward_number = N`
3. Join `ward_name` from the ward names lookup on `ward_number`.
4. Add a `year` column extracted from the sheet name (first 4 characters, e.g., `"2021"`).
5. Add a `category` column from the category title captured in Step 4.

Final columns per row:
```
year | category | metric | ward_number | ward_name | value
```

### Step 6: Validate

For each cleaned sheet:
- Confirm row count is `(number of metrics) × 26` (25 wards + Toronto).
- Confirm no NaN values in `metric`, `ward_number`, or `ward_name`.
- Log any unexpected shapes or missing joins.

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Target Excel file not found | Raise FileNotFoundError with full expected path |
| Sheet name not in expected list | Log warning but continue — do not drop unknown sheets |
| Row 1 does not contain "Toronto" in col 1 | Log error for that sheet; skip cleaning, return raw DataFrame |
| Ward number not found in lookup | Log warning; set `ward_name = "Unknown"` |
| Non-numeric value in a data cell | Leave as-is; do not coerce — downstream load handles typing |

---

## Key Implementation Notes

- The `_modified` file is the authoritative input — never use the original unmodified file in this mode.
- `2023-wardprofiles-geographicareas.xlsx` must be excluded during file discovery.
- The sheet name typo `2016enthic` (should be "ethnic") is preserved as-is — do not rename.
- The `pull_data` utility in `src/utils/data_loader.py` accepts an explicit `files=` list,
  bypassing folder discovery — use this when loading the ward names file directly by path.
- When loading the modified workbook, do not use `pull_data` — use `pd.ExcelFile` directly
  to access all sheets without flattening to a single DataFrame.

---

## Source Reference
`pipeline/Transformations/ward_profiles_split.ipynb`
