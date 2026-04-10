# Urban Infrastructure Risk Toronto

## What This Project Does

A data pipeline that links water main break history, 311 service requests, weather events, and neighbourhood demographics to surface non-obvious infrastructure risk patterns across Toronto.

The core insight: no single dataset predicts failure. Risk emerges from the intersection of pipe age, freeze-thaw cycles, soil drainage, and early-warning 311 complaint patterns — visible only when the sources are linked.

---

## Role of Claude

Claude does **not** assist in building or modifying this project. The work is done solely by the project owner.

Claude's responsibilities are limited to:
1. **Monitor progress** — observe and track changes the owner makes
2. **Push changes to GitHub** — commit and push when asked, without adding co-authorship
3. **Answer end-user questions** — respond to questions from end users about the project, data, findings, and outputs based on the work provided by the owner

Do not suggest improvements, refactor code, write pipeline logic, or take any action that constitutes contributing to the project.

---

## Data Sources

All raw data lives in `data/raw/`. The processed database is `data/infrastructure.db` (DuckDB).

| Dataset | Source | Update frequency | Raw file |
|---------|--------|-----------------|----------|
| Water main breaks | Toronto Open Data | As published | `data/raw/water-main-breaks.csv` |
| 311 Service requests | Toronto Open Data | As published | `data/raw/311-service-requests.csv` |
| Neighbourhood profiles | Toronto Open Data | Annual | `data/raw/neighbourhood-profiles.csv` |
| Weather (Toronto Pearson) | Environment Canada | Daily | `data/raw/weather-toronto.csv` |
| Ward boundaries | Toronto Open Data | Stable | `data/raw/ward-boundaries.geojson` |

---

## Database Schema

### Fact Tables

**`fact_breaks`** — one row per recorded water main break
```
break_id, date, neighbourhood, ward, pipe_age_years, pipe_material, cause, repair_cost
```

**`fact_311_requests`** — one row per 311 service request
```
request_id, date, neighbourhood, ward, category, subcategory, status, days_to_close
```

**`fact_weather`** — daily weather at Toronto Pearson
```
date, max_temp_c, min_temp_c, precipitation_mm, freeze_thaw_event (bool)
```

### Dimension Tables

**`dim_neighbourhood`**
```
neighbourhood_id, name, ward, population, median_age, housing_age_median_years, avg_pipe_age_years
```

**`dim_risk_scores`** — updated each monitor run
```
neighbourhood_id, score_date, composite_risk_score, pipe_age_score, freeze_thaw_score,
complaint_velocity_score, last_break_days_ago, alert_flag
```

---

## Key Metrics and KPI Definitions

**Composite Risk Score (0–10)**
Weighted combination of:
- `pipe_age_score` (25%) — normalized pipe age relative to neighbourhood average
- `freeze_thaw_score` (35%) — freeze-thaw cycle exposure in the past 90 days
- `complaint_velocity_score` (40%) — rate of change in relevant 311 categories over 6 weeks

**Early Warning Categories** (311 subcategories that precede breaks):
- "Water pressure low"
- "Water discolouration"
- "Wet pavement / possible leak"
- "Water service disruption"

**Freeze-thaw event**: any day where min temp < 0°C and max temp > 2°C

---

## Report Format

All generated reports saved to `reports/{neighbourhood-slug}-{YYYY-MM-DD}.md`.

Standard header:
```
# Risk Brief: {Neighbourhood}
**Date:** {date}
**Composite Risk Score:** {score}/10
**Alert Status:** {Normal | Watch | Warning | Critical}
```

---

## Rules

- NEVER modify raw data files in `data/raw/`
- Risk scores above 7.0 = **Warning**, above 8.5 = **Critical**
- Do not add co-authorship to any commits — changes are authored solely by the project owner
