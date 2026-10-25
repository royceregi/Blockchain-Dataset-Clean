# Property Database (PostgreSQL + ETL)

PropGuard AI property database: load cleaned CSVs into **`staging.*`**, transform into the **16-table model from `1.txt`** in **`main.*`**.

Wide CSV column spec: [`../cleaner.md`](../cleaner.md). Table list: [`../1.txt`](../1.txt).

```
preprocessing/data/cleaned/*.csv
        │  copy/symlink into data/cleaned/
    ▼
   staging.*  (TEXT columns, safe to truncate)
        │
        ▼
   main.*     (typed tables from 1.txt — query these from app/API)
        │
        ▼
   public.*   (agent-facing views over main.*)
```

## Schemas

| Schema | Role |
|--------|------|
| `staging` | Raw cleaned CSV ingest (all TEXT) |
| `core` | Optional legacy/system schema (`sql/03_normalized_tables.sql`) |
| `main` | Application dataset — 16 tables from `1.txt` |
| `public` | Views over `main.*` |

## Hash policy

- If a hash already exists in cleaned data (`document_hash`, `tx_hash`, `password_hash`, …), **keep it**.
- Otherwise store the **plain** value (e.g. UAE NIC in `nic_hash`) — hash later in the app.
- ETL does **not** invent new SHA-256 hashes.

## Data lifecycle

| Category | Tables | Source |
|----------|--------|--------|
| **A — ETL from CSV** | `properties`, `property_transactions`, `transaction_types`, `transaction_parties`, `property_ownership_history`, `property_documents`, `registration_details`, `blockchain_transactions`, `locations`, stakeholder `users` | Merged transactions + enrichment + ledger + stakeholders |
| **B — Seeded system users** | `users` (`SYS*`) | ETL system seeds / `sql/07_seed_users.sql` |
| **C — Runtime** | `risk_assessments`, `risk_indicators`, `agent_runs` | Empty at bootstrap |
| **C — Post-ETL analytics** | `transaction_features` | Computed during ETL |
| **C — IR baseline** | `query_logs`, `query_retrievals` | `query_logs_cleaned.csv` |

## Source CSV files

| File | Staging | Main |
|------|---------|------|
| `transactions_cleaned.csv` | `staging.transactions` | Merged → txs, properties, … |
| `property_enriched_cleaned.csv` | `staging.property_enriched` | Merged on `transaction_id` |
| `blockchain_ledger_cleaned.csv` | `staging.blockchain` | `main.blockchain_transactions` |
| `query_logs_cleaned.csv` | `staging.query_logs` | `main.query_logs` + `query_retrievals` |
| `users_stakeholders_cleaned.csv` | `staging.users` | `main.users` (plain NIC; existing password hashes kept) |

## Bootstrap (full pipeline)

```bash
cd property-database

psql -U postgres -h localhost -f sql/01_create_db.sql
psql -U postgres -h localhost -d property_db -f sql/02_staging_tables.sql
psql -U postgres -h localhost -d property_db -f sql/08_main_tables.sql
# optional: also create legacy core
# psql -U postgres -h localhost -d property_db -f sql/03_normalized_tables.sql
psql -U postgres -h localhost -d property_db -f sql/07_seed_users.sql

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # if needed

python etl/load_staging.py
python etl/run_etl.py

psql -U postgres -h localhost -d property_db -f sql/04_indexes.sql
psql -U postgres -h localhost -d property_db -f sql/05_views.sql
psql -U postgres -h localhost -d property_db -f sql/06_verification.sql
```

## Demo login accounts

Password for all demo accounts: **`PropGuardDemo2024!`**

| user_id | username | role |
|---------|----------|------|
| SYS000001 | superadmin | SUPER_ADMIN |
| SYS000002 | landregistry | LAND_REGISTRY |
| SYS000003 | realestate | REAL_ESTATE_COMPANY |
| SYS000004 | publicuser | PUBLIC_USER |

## ETL rules

1. **Merge, don't duplicate** — `staging.transactions` + `staging.property_enriched` on `transaction_id`.
2. **Canonical hashes** — existing `blockchain_transaction_hash` → `tx_hash`, etc.; no re-hashing.
3. **Query log splitting** — `retrieved_transaction_ids` → `main.query_retrievals` rows.
4. **Users** — system `SYS*` + cleaned stakeholders in `main.users`; parties link by `user_id` when present.
5. **Owners** — `properties.current_owner_id` set from latest enriched `owner_id` when that user exists.

## Views (`public`, over `main.*`)

| View | Purpose |
|------|---------|
| `v_current_ownership` | Property → current owner |
| `v_property_full_history` | Tx + ownership timeline |
| `v_transaction_with_parties_and_docs` | Parties, fees, document preview |
| `v_blockchain_verification` | Tx ↔ chain ↔ document hash |
| `v_risk_summary` | Risk assessments + indicator counts |
