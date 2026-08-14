# Relational schema (12 tables)

Wide finalized CSVs are useful for agents. They are a poor production database: owners, fees, deeds, and chain facts would be duplicated on every row.

This project loads **cleaned** CSVs into PostgreSQL and splits them into **12 tables**. Runnable SQL is in `sql/`; ETL is in `etl/`. Follow [`README.md`](README.md) to create `property_db` and load data.

Source spec for the four wide files: [`../cleaner.md`](../cleaner.md).

## ID types (important)

The original sketch used `BIGINT` keys. The cleaned files use **text IDs**, so the live schema does too:

| Entity | Example | Column type |
|--------|---------|-------------|
| User | `USER000001` | `TEXT` |
| Property | large hash / scientific-notation string | `TEXT` |
| Transaction | `1-102-2021-1` | `TEXT` |
| Query | `QRY000001` | `TEXT` |

NIC is **hashed** (`sha256`) into `users.nic_hash`. It is not stored in clear in the final `users` table.

---

## Table list

```text
1. properties
2. property_ownership_history
3. property_transactions
4. transaction_types
5. property_classifications
6. transaction_parties
7. registration_details
8. property_documents
9. blockchain_transactions
10. users
11. query_logs
12. locations
```

`properties` is the hub. Transactions hang off it. Parties, fees, documents, and chain rows hang off transactions. Users appear as owners, parties, and query authors.

```text
users ──────────────────────────────► query_logs
  │
  ├─ current_owner_id ──────────────► properties
  │                                      │
  │                                      ├─► locations
  │                                      ├─► property_ownership_history
  │                                      ├─► property_classifications
  │                                      ├─► property_documents
  │                                      └─► property_transactions
  │                                                │
  │                                                ├─► transaction_types
  │                                                ├─► transaction_parties ──► users
  │                                                ├─► registration_details
  │                                                └─► blockchain_transactions
```

---

## 1. `properties`

One row per property (the asset), not per sale.

| Column | Type | Notes |
|--------|------|--------|
| `property_id` | TEXT PK | Grouping key from preprocessing |
| `title_deed_number` | VARCHAR | Deed reference |
| `property_name` | VARCHAR | Display name |
| `address` | TEXT | Combined address |
| `district` | VARCHAR | Area / district |
| `city` | VARCHAR | Default `Dubai` |
| `latitude` / `longitude` | DECIMAL | GPS |
| `land_area` | DECIMAL | Size |
| `area_unit` | VARCHAR | Default `sqm` |
| `land_type` | VARCHAR | Zone / land class |
| `survey_plan_number` | VARCHAR | Survey ref |
| `current_owner_id` | TEXT FK → `users` | Convenience pointer |
| `current_usage_type` | VARCHAR | Active use |
| `current_subtype` | VARCHAR | Fine type |
| `current_value` | DECIMAL | Latest value (AED) |
| `legal_status` | VARCHAR | Clear, Mortgaged, … |
| `verification_status` | VARCHAR | Verified / Pending / Rejected |
| `encumbrances` | TEXT | Liens, caveats |
| `boundary_north` … `_west` | TEXT | Spatial markers |
| `created_at` / `updated_at` | TIMESTAMP | Audit |

Current owner on this table is a shortcut. The **timeline of truth** is `property_ownership_history` where `ownership_end_date IS NULL`.

---

## 2. `property_ownership_history`

Provenance and fraud checks need a chain of owners, not a single name.

| Column | Type | Notes |
|--------|------|--------|
| `ownership_id` | BIGSERIAL PK | |
| `property_id` | TEXT FK | |
| `owner_id` | TEXT FK → `users` | |
| `ownership_start_date` | DATE | |
| `ownership_end_date` | DATE | `NULL` = current |
| `ownership_type` | VARCHAR | |
| `transaction_id` | TEXT FK | Transfer that started this period |
| `ownership_status` | VARCHAR | |
| `recorded_at` | TIMESTAMP | |

Example: Owner A 2021–2022, Owner B 2022–present.

---

## 3. `property_transactions`

Every sale, transfer, or registration is one row. This is the main fact table.

| Column | Type | Notes |
|--------|------|--------|
| `transaction_id` | TEXT PK | DLD-style ID |
| `property_id` | TEXT FK | |
| `transaction_type_id` | INT FK → `transaction_types` | |
| `transaction_group` | VARCHAR | e.g. Sales |
| `registration_type` | VARCHAR | Existing / off-plan |
| `procedure_name` | VARCHAR | Sell, transfer, … |
| `transaction_date` | DATE | |
| `transaction_time` | TIME | |
| `transaction_datetime` | TIMESTAMP | Canonical timestamp |
| `year` / `month` / `quarter` | INT | Derived (no separate date dimension) |
| `day_of_week` | VARCHAR | |
| `day_of_month` | INT | |
| `current_value` / `previous_value` | DECIMAL | |
| `transaction_value` | DECIMAL | |
| `value_change_pct` | DECIMAL | |
| `procedure_area` | DECIMAL | |
| `meter_sale_price` | DECIMAL | |
| `currency` | VARCHAR | Default `AED` |
| `rooms` | VARCHAR | |
| `has_parking` | BOOLEAN | |
| `status` | VARCHAR | Default `Completed` |

Study window in preprocessing is **2021–2023**.

---

## 4. `transaction_types`

Lookup so type names are not repeated as free text on every fact row.

| Column | Type | Notes |
|--------|------|--------|
| `transaction_type_id` | SERIAL PK | |
| `transaction_type_name` | VARCHAR UNIQUE | Registration, Transfer, Sale, … |
| `description` | TEXT | |

---

## 5. `property_classifications`

Current vs previous usage/subtype, group, zone — stored per property (and optionally per transaction) instead of dozens of columns on `properties`.

| Column | Type | Notes |
|--------|------|--------|
| `classification_id` | BIGSERIAL PK | |
| `property_id` | TEXT FK | |
| `transaction_id` | TEXT FK | Optional snapshot at that tx |
| `property_group` | VARCHAR | |
| `property_type` | VARCHAR | Land, Villa, Apartment, … |
| `previous_subtype` / `current_subtype` | VARCHAR | |
| `previous_usage_type` / `current_usage_type` | VARCHAR | |
| `registration_type` | VARCHAR | |
| `land_type` | VARCHAR | |
| `land_use_zone` | VARCHAR | |
| `effective_date` | DATE | |

---

## 6. `transaction_parties`

Buyer, seller, owner, witness, notary, registrar — one table, many roles. Avoids `buyer_id`, `seller_id`, `witness1_id`, …

| Column | Type | Notes |
|--------|------|--------|
| `transaction_party_id` | BIGSERIAL PK | |
| `transaction_id` | TEXT FK | |
| `user_id` | TEXT FK → `users` | Null if only a name is known |
| `party_name` | VARCHAR | Display name from the CSV |
| `role` | VARCHAR | Owner, Seller, Notary, Witness, … |
| `is_primary` | BOOLEAN | |

Unique on `(transaction_id, role, party_name)`.

---

## 7. `registration_details`

Fees and taxes for a registration. People (witnesses, notary) stay in `transaction_parties`.

| Column | Type | Notes |
|--------|------|--------|
| `registration_id` | BIGSERIAL PK | |
| `transaction_id` | TEXT UNIQUE FK | One fee row per tx |
| `registration_number` | VARCHAR | |
| `registration_date` | DATE | |
| `registration_fee` | DECIMAL | |
| `tax_amount` | DECIMAL | Stamp duty / tax |
| `other_fee` | DECIMAL | e.g. trustee office |
| `total_amount_paid` | DECIMAL | |
| `currency` | VARCHAR | Default `AED` |
| `registration_status` | VARCHAR | |

---

## 8. `property_documents`

NLP (deed text) and integrity (hash mirrored on-chain).

| Column | Type | Notes |
|--------|------|--------|
| `document_id` | BIGSERIAL PK | |
| `property_id` | TEXT FK | |
| `transaction_id` | TEXT FK | |
| `document_type` | VARCHAR | Default `Title Deed` |
| `document_number` | VARCHAR | |
| `document_text` | TEXT | Unstructured deed |
| `document_hash` | VARCHAR | Tamper-evident hash |
| `document_url` | TEXT | Optional |
| `issued_date` | DATE | |
| `verification_status` | VARCHAR | |

---

## 9. `blockchain_transactions`

Prototype ledger row linked to a property transaction.

| Column | Type | Notes |
|--------|------|--------|
| `blockchain_tx_id` | BIGSERIAL PK | |
| `transaction_id` | TEXT FK | Off-chain fact |
| `property_id` | TEXT FK | |
| `tx_hash` | VARCHAR UNIQUE | |
| `previous_hash` | VARCHAR | Chain pointer |
| `property_hash` | VARCHAR | |
| `block_number` | BIGINT | |
| `block_timestamp` | TIMESTAMP | |
| `from_wallet` / `to_wallet` | VARCHAR | |
| `transaction_type` | VARCHAR | |
| `transaction_value_aed` | DECIMAL | |
| `smart_contract_address` | VARCHAR | Prototype address if not deployed |
| `digital_signature` | TEXT | |
| `transaction_status` | VARCHAR | |
| `consensus_verification` | TEXT | Stored as text (not boolean) |
| `gas_fee_aed` | DECIMAL | |

Missing chain links are left `NULL`. ETL does not invent hashes when the cleaned ledger has none.

---

## 10. `users`

Authentication and RBAC. Never store a plaintext password.

| Column | Type | Notes |
|--------|------|--------|
| `user_id` | TEXT PK | `USER…` |
| `username` | VARCHAR UNIQUE | |
| `name` | VARCHAR | |
| `email` | VARCHAR | |
| `contact` | VARCHAR | Phone |
| `role` | VARCHAR | Buyer, Seller, Notary, Agent, Admin, … |
| `wallet_address` | VARCHAR | |
| `password_hash` | TEXT | |
| `nic_hash` | VARCHAR(64) | SHA-256 of NIC |
| `kyc_status` | VARCHAR | |
| `access_level` | VARCHAR | Standard / Elevated, … |
| `mfa_enabled` | BOOLEAN | |
| `is_active` | BOOLEAN | |
| `created_at` / `last_login` | TIMESTAMP | |

---

## 11. `query_logs`

IR evaluation and prompt-injection / access flags.

| Column | Type | Notes |
|--------|------|--------|
| `query_id` | TEXT PK | `QRY…` |
| `user_id` | TEXT FK | |
| `query_text` | TEXT | |
| `log_timestamp` | TIMESTAMP | Source file may lack a timestamp |
| `retrieved_transaction_ids` | TEXT | IDs returned by IR |
| `agent_response` | TEXT | |
| `confidence_score` / `relevance_score` | DECIMAL | |
| `flagged_suspicious` | BOOLEAN | |
| `agent_used` | VARCHAR | |
| `response_time_ms` | INT | |

---

## 12. `locations`

Landmarks and project names without cluttering `properties`. One row per property.

| Column | Type | Notes |
|--------|------|--------|
| `location_id` | BIGSERIAL PK | |
| `property_id` | TEXT UNIQUE FK | |
| `district` / `city` | VARCHAR | |
| `latitude` / `longitude` | DECIMAL | |
| `area_name` / `building_name` | VARCHAR | |
| `project_name` / `master_project` | VARCHAR | |
| `nearest_landmark` / `_metro` / `_mall` | VARCHAR | |

---

## Views (after ETL)

Defined in `sql/05_views.sql`:

| View | Use |
|------|-----|
| `v_current_ownership` | Property → current owner |
| `v_property_full_history` | Timeline of transactions and owners |
| `v_transaction_with_parties_and_docs` | Parties, fees, deed preview |
| `v_blockchain_verification` | Tx ↔ chain ↔ document hash |

Staging tables (`staging_users`, `staging_property_enriched`, …) are ETL scratch space. Drop them before handing over a dump. See the database README for `pg_dump` commands.

---

## Which tables each agent uses

| Agent | Tables |
|-------|--------|
| IR | `properties`, `property_transactions`, `property_ownership_history`, `property_documents`, `locations` |
| Blockchain | `property_transactions`, `blockchain_transactions`, `property_documents` |
| Risk / fraud | `property_transactions`, `property_ownership_history`, `registration_details`, `transaction_parties`, `blockchain_transactions` |
| NLP | `property_documents`, `query_logs`, `properties` |
| Security | `users`, `query_logs` |

---

## Source vs generated fields

The Dubai Land Department CSV has transactions, dates, area, and worth. It does **not** natively include notaries, NIC, deed text, or live chain hashes.

Those fields come from **enriched** project files or are **prototype** values. Say so in the write-up: do not present them as official DLD columns.

## What to implement

All **12 tables above are created** (`sql/03_normalized_tables.sql`). There is no separate `date_dimension`; year/month/quarter live on `property_transactions`.
