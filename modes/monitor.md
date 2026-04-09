# Mode: Monitor — Data Refresh and Risk Change Detection

The user wants to refresh the data and check what has changed since the last run. Run the full pipeline, recompute risk scores, and surface anything that crossed a threshold or moved significantly.

---

## Process

### 1. Check last run

Read `data/monitor-log.md` to find the date of the last monitor run. If the file doesn't exist yet, this is the first run — note that.

### 2. Refresh data

Run ingestion for all sources:

```bash
python pipeline/ingest.py
```

If ingest fails for any source, note it (don't abort — partial data is better than nothing). Report which sources succeeded and which failed.

### 3. Rebuild and validate

```bash
python pipeline/transform.py
python pipeline/validate.py
```

If validate surfaces data quality issues (nulls, duplicates, out-of-range values), report them. Don't proceed to scoring if more than 20% of rows are affected.

### 4. Recompute risk scores

```bash
python pipeline/score.py
```

This updates `dim_risk_scores` with today's scores.

### 5. Detect changes

Query for significant movements since the last run:

```sql
-- Neighbourhoods that crossed a threshold (new Warnings or Criticals)
SELECT
  current.neighbourhood_id,
  n.name,
  prev.composite_risk_score AS score_before,
  current.composite_risk_score AS score_now,
  current.alert_flag,
  current.complaint_velocity_score,
  current.freeze_thaw_score
FROM dim_risk_scores current
JOIN dim_risk_scores prev
  ON current.neighbourhood_id = prev.neighbourhood_id
  AND prev.score_date = (SELECT MAX(score_date) FROM dim_risk_scores WHERE score_date < current.score_date)
JOIN dim_neighbourhood n ON current.neighbourhood_id = n.neighbourhood_id
WHERE current.score_date = CURRENT_DATE
  AND (
    current.composite_risk_score > 7.0  -- now in Warning or Critical
    OR current.composite_risk_score - prev.composite_risk_score > 1.5  -- jumped significantly
  )
ORDER BY current.composite_risk_score DESC
```

Also check for new recorded breaks since last run:

```sql
SELECT date, neighbourhood, pipe_age_years, cause
FROM fact_breaks
WHERE date > '{last_run_date}'
ORDER BY date DESC
```

### 6. Log the run

Append to `data/monitor-log.md`:
```
{YYYY-MM-DD} | Sources refreshed: {n}/5 | New breaks: {n} | New warnings: {n} | New criticals: {n}
```

### 7. Report findings

Structure your response as:

**Data refresh**
- Which sources updated, which (if any) failed
- Date range of new records ingested

**New breaks recorded**
- List any new breaks since last run with neighbourhood and cause

**Risk score changes**
- Neighbourhoods that crossed into Warning (>7.0) or Critical (>8.5) — flag these prominently
- Neighbourhoods with the largest score increase (even if not yet at threshold)
- Any neighbourhoods that improved significantly (worth noting)

**Early warning signals**
- Neighbourhoods with rapidly rising complaint velocity but no recent break — these are the actionable ones

**Recommended next step**
- Suggest which neighbourhood to run a full `report` on, and why

---

## Alert levels

| Score | Status | Action |
|-------|--------|--------|
| 0–5.0 | Normal | No action needed |
| 5.0–7.0 | Elevated | Monitor next cycle |
| 7.0–8.5 | Warning | Flag for report |
| 8.5–10 | Critical | Immediate report + highlight |
