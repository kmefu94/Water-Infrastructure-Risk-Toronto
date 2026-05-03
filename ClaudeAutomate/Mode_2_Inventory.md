# Mode 2 — Data Inventory

## Purpose
Profile and document all raw datasets before transformation. Produces a structural
understanding of each dataset: column types, missing data, uniqueness, and cross-dataset
column overlap. This is an auditing step, not a transformation step.

## Trigger
Run when: new raw data has been downloaded (after Mode 1), or when auditing an existing
raw data directory before building cleaning rules.

## Inputs
- All files under `data/RawData/<source>/` with extensions `.csv`, `.xlsx`, `.xls`
- `src/utils/data_loader.py` — `get_sources()`, `read_files()`, `pull_data()`
- `src/utils/data_summaries.py` — `quick_summary()`, `full_summary()`

## Outputs
- Console / notebook output: per-dataset summaries, column presence report
- No files written to disk (audit only)

---

## Step-by-Step Logic

### Step 1: Discover sources
1. Call `get_sources()` to list all subdirectory names under `data/RawData/`.
2. Log the list of sources found.

### Step 2: For each source

#### 2a. Collect files
1. Call `read_files(source)` to get all `.csv`, `.xlsx`, `.xls` files in that source folder.
2. Log how many files were found.

#### 2b. Load data
1. Call `pull_data(source)` to load all files into a dictionary of DataFrames.
2. Log the keys (file stems) successfully loaded.
3. Log any files that failed to load and the reason.

#### 2c. Quick summary per dataset
For each DataFrame in the loaded dictionary, produce a per-column report:
| Column | dtype | missing_pct | n_unique |
|--------|-------|-------------|----------|

#### 2d. Cross-dataset column comparison
1. Collect all unique column names across all DataFrames in this source.
2. Build a boolean matrix: rows = column names, columns = dataset names, values = True/False (column present or not).
3. This surfaces columns shared across multiple files (useful for join keys).

#### 2e. Column presence score
For each unique column across all datasets in this source:
- Count how many datasets contain it.
- Compute `presence_score = count / total_datasets`.
- List which dataset names contain it.
Sort by presence_score descending.

### Step 3: Repeat for all sources
Process each source in the list from Step 1.

### Step 4: Flag issues
After all sources are processed, flag:
- Any dataset with > 20% missing values in any column
- Any dataset with zero rows
- Any file that failed to load

---

## Error Handling

| Scenario | Action |
|----------|--------|
| CSV encoding error (UTF-8) | Retry with `latin1` encoding |
| CSV bad rows (column count mismatch) | Skip bad lines; log the first problematic row |
| Excel read failure | Log error and skip the file |
| Source folder is empty | Log warning and skip |

---

## Key Implementation Notes

### `get_sources()`
- Resolves path 2 levels up from `src/utils/data_loader.py` to project root.
- Lists subdirectories of `data/RawData/` (not files).

### `read_files(source)`
- Only returns files with extensions `.csv`, `.xlsx`, `.xls` (case-insensitive check).
- Does not recurse into subdirectories.

### `pull_data(source=None, files=None)`
- Accepts either a source name (string) or an explicit list of Path objects.
- Keys in the returned dict are file stems (filename without extension).
- Does not halt on per-file errors; continues loading remaining files.

### CSV error diagnosis
When a CSV fails to load, the fallback scans the file row-by-row using `csv.reader`
to find the first row where the column count differs from the header row.
This row index and content is logged for manual inspection.

---

## Source Reference
`reports/Data_Inventory.ipynb`, `src/utils/data_loader.py`, `src/utils/data_summaries.py`
