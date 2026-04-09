# Mode: Query — Natural Language Data Analysis

The user has asked a question about the infrastructure data. Your job is to answer it accurately using the database, not from memory or assumption.

---

## Process

### 1. Understand the question

Identify what the user is asking for:
- A specific neighbourhood or ward?
- A time range?
- A comparison between areas?
- A trend or pattern?
- A "why" question (root cause)?

If the question is ambiguous, ask one clarifying question before running anything.

### 2. Plan the SQL

Think through which tables you need:
- Break history → `fact_breaks`
- 311 complaint patterns → `fact_311_requests`
- Weather correlation → `fact_weather`
- Current risk scores → `dim_risk_scores`
- Neighbourhood context → `dim_neighbourhood`

Write a CTE-based SQL query. Use window functions where relevant (e.g., rolling averages, rank by risk score, lag for trend detection).

### 3. Execute

Run the query using the Bash tool:

```bash
python -c "
import duckdb
import pandas as pd
con = duckdb.connect('data/infrastructure.db')
df = con.execute('''
  YOUR SQL HERE
''').df()
print(df.to_string(index=False))
"
```

If the query errors, read the error, fix the SQL, and retry once. If it errors again, show the user the SQL and error and ask for guidance.

### 4. Interpret

Do not just return the raw table. Explain:
- What the numbers mean in plain English
- What's surprising or non-obvious about the result
- If there's a follow-up question worth asking (e.g., "This neighbourhood scores high on complaint velocity — want me to break down which complaint types are driving it?")

---

## Example questions and the insight to surface

| Question | What to look for |
|----------|-----------------|
| "Which neighbourhoods are highest risk?" | Top composite scores + what's driving each |
| "Has anything changed since last month?" | Compare current scores to previous monitor run |
| "Why does [X] keep having breaks?" | Pipe age + freeze-thaw exposure + complaint history |
| "Where should the city act first?" | Highest score + longest time since last break (overdue) |
| "Is the 311 data actually predictive?" | Lag correlation between complaint spike and break date |

---

## Output format

Answer conversationally. Include:
- The direct answer in the first sentence
- Supporting data (can be a small table if helpful)
- One insight the user probably didn't expect
- An optional follow-up question if there's more to explore

Keep it tight — this is an analytical tool, not a report generator. Use `report` mode for full briefs.
