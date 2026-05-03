# Mode 1 — Fetch Raw Data

## Purpose
Download all raw datasets from the Toronto Open Data CKAN API and organize them into
the project's raw data directory. Handles CSV, Excel, and ZIP file formats.

## Trigger
Run when: starting a fresh pipeline, refreshing data from source, or adding a new dataset.

## Inputs
- Internet access to Toronto Open Data API
- Base URL: `https://ckan0.cf.opendata.inter.prod-toronto.ca`
- Dataset registry (see Configuration below)

## Outputs
- Files downloaded to `data/RawData/<dataset-name>/` for each dataset
- ZIP archives are extracted; the ZIP itself is retained alongside extracted files

## Configuration

### API Endpoint
```
GET {base_url}/api/3/action/package_show?id={dataset_id}
GET {base_url}/api/3/action/resource_show?id={resource_id}
```

### Dataset Registry
| Key | CKAN Package ID |
|-----|----------------|
| `wardprofile` | `ward-profiles-25-ward-model` |
| `neighbourhoods` | `neighbourhoods` |
| `watermains` | `watermains` |
| `watermainbreaks` | `watermain-breaks` |
| `311` | `311-service-requests-customer-initiated` |
| `climate` | `current-and-future-climate` |

---

## Step-by-Step Logic

### Step 1: For each dataset in the registry

1. Call the CKAN package_show endpoint with the dataset's package ID.
2. Check `response["success"]`. If False, log an error and skip to the next dataset.
3. Extract the dataset name from `response["result"]["name"]`.
4. Create directory: `data/RawData/<dataset-name>/` if it does not exist.

### Step 2: For each resource in the dataset

1. Skip any resource where `datastore_active == True` (these are API-served, not files).
2. For remaining resources, call resource_show to get file metadata:
   - `url`: download URL
   - `format`: file format string (e.g., "CSV", "XLSX", "ZIP")
   - `name`: filename

### Step 3: Download by format

**ZIP files:**
1. Download the file to `data/RawData/<dataset-name>/<filename>.zip`.
2. Open with `zipfile.ZipFile` and extract all contents to the same directory.
3. Record each extracted filename in the file's metadata.

**CSV files:**
1. Download and write to `data/RawData/<dataset-name>/<filename>.csv`.

**XLS / XLSX files:**
1. Download and write to `data/RawData/<dataset-name>/<filename>.xlsx`.

**Any other format:**
1. Log a warning and skip. Do not attempt to download.

### Step 4: Return / report
After all datasets are processed, report:
- How many datasets were fetched
- How many files were downloaded per dataset
- Any datasets or resources that were skipped or failed

---

## Error Handling

| Scenario | Action |
|----------|--------|
| API returns `success: false` | Log error, skip dataset, continue |
| HTTP download fails (non-200) | Log error with status code, skip file |
| ZIP extraction fails | Log error, leave partial ZIP on disk |
| Unsupported file format | Log warning, skip |

---

## Key Implementation Notes

- Resources with `datastore_active=True` are excluded — they are live API tables, not static files.
- The dataset name used for folder creation comes from the API response (`result.name`), not the registry key.
- File paths use the dataset name from the API as the folder name (e.g., `ward-profiles-25-ward-model/`).
- Existing files are overwritten on re-run (no incremental check implemented).

---

## Source Reference
`pipeline/FetchRawData.ipynb`
