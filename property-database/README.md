# Property Database (PostgreSQL + ETL)

Load cleaned CSVs into **staging** tables, then transform them into the **12-table** relational schema.

Schema and why each table exists: [`table.md`](table.md).  
Wide CSV column spec: [`../cleaner.md`](../cleaner.md).

```
preprocessing/data/cleaned/*.csv
        │  copy into data/cleaned/
        ▼
   staging_* tables
        │
        ▼
  12 normalized tables
```

## Final 12 tables

| # | Table | Role |
|---|--------|------|
| 1 | `properties` | Core property master |
| 2 | `property_ownership_history` | Ownership timeline |
| 3 | `property_transactions` | Sales / transfers / registrations |
| 4 | `transaction_types` | Lookup for procedure / type names |
| 5 | `property_classifications` | Type, subtype, usage, group, zone |
| 6 | `transaction_parties` | Owner, seller, notary, witnesses |
| 7 | `registration_details` | Fees and registration metadata |
| 8 | `property_documents` | Deed text + hash (NLP / integrity) |
| 9 | `blockchain_transactions` | Ledger facts |
| 10 | `users` | Stakeholders / auth |
| 11 | `query_logs` | IR / security query logs |
| 12 | `locations` | Area, GPS, landmarks |

Column details: see `table.md` (types adapted to real CSV IDs: `TEXT` for `user_id`, `transaction_id`, `property_id`).

## Source files

Copy from `../preprocessing/data/cleaned/` into `data/cleaned/` (or keep a local copy).

| File | Feeds |
|------|--------|
| `users_stakeholders_cleaned.csv` | `users` |
| `property_enriched_cleaned.csv` | **primary** → properties, transactions, ownership, parties, docs, classifications, locations, registration |
| `transactions_cleaned.csv` | staging only (cross-check / future use) |
| `blockchain_ledger_cleaned.csv` | `blockchain_transactions` |
| `query_logs_cleaned.csv` | `query_logs` |
| `property_features_ready.csv` | optional (not loaded by default) |

## Project layout

```
property-database/
├── data/cleaned/          # cleaned CSVs (gitignored)
├── sql/
│   ├── 01_create_db.sql
│   ├── 02_staging_tables.sql
│   ├── 03_normalized_tables.sql
│   ├── 04_indexes.sql
│   └── 05_views.sql
├── etl/
│   ├── db.py
│   ├── utils.py
│   ├── load_staging.py
│   ├── transform.py
│   └── run_etl.py
├── .env.example
├── requirements.txt
├── table.md
└── README.md
```

## What to run

All commands assume you are in this directory:

```bash
cd property-database
```

### 0) Install PostgreSQL (if needed)

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

Set a password for the `postgres` role if you have not already:

```bash
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'YOUR_PASSWORD';"
```

### 1) Create the database

```bash
sudo -u postgres psql -f sql/01_create_db.sql
```

If peer auth fails, use:

```bash
psql -U postgres -h localhost -f sql/01_create_db.sql
```

### 2) Create staging + final tables

```bash
psql -U postgres -h localhost -d property_db -f sql/02_staging_tables.sql
psql -U postgres -h localhost -d property_db -f sql/03_normalized_tables.sql
```

You will be prompted for the postgres password.

### 3) Python environment + `.env`

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` so it matches your password:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/property_db
```

### 4) Load CSVs → staging

```bash
source .venv/bin/activate
python etl/load_staging.py
```

Expected: ~50k users, ~91k enriched rows, ~236k transactions, ~236k blockchain rows, ~50k query logs (exact counts depend on files).

### 5) Transform staging → 12 final tables

```bash
python etl/run_etl.py
```

This truncates the 12 final tables and reloads them in FK-safe order inside one DB transaction.

### 6) Indexes + views (after data load)

```bash
psql -U postgres -h localhost -d property_db -f sql/04_indexes.sql
psql -U postgres -h localhost -d property_db -f sql/05_views.sql
```

### 7) Quick validation

```bash
psql -U postgres -h localhost -d property_db
```

Then run:

```sql
SELECT 'users' AS t, COUNT(*) FROM users
UNION ALL SELECT 'properties', COUNT(*) FROM properties
UNION ALL SELECT 'locations', COUNT(*) FROM locations
UNION ALL SELECT 'transaction_types', COUNT(*) FROM transaction_types
UNION ALL SELECT 'property_transactions', COUNT(*) FROM property_transactions
UNION ALL SELECT 'property_ownership_history', COUNT(*) FROM property_ownership_history
UNION ALL SELECT 'property_classifications', COUNT(*) FROM property_classifications
UNION ALL SELECT 'transaction_parties', COUNT(*) FROM transaction_parties
UNION ALL SELECT 'registration_details', COUNT(*) FROM registration_details
UNION ALL SELECT 'property_documents', COUNT(*) FROM property_documents
UNION ALL SELECT 'blockchain_transactions', COUNT(*) FROM blockchain_transactions
UNION ALL SELECT 'query_logs', COUNT(*) FROM query_logs
ORDER BY 1;

-- Current owners
SELECT * FROM v_current_ownership LIMIT 20;

-- Blockchain + document check
SELECT * FROM v_blockchain_verification LIMIT 20;
```

## Design notes

1. **Primary source** — `property_enriched_cleaned.csv` drives almost all operational facts.
2. **IDs** — `user_id` / `transaction_id` are text (`USER000001`, `1-102-2021-1`). `property_id` is stored as text after normalizing scientific notation.
3. **PII** — raw NIC is hashed (`sha256`) into `users.nic_hash`; not stored in clear in the final `users` table.
4. **Current owner** — also stored on `properties.current_owner_id` for convenience; timeline truth lives in `property_ownership_history` where `ownership_end_date IS NULL`.
5. **Parties** — Owner / Seller / Notary / Witness rows go into `transaction_parties` (not separate columns).
6. **Blockchain** — loaded from `blockchain_ledger_cleaned.csv`; missing links stay `NULL` rather than inventing hashes.
7. **Re-runs** — safe to re-run `load_staging.py` then `run_etl.py` (staging truncate + final truncate).

## Useful views

| View | Purpose |
|------|---------|
| `v_current_ownership` | Property → current owner |
| `v_property_full_history` | Timeline of txs + ownership |
| `v_transaction_with_parties_and_docs` | Parties, fees, document preview |
| `v_blockchain_verification` | Tx ↔ chain ↔ document hash |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `DATABASE_URL missing` | Create `.env` from `.env.example` |
| `peer authentication failed` | Use `-h localhost` with password auth |
| `relation staging_users does not exist` | Run `sql/02_staging_tables.sql` first |
| `ForeignKeyViolation` | Re-run `sql/03_normalized_tables.sql` then `python etl/run_etl.py` |
| Password auth errors | Confirm postgres password and `DATABASE_URL` |
| Slow load | Normal for ~90k+ enriched rows; wait for completion |
| Missing CSVs | Copy files from `../preprocessing/data/cleaned/` into `data/cleaned/` |

## Full reset (optional)

```bash
psql -U postgres -h localhost -d property_db -f sql/02_staging_tables.sql
psql -U postgres -h localhost -d property_db -f sql/03_normalized_tables.sql
python etl/load_staging.py
python etl/run_etl.py
psql -U postgres -h localhost -d property_db -f sql/04_indexes.sql
psql -U postgres -h localhost -d property_db -f sql/05_views.sql
```

### Remove (staging only)

Drop these — they are ETL scratch space, not part of the relational design:

```sql
DROP TABLE IF EXISTS staging_property_features CASCADE;
DROP TABLE IF EXISTS staging_query_logs CASCADE;
DROP TABLE IF EXISTS staging_blockchain CASCADE;
DROP TABLE IF EXISTS staging_transactions CASCADE;
DROP TABLE IF EXISTS staging_property_enriched CASCADE;
DROP TABLE IF EXISTS staging_users CASCADE;
```

### Keep (what to share)

**12 tables:**  
`properties`, `property_ownership_history`, `property_transactions`, `transaction_types`, `property_classifications`, `transaction_parties`, `registration_details`, `property_documents`, `blockchain_transactions`, `users`, `query_logs`, `locations`

**Optional but useful:** the 4 views  
`v_current_ownership`, `v_property_full_history`, `v_transaction_with_parties_and_docs`, `v_blockchain_verification`

### Best way to share with your instructor

Do not hand over a live DB with staging. Export a clean dump of only the final schema:

```bash
pg_dump -U postgres -h localhost -d property_db \
  --no-owner --no-privileges \
  -t properties \
  -t property_ownership_history \
  -t property_transactions \
  -t transaction_types \
  -t property_classifications \
  -t transaction_parties \
  -t registration_details \
  -t property_documents \
  -t blockchain_transactions \
  -t users \
  -t query_logs \
  -t locations \
  -t v_current_ownership \
  -t v_property_full_history \
  -t v_transaction_with_parties_and_docs \
  -t v_blockchain_verification \
  -F c -f property_db_relational.dump
```

Or a plain SQL file:

```bash
pg_dump -U postgres -h localhost -d property_db \
  --no-owner --no-privileges \
  -t properties -t property_ownership_history -t property_transactions \
  -t transaction_types -t property_classifications -t transaction_parties \
  -t registration_details -t property_documents -t blockchain_transactions \
  -t users -t query_logs -t locations \
  -f property_db_relational.sql
```

Restore with `pg_restore` (custom dump) or `psql -f` (SQL file).

Do not share `.env` (password). A dump plus `table.md` is enough.
