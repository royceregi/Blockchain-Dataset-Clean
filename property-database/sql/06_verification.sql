-- PropGuard AI verification queries: row counts, FK integrity, constraints.
-- Run after ETL completes: psql -U postgres -h localhost -d property_db -f sql/06_verification.sql

\echo '=== 1. Row counts (16 main tables) ==='
SELECT 'users' AS table_name, COUNT(*) AS row_count FROM main.users
UNION ALL SELECT 'properties', COUNT(*) FROM main.properties
UNION ALL SELECT 'transaction_types', COUNT(*) FROM main.transaction_types
UNION ALL SELECT 'property_transactions', COUNT(*) FROM main.property_transactions
UNION ALL SELECT 'transaction_parties', COUNT(*) FROM main.transaction_parties
UNION ALL SELECT 'property_ownership_history', COUNT(*) FROM main.property_ownership_history
UNION ALL SELECT 'property_documents', COUNT(*) FROM main.property_documents
UNION ALL SELECT 'registration_details', COUNT(*) FROM main.registration_details
UNION ALL SELECT 'blockchain_transactions', COUNT(*) FROM main.blockchain_transactions
UNION ALL SELECT 'risk_assessments', COUNT(*) FROM main.risk_assessments
UNION ALL SELECT 'risk_indicators', COUNT(*) FROM main.risk_indicators
UNION ALL SELECT 'transaction_features', COUNT(*) FROM main.transaction_features
UNION ALL SELECT 'query_logs', COUNT(*) FROM main.query_logs
UNION ALL SELECT 'query_retrievals', COUNT(*) FROM main.query_retrievals
UNION ALL SELECT 'agent_runs', COUNT(*) FROM main.agent_runs
UNION ALL SELECT 'locations', COUNT(*) FROM main.locations
ORDER BY table_name;

\echo ''
\echo '=== 2. Staging row counts ==='
SELECT 'staging.users' AS table_name, COUNT(*) AS row_count FROM staging.users
UNION ALL SELECT 'staging.property_enriched', COUNT(*) FROM staging.property_enriched
UNION ALL SELECT 'staging.transactions', COUNT(*) FROM staging.transactions
UNION ALL SELECT 'staging.blockchain', COUNT(*) FROM staging.blockchain
UNION ALL SELECT 'staging.query_logs', COUNT(*) FROM staging.query_logs
ORDER BY table_name;

\echo ''
\echo '=== 3. Seeded system users (expect 4 roles) ==='
SELECT user_id, username, role, kyc_status, is_active
FROM main.users
ORDER BY user_id;

\echo ''
\echo '=== 4. Foreign key orphan checks (expect 0 rows each) ==='
SELECT 'property_transactions.property_id' AS fk_check, COUNT(*) AS orphans
FROM main.property_transactions pt
LEFT JOIN main.properties p ON pt.property_id = p.property_id
WHERE p.property_id IS NULL

UNION ALL
SELECT 'transaction_parties.transaction_id', COUNT(*)
FROM main.transaction_parties tp
LEFT JOIN main.property_transactions pt ON tp.transaction_id = pt.transaction_id
WHERE pt.transaction_id IS NULL

UNION ALL
SELECT 'property_ownership_history.property_id', COUNT(*)
FROM main.property_ownership_history oh
LEFT JOIN main.properties p ON oh.property_id = p.property_id
WHERE p.property_id IS NULL

UNION ALL
SELECT 'property_documents.property_id', COUNT(*)
FROM main.property_documents pd
LEFT JOIN main.properties p ON pd.property_id = p.property_id
WHERE pd.property_id IS NOT NULL AND p.property_id IS NULL

UNION ALL
SELECT 'blockchain_transactions.transaction_id', COUNT(*)
FROM main.blockchain_transactions bt
LEFT JOIN main.property_transactions pt ON bt.transaction_id = pt.transaction_id
WHERE bt.transaction_id IS NOT NULL AND pt.transaction_id IS NULL

UNION ALL
SELECT 'transaction_features.transaction_id', COUNT(*)
FROM main.transaction_features tf
LEFT JOIN main.property_transactions pt ON tf.transaction_id = pt.transaction_id
WHERE pt.transaction_id IS NULL

UNION ALL
SELECT 'query_retrievals.query_id', COUNT(*)
FROM main.query_retrievals qr
LEFT JOIN main.query_logs ql ON qr.query_id = ql.query_id
WHERE ql.query_id IS NULL

UNION ALL
SELECT 'transaction_parties.user_id', COUNT(*)
FROM main.transaction_parties tp
LEFT JOIN main.users u ON tp.user_id = u.user_id
WHERE tp.user_id IS NOT NULL AND u.user_id IS NULL;

\echo ''
\echo '=== 5. Unique constraint checks (expect 0 duplicate groups) ==='
SELECT 'properties.title_deed_number' AS constraint_check, COUNT(*) - COUNT(DISTINCT title_deed_number) AS duplicate_count
FROM main.properties WHERE title_deed_number IS NOT NULL

UNION ALL
SELECT 'properties.survey_plan_number', COUNT(*) - COUNT(DISTINCT survey_plan_number)
FROM main.properties WHERE survey_plan_number IS NOT NULL

UNION ALL
SELECT 'blockchain_transactions.tx_hash', COUNT(*) - COUNT(DISTINCT tx_hash)
FROM main.blockchain_transactions

UNION ALL
SELECT 'blockchain_transactions.transaction_id', COUNT(*) - COUNT(DISTINCT transaction_id)
FROM main.blockchain_transactions WHERE transaction_id IS NOT NULL

UNION ALL
SELECT 'registration_details.transaction_id', COUNT(*) - COUNT(DISTINCT transaction_id)
FROM main.registration_details;

\echo ''
\echo '=== 6. Users mix (system seeds + stakeholders) ==='
SELECT
    COUNT(*) AS total_users,
    COUNT(*) FILTER (WHERE role IN ('SUPER_ADMIN', 'LAND_REGISTRY', 'REAL_ESTATE_COMPANY', 'PUBLIC_USER')) AS system_role_count,
    COUNT(*) FILTER (WHERE user_id LIKE 'USER%') AS stakeholder_count,
    COUNT(*) FILTER (WHERE nic_hash IS NOT NULL AND LENGTH(nic_hash) = 64) AS nic_looks_hashed,
    COUNT(*) FILTER (WHERE nic_hash IS NOT NULL AND nic_hash LIKE '784-%') AS nic_plain_uae,
    COUNT(*) FILTER (WHERE password_hash LIKE 'pbkdf2_sha256$%') AS demo_password_count,
    COUNT(*) FILTER (WHERE password_hash IS NULL) AS missing_password_count
FROM main.users;

\echo ''
\echo '=== 7. Merge integrity: one row per transaction_id ==='
SELECT
    (SELECT COUNT(*) FROM main.property_transactions) AS main_transactions,
    (SELECT COUNT(DISTINCT transaction_id) FROM staging.transactions WHERE transaction_id IS NOT NULL) AS staging_tx_distinct,
    (SELECT COUNT(DISTINCT transaction_id) FROM staging.property_enriched WHERE transaction_id IS NOT NULL) AS staging_enriched_distinct;

\echo ''
\echo '=== 8. Query retrieval split check ==='
SELECT
    COUNT(*) AS query_log_count,
    (SELECT COUNT(*) FROM main.query_retrievals) AS retrieval_row_count,
    (SELECT COUNT(DISTINCT query_id) FROM main.query_retrievals) AS queries_with_retrievals
FROM main.query_logs;

\echo ''
\echo '=== 9. Category C runtime tables (empty at bootstrap) ==='
SELECT
    (SELECT COUNT(*) FROM main.risk_assessments) AS risk_assessments,
    (SELECT COUNT(*) FROM main.risk_indicators) AS risk_indicators,
    (SELECT COUNT(*) FROM main.agent_runs) AS agent_runs;

\echo ''
\echo '=== 10. Parties linked to main.users ==='
SELECT
    COUNT(*) AS total_parties,
    COUNT(*) FILTER (WHERE user_id IS NULL) AS parties_without_user_fk,
    COUNT(*) FILTER (WHERE user_id IS NOT NULL) AS parties_with_user_fk,
    COUNT(*) FILTER (WHERE party_name IS NOT NULL) AS parties_with_name
FROM main.transaction_parties;

\echo ''
\echo '=== 11. Canonical tx_hash naming check (legacy columns should not exist) ==='
SELECT column_name
FROM information_schema.columns
WHERE table_schema = 'main'
  AND table_name = 'blockchain_transactions'
  AND column_name IN ('blockchain_transaction_hash', 'transaction_value_aed', 'gas_fee_aed');
-- Expect 0 rows

\echo ''
\echo '=== 12. Schema presence ==='
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('staging', 'core', 'main', 'public')
ORDER BY schema_name;
