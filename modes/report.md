# Mode: Report — Neighbourhood Risk Brief

Generate a full risk brief for a specific neighbourhood or ward. This is the main deliverable output — a structured markdown document saved to `reports/`.

---

## Process

### 1. Identify the target

Extract the neighbourhood or ward from the user's message. If ambiguous or not provided, ask:
> "Which neighbourhood or ward would you like a report for? Or should I generate briefs for all current Warning and Critical areas?"

Validate the name exists in `dim_neighbourhood`:

```bash
python -c "
import duckdb
con = duckdb.connect('data/infrastructure.db')
print(con.execute(\"SELECT name, ward FROM dim_neighbourhood WHERE LOWER(name) LIKE LOWER('%{input}%')\").df().to_string(index=False))
"
```

If no match, show the closest results and ask the user to confirm.

### 2. Pull all data for the neighbourhood

Run each of these queries and hold the results:

**Current risk profile:**
```sql
SELECT r.*, n.name, n.population, n.housing_age_median_years, n.avg_pipe_age_years
FROM dim_risk_scores r
JOIN dim_neighbourhood n ON r.neighbourhood_id = n.neighbourhood_id
WHERE n.name = '{neighbourhood}'
  AND r.score_date = (SELECT MAX(score_date) FROM dim_risk_scores)
```

**Break history (last 5 years):**
```sql
SELECT DATE_TRUNC('year', date) AS year, COUNT(*) AS breaks, AVG(repair_cost) AS avg_cost
FROM fact_breaks
WHERE neighbourhood = '{neighbourhood}'
  AND date >= CURRENT_DATE - INTERVAL '5 years'
GROUP BY 1 ORDER BY 1
```

**311 complaint trend (last 12 weeks):**
```sql
SELECT
  DATE_TRUNC('week', date) AS week,
  subcategory,
  COUNT(*) AS requests
FROM fact_311_requests
WHERE neighbourhood = '{neighbourhood}'
  AND subcategory IN ('Water pressure low', 'Water discolouration', 'Wet pavement / possible leak', 'Water service disruption')
  AND date >= CURRENT_DATE - INTERVAL '12 weeks'
GROUP BY 1, 2
ORDER BY 1, 3 DESC
```

**Freeze-thaw exposure (last 90 days):**
```sql
SELECT COUNT(*) AS freeze_thaw_days, AVG(min_temp_c) AS avg_low
FROM fact_weather
WHERE date >= CURRENT_DATE - INTERVAL '90 days'
  AND freeze_thaw_event = TRUE
```

**Comparison to city average:**
```sql
SELECT
  AVG(composite_risk_score) AS city_avg,
  PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY composite_risk_score) AS p90
FROM dim_risk_scores
WHERE score_date = (SELECT MAX(score_date) FROM dim_risk_scores)
```

### 3. Synthesize findings

Before writing the report, identify:
- The **primary risk driver** (which sub-score is highest and why)
- The **early warning pattern** (is complaint velocity rising ahead of a potential break?)
- The **freeze-thaw exposure** context (has this winter been unusually high?)
- How this neighbourhood compares to the **city average and P90**
- The **trend** (improving, stable, or deteriorating over the last 3 score cycles?)

### 4. Write and save the report

Save to `reports/{neighbourhood-slug}-{YYYY-MM-DD}.md`.

Use this structure:

```markdown
# Risk Brief: {Neighbourhood}

**Date:** {YYYY-MM-DD}
**Ward:** {ward}
**Composite Risk Score:** {score}/10
**Alert Status:** {Normal | Elevated | Warning | Critical}
**Compared to city:** {above/below} average ({city_avg}/10), {percentile}th percentile

---

## Risk Score Breakdown

| Factor | Score | Weight | Contribution |
|--------|-------|--------|-------------|
| Freeze-thaw exposure | {score} | 35% | {contribution} |
| 311 complaint velocity | {score} | 40% | {contribution} |
| Pipe age | {score} | 25% | {contribution} |
| **Composite** | **{total}** | | |

---

## Key Findings

{2–4 bullet points. Lead with the most non-obvious finding. What does linking these datasets reveal that no single source would show?}

---

## Break History (5 Years)

| Year | Recorded Breaks | Avg Repair Cost |
|------|----------------|-----------------|
{table rows}

---

## Early Warning Signals

{Describe the 311 complaint trend over the last 12 weeks. Is there a rising pattern in the predictive categories? How many weeks until a break would be expected based on historical lag?}

---

## Freeze-Thaw Context

{X freeze-thaw events in the last 90 days vs. historical average. Context on whether this winter has been unusually stressful for infrastructure.}

---

## Recommendation

**{One clear sentence: what should happen next and why.}**

{1–2 sentences of supporting reasoning.}
```

### 5. Confirm and offer next steps

After saving, tell the user the report path and offer:
- Run a report for the next highest-risk neighbourhood
- Query for more detail on any specific finding
- Compare this neighbourhood to a similar one
