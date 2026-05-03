# Mode 4 — Transform: Core Datasets

## Purpose
Clean and standardize the four remaining raw datasets (water main breaks, watermains,
311 service requests, weather/climate) into consistent tabular form ready for loading
into DuckDB. Each dataset maps to a fact or dimension table in the schema.

## Trigger
Run after Mode 1 (raw data downloaded). Runs in parallel with Mode 3.

## Inputs

| Dataset | Raw Path | Target Table |
|---------|----------|--------------|
| Water main breaks | `data/RawData/watermain-breaks/watermain-breaks-1990-to-2016-excel.xlsx` | `fact_breaks` |
| Watermains (infrastructure) | `data/RawData/watermains/distribution-watermain-2952.*` | `dim_neighbourhood` (pipe age) |
| 311 Service requests | `data/RawData/311-service-requests-customer-initiated/SR<YEAR>.csv` (one file per year) | `fact_311_requests` |
| Climate/weather | `data/RawData/current-and-future-climate/climate-variables.*` | `fact_weather` |

## Outputs
- Cleaned DataFrames in memory, named per target table schema
- Fed into Mode 5 (Load) for DuckDB insertion

---

## Target Schema Reference

### `fact_breaks`
```
break_id, date, neighbourhood, ward, pipe_age_years, pipe_material, cause, repair_cost
```

### `fact_311_requests`
```
request_id, date, neighbourhood, ward, category, subcategory, status, days_to_close
```

### `fact_weather`
```
date, max_temp_c, min_temp_c, precipitation_mm, freeze_thaw_event (bool)
```

### `dim_neighbourhood` (pipe age contribution)
```
neighbourhood_id, name, ward, population, median_age, housing_age_median_years, avg_pipe_age_years
```

---

## Step-by-Step Logic

---

### Sub-mode 4A: Water Main Breaks → `fact_breaks`

1. Load `watermain-breaks-1990-to-2016-excel.xlsx` using `pull_data`.
2. Map source columns to schema columns:
   - Identify the date column → standardize to `date` (parse as datetime, output as `YYYY-MM-DD`)
   - Identify neighbourhood / ward columns → map to `neighbourhood`, `ward`
   - Identify pipe age or install year column → derive `pipe_age_years` if not directly present
   - Identify pipe material column → map to `pipe_material`
   - Identify cause column → map to `cause`
   - Identify repair cost column → map to `repair_cost`
3. Generate `break_id` as a sequential integer index if no natural key exists.
4. Drop any row where `date` is null.
5. Standardize string columns: strip whitespace, title-case where appropriate.

---

### Sub-mode 4B: Watermains Infrastructure → `dim_neighbourhood` (pipe age)

1. Load the distribution-watermain file using `pull_data`.
2. Extract the `Install Date` column (note: contains null values — handle gracefully).
3. Parse `Install Date` as datetime; rows with null install date are included but `pipe_age_years` will be null.
4. Compute `pipe_age_years` = current year − year(Install Date) where available.
5. Group by neighbourhood/ward to compute `avg_pipe_age_years` per area.
6. Output: one row per neighbourhood with `avg_pipe_age_years`.

---

### Sub-mode 4C: 311 Service Requests → `fact_311_requests`

1. Discover all SR files: files matching `SR<YEAR>.csv` pattern in the 311 source folder.
2. Load each file using `pull_data` with UTF-8 encoding (fallback to latin1 on failure).
3. Concatenate all year files into a single DataFrame.
4. Map columns to schema:
   - Request identifier → `request_id`
   - Date opened → `date` (parse as datetime)
   - Neighbourhood / ward → `neighbourhood`, `ward`
   - Service category → `category`
   - Service subcategory → `subcategory`
   - Status → `status`
   - Derive `days_to_close`: date closed − date opened (in days); null if not yet closed
5. Filter to keep only **Early Warning Categories** (relevant to infrastructure risk):
   - "Water pressure low"
   - "Water discolouration"
   - "Wet pavement / possible leak"
   - "Water service disruption"
   
   Note: Keep all categories in the full dataset for `fact_311_requests`, but flag early warning rows with a boolean `is_early_warning` column.
6. Drop rows where `date` is null.
7. Standardize string columns.

---

### Sub-mode 4D: Climate / Weather → `fact_weather`

1. Load the climate-variables file using `pull_data`.
2. Identify the date column → standardize to `date`.
3. Map temperature and precipitation columns:
   - Daily maximum temperature → `max_temp_c`
   - Daily minimum temperature → `min_temp_c`
   - Daily precipitation → `precipitation_mm`
4. Compute `freeze_thaw_event` (boolean):
   - `True` if `min_temp_c < 0` AND `max_temp_c > 2`
   - `False` otherwise
   - `NULL` if either temperature value is missing
5. Drop rows where `date` is null.
6. One row per day; if multiple rows exist per day, aggregate (take max/min appropriately).

---

## Error Handling

| Scenario | Action |
|----------|--------|
| Source file not found | Log error with expected path; skip sub-mode |
| Column name not recognized | Log warning with available column names; halt sub-mode and request mapping |
| Date parsing fails on a row | Set `date = NULL`; flag row in log |
| Null install date (watermains) | Set `pipe_age_years = NULL`; retain the row |
| 311 CSV bad lines | Skip bad lines (use `on_bad_lines="skip"`); log count of skipped rows |
| Encoding error | Retry with `latin1`; log if fallback was needed |

---

## Key Implementation Notes

- Use `pull_data` from `src/utils/data_loader.py` for all file loading.
- The 311 dataset is split by year — concatenate all files before processing.
- The early warning filter for 311 is applied at the reporting/scoring stage (Mode 6),
  but the `is_early_warning` flag should be computed here during transformation.
- Pipe age computation requires knowing the current year — use `datetime.date.today().year`.
- Do not impute missing values; retain NULLs for the database layer to handle.

---

## Source Reference
`reports/Data_Inventory.ipynb` (exploration of all four datasets)
`CLAUDE.md` (schema definitions, freeze-thaw definition, early warning categories)
