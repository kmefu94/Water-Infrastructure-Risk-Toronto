# Mode 7 — Generate Risk Reports

## Purpose
Query `dim_risk_scores` and produce markdown risk brief reports for each neighbourhood,
following the standard report format defined in CLAUDE.md.

## Trigger
Run after Mode 6 (risk scores are computed and written to `dim_risk_scores`).
Can be scoped to: all neighbourhoods, flagged-only (Watch/Warning/Critical), or a specific neighbourhood.

## Inputs
- `data/infrastructure.db` — `dim_risk_scores`, `dim_neighbourhood`, `fact_breaks`, `fact_311_requests`, `fact_weather`
- Report date: today's date
- Scope parameter: `"all"` | `"flagged"` | `"<neighbourhood_name>"`

## Outputs
- Markdown files written to `reports/<neighbourhood-slug>-<YYYY-MM-DD>.md`
- One file per neighbourhood per run

---

## Report Format

```markdown
# Risk Brief: {Neighbourhood Name}
**Date:** {YYYY-MM-DD}
**Composite Risk Score:** {score}/10
**Alert Status:** {Normal | Watch | Warning | Critical}

## Score Breakdown
| Component | Score | Weight |
|-----------|-------|--------|
| Pipe Age | {pipe_age_score}/10 | 25% |
| Freeze-Thaw Exposure (90d) | {freeze_thaw_score}/10 | 35% |
| Complaint Velocity (6w) | {complaint_velocity_score}/10 | 40% |

## Key Indicators
- **Last recorded break:** {last_break_days_ago} days ago (or "No break on record")
- **Freeze-thaw events (past 90 days):** {count}
- **Early warning 311 requests (past 6 weeks):** {recent_count}
- **Change vs prior 6 weeks:** {+/- N} ({+/- pct}%)

## Infrastructure Context
- **Ward:** {ward_number} — {ward_name}
- **Average pipe age:** {avg_pipe_age_years} years
- **Population:** {population}

## Notes
{Any anomalies or data gaps noted during score computation}
```

---

## Step-by-Step Logic

### Step 1: Connect to DuckDB
Open `data/infrastructure.db` read-only (no writes in this mode).

### Step 2: Determine scope
- If scope = `"all"`: query all neighbourhood_ids from `dim_risk_scores` for today's date.
- If scope = `"flagged"`: query where `alert_flag IN ('Watch', 'Warning', 'Critical')`.
- If scope = `"<name>"`: query where `dim_neighbourhood.name = '<name>'`.

### Step 3: For each neighbourhood in scope

#### 3a. Fetch score row
```sql
SELECT *
FROM dim_risk_scores
WHERE neighbourhood_id = ?
  AND score_date = CURRENT_DATE
```

#### 3b. Fetch neighbourhood metadata
```sql
SELECT name, ward, population, avg_pipe_age_years
FROM dim_neighbourhood
WHERE neighbourhood_id = ?
```

#### 3c. Fetch supporting indicators

Freeze-thaw count (past 90 days):
```sql
SELECT COUNT(*) FROM fact_weather
WHERE date >= CURRENT_DATE - INTERVAL '90 days'
  AND freeze_thaw_event = TRUE
```

Recent 311 early warning count (past 6 weeks):
```sql
SELECT COUNT(*) FROM fact_311_requests
WHERE ward = ?
  AND is_early_warning = TRUE
  AND date >= CURRENT_DATE - INTERVAL '42 days'
```

Prior 311 early warning count (prior 6 weeks):
```sql
SELECT COUNT(*) FROM fact_311_requests
WHERE ward = ?
  AND is_early_warning = TRUE
  AND date BETWEEN CURRENT_DATE - INTERVAL '84 days' AND CURRENT_DATE - INTERVAL '42 days'
```

#### 3d. Build the neighbourhood slug
- Take `dim_neighbourhood.name`
- Lowercase, replace spaces and special characters with hyphens
- Example: "Etobicoke North" → `etobicoke-north`

#### 3e. Fill the report template
Substitute all placeholder values. For missing/null values:
- NULL score → `"N/A"`
- NULL `last_break_days_ago` → `"No break on record"`
- NULL complaint delta → `"Insufficient data"`

#### 3f. Write the file
- Path: `reports/<neighbourhood-slug>-<YYYY-MM-DD>.md`
- Overwrite if file already exists for that date.

### Step 4: Log output
After all reports are written, log:
- Total reports generated
- Any neighbourhoods skipped (missing score data)
- File paths of any Critical or Warning reports

---

## Error Handling

| Scenario | Action |
|----------|--------|
| No score row for today | Log warning; skip report for that neighbourhood |
| Neighbourhood name is NULL | Use `"ward-{ward_number}"` as the slug |
| `reports/` directory does not exist | Create it before writing |
| File write fails (permissions) | Log error with path; continue with remaining reports |

---

## Key Implementation Notes

- Reports are append-safe: each file is named with a date suffix, so re-runs on the same day
  overwrite that day's file but never affect previous days.
- Freeze-thaw count in the report is city-wide (same for all neighbourhoods) — it is descriptive,
  not per-neighbourhood.
- The `is_early_warning` filter in 311 queries must match exactly the subcategories defined in CLAUDE.md.
- Do not round scores in the template beyond 1 decimal place — preserve precision from the database.

---

## Source Reference
`CLAUDE.md` — Report format, alert thresholds, neighbourhood slug convention
