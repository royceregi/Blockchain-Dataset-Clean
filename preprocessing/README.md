# Preprocessing

Profile raw Dubai property CSVs, clean them, add features, and write the four finalized datasets.

Column meanings: [`../cleaner.md`](../cleaner.md).  
How those columns become 12 Postgres tables: [`../property-database/table.md`](../property-database/table.md).

Run all commands from this folder (`preprocessing/`).

## Layout

```
preprocessing/
├── data/
│   ├── raw/            # original sources (never modified)
│   ├── preprocessed/   # intermediate AI-enriched extracts
│   ├── cleaned/        # working tables for ETL
│   └── finalized/      # mandatory columns from cleaner.md
├── reports/            # profiling and cleaning summaries
├── scripts/
│   ├── 01_profile_data.py
│   ├── 02_clean_data.py
│   ├── 03_create_features.py
│   ├── 04_make_fully_clean_csv.py
│   └── schemas.py      # column maps for the four finalized tables
└── README.md
```

## Install

```bash
pip install pandas numpy
```

## Run the pipeline

```bash
python scripts/01_profile_data.py
python scripts/02_clean_data.py
python scripts/03_create_features.py
python scripts/04_make_fully_clean_csv.py
```

| Script | What it does |
|--------|----------------|
| `01_profile_data.py` | Profiles every CSV in `data/raw/` → `reports/` |
| `02_clean_data.py` | Dedupes, dates, numerics, text cleanup → `data/cleaned/` |
| `03_create_features.py` | Time features, hashes, prototype blockchain fields |
| `04_make_fully_clean_csv.py` | Maps to `cleaner.md` columns → `data/finalized/` |

## Finalized outputs (`data/finalized/`)

| File | Rows (approx.) | Role |
|------|----------------|------|
| `property_land_title_records.csv` | 91,037 | Core title / property records (Table 1) |
| `blockchain_transaction_ledger.csv` | 91,037 | On-chain style ledger linked by `Property_ID` (Table 2) |
| `users_stakeholders.csv` | 50,000 | Users, wallets, KYC (Table 3) |
| `query_interaction_logs.csv` | 50,000 | Agent query logs (Table 4) |
| `finalized_manifest.csv` | — | Row/column/missing-value summary |

CSV-safe names are used where `cleaner.md` had slashes (for example `Land_Extent_Area`, `Name_Contact`, `Auth_Credentials_Hashed`).

## Cleaned outputs (`data/cleaned/`)

These files are the ETL input for [`../property-database/`](../property-database/). Copy them to `property-database/data/cleaned/` before loading Postgres.

| File | Feeds | Notes |
|------|--------|--------|
| `users_stakeholders_cleaned.csv` | `users` | Roles, contact, hashed password, KYC |
| `property_enriched_cleaned.csv` | Primary operational facts | Enriched titles, owners, GPS, deeds, fees |
| `transactions_cleaned.csv` | Staging / cross-check | 2021–2023 DLD transactions + generated `property_id` |
| `blockchain_ledger_cleaned.csv` | `blockchain_transactions` | Prototype hashes, wallets, status |
| `query_logs_cleaned.csv` | `query_logs` | IR queries (no source timestamp column) |
| `property_features_ready.csv` | Optional | Same as enriched plus `registration_quarter` |

## Reports (`reports/`)

- `raw_profile_summary.csv` — rows, columns, date range per raw file
- `cleaning_summary.csv` — drop counts and final sizes
- `missing_values_*.csv` — null rates per source file

## Important notes

- Raw `Transactions.csv` is never overwritten.
- Study period is **2021-01-01** through **2023-12-31**.
- `Property_ID` is a project grouping key, not a legal title ID.
- Blockchain hashes and contract addresses are **prototype** fields.
- PII such as `Owner_NIC` is kept in finalized CSVs for downstream hashing (the database ETL hashes NIC into `users.nic_hash`).
- Primary transaction source: `data/raw/Transactions.csv`. Enriched Dubai fields: `dubai_property_MERGED_enriched.csv`.
