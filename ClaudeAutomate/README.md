# ClaudeAutomate — Urban Infrastructure Risk Toronto

This folder defines the agentic workflow modes for automating this project with Claude.
Each mode corresponds to a distinct stage of the pipeline and contains the full instructions
Claude would follow to execute that stage autonomously.

---

## Mode Overview

| Mode | File | Purpose | Status |
|------|------|---------|--------|
| 1 | `Mode_1_Fetch.md` | Download all raw datasets from Toronto Open Data | Implemented |
| 2 | `Mode_2_Inventory.md` | Profile and document all raw datasets | Implemented |
| 3 | `Mode_3_Transform_WardProfiles.md` | Parse and split ward profile Excel workbooks | Implemented (manual pre-processing done) |
| 4 | `Mode_4_Transform_Core.md` | Clean and standardize all other raw datasets | Planned |
| 5 | `Mode_5_Load.md` | Load transformed data into DuckDB | Planned |
| 6 | `Mode_6_RiskScore.md` | Compute composite risk scores per neighbourhood | Planned |
| 7 | `Mode_7_Report.md` | Generate risk brief markdown reports | Planned |

---

## Execution Order

```
Mode 1 (Fetch)
    ↓
Mode 2 (Inventory)          ← Optional; run to audit new data
    ↓
Mode 3 (Ward Profiles)
Mode 4 (Core Transforms)    ← Modes 3 & 4 are independent, can run in parallel
    ↓
Mode 5 (Load → DuckDB)
    ↓
Mode 6 (Risk Scores)
    ↓
Mode 7 (Reports)
```

---

## Shared Conventions

- **Project root**: the directory containing `CLAUDE.md`, `data/`, `pipeline/`, `src/`
- **Raw data path**: `data/RawData/<dataset-name>/`
- **Database**: `data/infrastructure.db` (DuckDB)
- **Reports output**: `reports/<neighbourhood-slug>-<YYYY-MM-DD>.md`
- **Python environment**: Anaconda (`C:/Users/1/anaconda3/python.exe`), kernel `TestML`
- **Utility modules**: `src/utils/data_loader.py`, `src/utils/data_summaries.py`
- Never modify any file under `data/RawData/`

---

## How to Invoke a Mode

When asking Claude to run a mode, say:

> "Run Mode 1" or "Execute the Fetch mode"

Claude will follow the instructions in the corresponding mode file exactly.
