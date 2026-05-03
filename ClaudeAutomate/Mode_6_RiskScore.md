# Mode 6 — Compute Risk Scores

## Purpose
Query the DuckDB database and compute composite risk scores for each neighbourhood.
Write results into `dim_risk_scores`. Flags neighbourhoods that cross warning thresholds.

## Trigger
Run after Mode 5 (database is populated with fact and dimension tables).
Can be re-run at any time to refresh scores against updated data.

## Inputs
- `data/infrastructure.db` — DuckDB with populated fact and dimension tables
- Score date: today's date (`datetime.date.today()`)

## Outputs
- Rows inserted/updated in `dim_risk_scores`
- One row per neighbourhood per run date

---

## Composite Risk Score Definition

**Score range**: 0–10 (higher = higher risk)

| Component | Weight | Column |
|-----------|--------|--------|
| Pipe age score | 25% | `pipe_age_score` |
| Freeze-thaw score | 35% | `freeze_thaw_score` |
| Complaint velocity score | 40% | `complaint_velocity_score` |

```
composite_risk_score = (pipe_age_score × 0.25) + (freeze_thaw_score × 0.35) + (complaint_velocity_score × 0.40)
```

**Alert thresholds:**
- `composite_risk_score > 8.5` → `alert_flag = "Critical"`
- `composite_risk_score > 7.0` → `alert_flag = "Warning"`
- `composite_risk_score > 5.0` → `alert_flag = "Watch"`
- Otherwise → `alert_flag = "Normal"`

---

## Step-by-Step Logic

### Step 1: Connect to DuckDB
Open `data/infrastructure.db` for read/write.

---

### Step 2: Compute `pipe_age_score` (weight: 25%)

For each neighbourhood:
1. Query `dim_neighbourhood.avg_pipe_age_years`.
2. Normalize across all neighbourhoods:
   ```
   pipe_age_score = 10 × (avg_pipe_age_years − min_age) / (max_age − min_age)
   ```
   Where min/max are taken across all neighbourhoods in `dim_neighbourhood`.
3. Clamp result to [0, 10].

SQL pattern:
```sql
SELECT
    neighbourhood_id,
    10.0 * (avg_pipe_age_years - MIN(avg_pipe_age_years) OVER ())
           / NULLIF(MAX(avg_pipe_age_years) OVER () - MIN(avg_pipe_age_years) OVER (), 0)
    AS pipe_age_score
FROM dim_neighbourhood
```

---

### Step 3: Compute `freeze_thaw_score` (weight: 35%)

Lookback window: past 90 days from score date.

1. Query `fact_weather` for all rows where `date >= (score_date - 90 days)`.
2. Count rows where `freeze_thaw_event = TRUE`.
3. Normalize: `freeze_thaw_score = 10 × (count / 90)` — capped at 10.

Note: This score is the same for all neighbourhoods in a run (city-wide weather).
It can be computed once and applied to all rows.

SQL pattern:
```sql
SELECT
    COUNT(*) FILTER (WHERE freeze_thaw_event = TRUE) AS freeze_thaw_count
FROM fact_weather
WHERE date >= CURRENT_DATE - INTERVAL '90 days'
```

---

### Step 4: Compute `complaint_velocity_score` (weight: 40%)

Lookback windows: compare 6-week period vs prior 6-week period.

**Early Warning Categories** (filter `fact_311_requests` to these subcategories):
- "Water pressure low"
- "Water discolouration"
- "Wet pavement / possible leak"
- "Water service disruption"

For each neighbourhood:
1. Count early warning requests in the **recent 6 weeks** (weeks −6 to 0).
2. Count early warning requests in the **prior 6 weeks** (weeks −12 to −6).
3. Compute velocity:
   ```
   velocity = (recent_count - prior_count) / NULLIF(prior_count, 0)
   ```
   - Positive = increasing complaint rate (higher risk)
   - Negative = decreasing complaint rate
   - If prior_count = 0 and recent_count > 0: velocity = 1.0 (treat as maximum increase)
4. Normalize velocity to [0, 10]:
   ```
   complaint_velocity_score = CLAMP(5 + (velocity × 5), 0, 10)
   ```
   - Velocity of 0 (no change) → score of 5
   - Velocity of +1.0 (doubled) → score of 10
   - Velocity of −1.0 (halved) → score of 0

SQL pattern:
```sql
WITH recent AS (
    SELECT ward, COUNT(*) AS recent_count
    FROM fact_311_requests
    WHERE is_early_warning = TRUE
      AND date >= CURRENT_DATE - INTERVAL '42 days'
    GROUP BY ward
),
prior AS (
    SELECT ward, COUNT(*) AS prior_count
    FROM fact_311_requests
    WHERE is_early_warning = TRUE
      AND date BETWEEN CURRENT_DATE - INTERVAL '84 days' AND CURRENT_DATE - INTERVAL '42 days'
    GROUP BY ward
)
SELECT
    n.neighbourhood_id,
    COALESCE(r.recent_count, 0) AS recent_count,
    COALESCE(p.prior_count, 0) AS prior_count
FROM dim_neighbourhood n
LEFT JOIN recent r ON n.ward = r.ward
LEFT JOIN prior p ON n.ward = p.ward
```

---

### Step 5: Compute `last_break_days_ago`

For each neighbourhood:
```sql
SELECT
    n.neighbourhood_id,
    DATEDIFF('day', MAX(b.date), CURRENT_DATE) AS last_break_days_ago
FROM dim_neighbourhood n
LEFT JOIN fact_breaks b ON n.ward = b.ward
GROUP BY n.neighbourhood_id
```
- If no breaks on record: set `last_break_days_ago = NULL`.

---

### Step 6: Assemble and write scores

1. Join all component scores on `neighbourhood_id`.
2. Compute `composite_risk_score`:
   ```
   composite_risk_score = ROUND((pipe_age_score * 0.25) + (freeze_thaw_score * 0.35) + (complaint_velocity_score * 0.40), 2)
   ```
3. Assign `alert_flag`:
   - `> 8.5` → `"Critical"`
   - `> 7.0` → `"Warning"`
   - `> 5.0` → `"Watch"`
   - else → `"Normal"`
4. Set `score_date = today`.
5. Insert rows into `dim_risk_scores`. On conflict (same neighbourhood + date), replace.

---

## Error Handling

| Scenario | Action |
|----------|--------|
| No weather data in past 90 days | Set `freeze_thaw_score = NULL`; log warning |
| Neighbourhood has no 311 data | Set `complaint_velocity_score = 5.0` (neutral) |
| Neighbourhood has no breaks on record | Set `last_break_days_ago = NULL` |
| Division by zero in normalization | Use `NULLIF` in SQL to return NULL; propagate NULL through to composite score |
| Composite score is NULL | Set `alert_flag = "Unknown"`; log which component was missing |

---

## Source Reference
`CLAUDE.md` — KPI definitions, alert thresholds, freeze-thaw definition, early warning categories
