# Blockchain Property Records

Two-stage project: clean Dubai land-registry CSVs into mandatory tables, then load them into a 12-table PostgreSQL schema for blockchain / multi-agent work.

```
cleaner.md  (mandatory column spec)
        │
        ▼
preprocessing/          raw → cleaned → finalized CSVs
        │
        ▼
property-database/      staging → 12 normalized Postgres tables
```

## Layout

| Path | Role |
|------|------|
| [`cleaner.md`](cleaner.md) | Required columns for the four finalized CSVs (what each field means) |
| [`preprocessing/`](preprocessing/) | Profile, clean, feature-engineer, and emit CSVs |
| [`property-database/`](property-database/) | PostgreSQL schema + ETL from cleaned CSVs |
| [`property-database/table.md`](property-database/table.md) | The 12 normalized tables, keys, and agent usage |

## Quick start

**1. Preprocessing** (from `preprocessing/`):

```bash
pip install pandas numpy
python scripts/01_profile_data.py
python scripts/02_clean_data.py
python scripts/03_create_features.py
python scripts/04_make_fully_clean_csv.py
```

**2. Database** (from `property-database/`):

Copy cleaned CSVs into `property-database/data/cleaned/`, then follow [`property-database/README.md`](property-database/README.md) to create `property_db` and run ETL.

## Data flow

| Stage | Location | Contents |
|-------|----------|----------|
| Raw | `preprocessing/data/raw/` | Original source CSVs (never modified) |
| Preprocessed | `preprocessing/data/preprocessed/` | Intermediate AI-enriched extracts |
| Cleaned | `preprocessing/data/cleaned/` | Working tables used by ETL |
| Finalized | `preprocessing/data/finalized/` | Four CSVs matching `cleaner.md` |
| Database | `property_db` | 12 normalized tables + views |

## Notes

- Study period for transaction cleaning is **2021-01-01** through **2023-12-31**.
- Large CSVs, virtualenvs, and `.env` files are gitignored. Keep `.env.example` and schema/scripts in git.
- Do not commit `property-database/.env` (database password).
