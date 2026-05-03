# Mode 5 — Load to DuckDB

## Purpose
Write all cleaned, transformed DataFrames from Modes 3 and 4 into the DuckDB database
at `data/infrastructure.db`. Creates tables if they do not exist; replaces data on re-run.

## Trigger
Run after Modes 3 and 4 have completed and all target DataFrames are in memory.

## Inputs
- Cleaned DataFrames from Mode 3 (ward profiles → `dim_neighbourhood` census data)
- Cleaned DataFrames from Mode 4 (`fact_breaks`, `fact_311_requests`, `fact_weather`, pipe age for `dim_neighbourhood`)
- DuckDB at `data/infrastructure.db`

## Outputs
- Populated tables in `data/infrastructure.db`:
  - `fact_breaks`
  - `fact_311_requests`
  - `fact_weather`
  - `dim_neighbourhood`
  - `dim_risk_scores` (empty shell, populated by Mode 6)

---

## Schema Definitions

### `fact_breaks`
```sql
CREATE TABLE IF NOT EXISTS fact_breaks (
    break_id        INTEGER PRIMARY KEY,
    date            DATE,
    neighbourhood   VARCHAR,
    ward            INTEGER,
    pipe_age_years  INTEGER,
    pipe_material   VARCHAR,
    cause           VARCHAR,
    repair_cost     DOUBLE
);
```

### `fact_311_requests`
```sql
CREATE TABLE IF NOT EXISTS fact_311_requests (
    request_id          VARCHAR PRIMARY KEY,
    date                DATE,
    neighbourhood       VARCHAR,
    ward                INTEGER,
    category            VARCHAR,
    subcategory         VARCHAR,
    status              VARCHAR,
    days_to_close       INTEGER,
    is_early_warning    BOOLEAN
);
```

### `fact_weather`
```sql
CREATE TABLE IF NOT EXISTS fact_weather (
    date                DATE PRIMARY KEY,
    max_temp_c          DOUBLE,
    min_temp_c          DOUBLE,
    precipitation_mm    DOUBLE,
    freeze_thaw_event   BOOLEAN
);
```

### `dim_neighbourhood`
```sql
CREATE TABLE IF NOT EXISTS dim_neighbourhood (
    neighbourhood_id            INTEGER PRIMARY KEY,
    name                        VARCHAR,
    ward                        INTEGER,
    population                  INTEGER,
    median_age                  DOUBLE,
    housing_age_median_years    INTEGER,
    avg_pipe_age_years          DOUBLE
);
```

### `dim_risk_scores`
```sql
CREATE TABLE IF NOT EXISTS dim_risk_scores (
    neighbourhood_id            INTEGER,
    score_date                  DATE,
    composite_risk_score        DOUBLE,
    pipe_age_score              DOUBLE,
    freeze_thaw_score           DOUBLE,
    complaint_velocity_score    DOUBLE,
    last_break_days_ago         INTEGER,
    alert_flag                  VARCHAR,
    PRIMARY KEY (neighbourhood_id, score_date)
);
```

---

## Step-by-Step Logic

### Step 1: Connect to DuckDB
1. Open connection: `duckdb.connect("data/infrastructure.db")`.
2. Log confirmation that the connection was established.

### Step 2: Create tables
1. Execute each `CREATE TABLE IF NOT EXISTS` statement above.
2. If a table already exists, it is retained (no data loss on re-run from this step alone).

### Step 3: Load each table

For each target table, use `INSERT OR REPLACE` semantics (or `DELETE + INSERT`):

1. **`fact_breaks`**: Load from Mode 4A output.
2. **`fact_311_requests`**: Load from Mode 4C output.
3. **`fact_weather`**: Load from Mode 4D output.
4. **`dim_neighbourhood`**: Merge Mode 3 (census/demographics) and Mode 4B (pipe age) outputs.
   - Join on ward number or neighbourhood name.
   - Assign sequential `neighbourhood_id`.
5. **`dim_risk_scores`**: Insert empty shell (table exists but has no rows at this stage).

### Step 4: Validate row counts
After each table load, query `SELECT COUNT(*) FROM <table>` and log:
- Table name
- Rows inserted
- Expected count (from source DataFrame length)
- Pass / fail

### Step 5: Close connection
Close the DuckDB connection.

---

## Error Handling

| Scenario | Action |
|----------|--------|
| DuckDB file is locked by another process | Wait 5 seconds and retry once; if still locked, halt and log |
| DataFrame column mismatch with table schema | Log the mismatch; halt load for that table only |
| Duplicate primary key on insert | Log the duplicate key; skip or overwrite depending on table |
| Empty DataFrame | Log warning; skip insert but do not fail |

---

## Key Implementation Notes

- Use `duckdb` Python package: `import duckdb`.
- DuckDB supports direct DataFrame registration: `conn.register("df_name", df)` then `INSERT INTO table SELECT * FROM df_name`.
- On full re-run, drop and recreate tables to ensure clean state:
  `DROP TABLE IF EXISTS <table>; CREATE TABLE ...`
- The `dim_neighbourhood` table combines data from two separate modes (ward profiles + watermain infrastructure).
  These must be joined before insertion — do not insert them separately into the same table.
- `dim_risk_scores` is intentionally empty at load time; it is populated by Mode 6.
