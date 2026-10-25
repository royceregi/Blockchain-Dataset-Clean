-- PropGuard AI `main` schema: 16 tables from 1.txt (application dataset).
-- Schema layout: staging = CSV ingest | core = system seed (optional) | main = dataset | public = views
-- Application/API queries main.* ; raw CSV ingest lives in staging.*.
-- Connect to property_db before running.

DROP VIEW IF EXISTS v_blockchain_verification CASCADE;
DROP VIEW IF EXISTS v_transaction_with_parties_and_docs CASCADE;
DROP VIEW IF EXISTS v_property_full_history CASCADE;
DROP VIEW IF EXISTS v_current_ownership CASCADE;
DROP VIEW IF EXISTS v_risk_summary CASCADE;

-- Remove legacy public tables from older runs
DROP TABLE IF EXISTS public.products CASCADE;
DROP TABLE IF EXISTS public.property_classifications CASCADE;
DROP TABLE IF EXISTS public.agent_runs CASCADE;
DROP TABLE IF EXISTS public.query_retrievals CASCADE;
DROP TABLE IF EXISTS public.transaction_features CASCADE;
DROP TABLE IF EXISTS public.risk_indicators CASCADE;
DROP TABLE IF EXISTS public.risk_assessments CASCADE;
DROP TABLE IF EXISTS public.query_logs CASCADE;
DROP TABLE IF EXISTS public.blockchain_transactions CASCADE;
DROP TABLE IF EXISTS public.property_documents CASCADE;
DROP TABLE IF EXISTS public.registration_details CASCADE;
DROP TABLE IF EXISTS public.transaction_parties CASCADE;
DROP TABLE IF EXISTS public.property_ownership_history CASCADE;
DROP TABLE IF EXISTS public.property_transactions CASCADE;
DROP TABLE IF EXISTS public.transaction_types CASCADE;
DROP TABLE IF EXISTS public.locations CASCADE;
DROP TABLE IF EXISTS public.properties CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;

DROP SCHEMA IF EXISTS main CASCADE;
CREATE SCHEMA main;

-- 1. users (system seeds + cleaned stakeholders from staging.users)
CREATE TABLE main.users (
    user_id         TEXT PRIMARY KEY,
    username        VARCHAR(100) UNIQUE,
    full_name       VARCHAR(255),
    email           VARCHAR(255),
    phone_number    VARCHAR(50),
    password_hash   TEXT,
    role            VARCHAR(50),
    wallet_address  VARCHAR(255),
    nic_hash        VARCHAR(64),
    kyc_status      VARCHAR(50),
    access_level    VARCHAR(50),
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);

-- 2. properties
CREATE TABLE main.properties (
    property_id             TEXT PRIMARY KEY,
    title_deed_number       VARCHAR(100) UNIQUE,
    property_name           VARCHAR(255),
    address                 TEXT,
    district                VARCHAR(255),
    city                    VARCHAR(100) DEFAULT 'Dubai',
    latitude                NUMERIC(12, 8),
    longitude               NUMERIC(12, 8),
    land_area               NUMERIC(18, 4),
    area_unit               VARCHAR(20) DEFAULT 'sqm',
    land_type               VARCHAR(100),
    survey_plan_number      VARCHAR(100) UNIQUE,
    current_owner_id        TEXT REFERENCES main.users(user_id),
    current_usage_type      VARCHAR(100),
    current_subtype         VARCHAR(100),
    current_value           NUMERIC(18, 2),
    legal_status            VARCHAR(100),
    verification_status     VARCHAR(100),
    encumbrances            TEXT,
    boundary_north          TEXT,
    boundary_south          TEXT,
    boundary_east           TEXT,
    boundary_west           TEXT,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. transaction_types
CREATE TABLE main.transaction_types (
    transaction_type_id     SERIAL PRIMARY KEY,
    transaction_type_name   VARCHAR(255) NOT NULL UNIQUE,
    description             TEXT
);

-- 4. property_transactions
CREATE TABLE main.property_transactions (
    transaction_id          TEXT PRIMARY KEY,
    property_id             TEXT NOT NULL REFERENCES main.properties(property_id),
    transaction_type_id     INT REFERENCES main.transaction_types(transaction_type_id),
    transaction_group       VARCHAR(100),
    registration_type       VARCHAR(100),
    procedure_name          VARCHAR(255),
    transaction_datetime    TIMESTAMP,
    transaction_value       NUMERIC(18, 2),
    previous_value          NUMERIC(18, 2),
    value_change_pct        NUMERIC(18, 4),
    procedure_area          NUMERIC(18, 4),
    meter_sale_price        NUMERIC(18, 4),
    currency                VARCHAR(10) DEFAULT 'AED',
    status                  VARCHAR(50) DEFAULT 'Completed',
    procedure_id            VARCHAR(100),
    trans_group_id          VARCHAR(100),
    area_id                 VARCHAR(100),
    area_name               VARCHAR(255),
    project_number          VARCHAR(100),
    project_name            VARCHAR(255),
    master_project          VARCHAR(255),
    nearest_landmark        VARCHAR(255),
    rooms                   VARCHAR(50),
    has_parking             BOOLEAN,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. transaction_parties
CREATE TABLE main.transaction_parties (
    transaction_party_id    BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT NOT NULL REFERENCES main.property_transactions(transaction_id),
    user_id                 TEXT REFERENCES main.users(user_id),
    party_name              VARCHAR(255),
    role                    VARCHAR(50) NOT NULL,
    is_primary              BOOLEAN DEFAULT FALSE,
    UNIQUE (transaction_id, role, party_name)
);

-- 6. property_ownership_history (owner_id = historical party identifier from CSV)
CREATE TABLE main.property_ownership_history (
    ownership_id            BIGSERIAL PRIMARY KEY,
    property_id             TEXT NOT NULL REFERENCES main.properties(property_id),
    owner_id                TEXT,
    ownership_start_date    DATE,
    ownership_end_date      DATE,
    ownership_type          VARCHAR(100),
    transaction_id          TEXT REFERENCES main.property_transactions(transaction_id),
    ownership_status        VARCHAR(50),
    recorded_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. property_documents
CREATE TABLE main.property_documents (
    document_id             BIGSERIAL PRIMARY KEY,
    property_id             TEXT REFERENCES main.properties(property_id),
    transaction_id          TEXT REFERENCES main.property_transactions(transaction_id),
    document_type           VARCHAR(100) DEFAULT 'Title Deed',
    document_number         VARCHAR(100),
    document_text           TEXT,
    document_hash           VARCHAR(255),
    document_url            TEXT,
    issued_date             DATE,
    verification_status     VARCHAR(50),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. registration_details
CREATE TABLE main.registration_details (
    registration_id         BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT NOT NULL UNIQUE REFERENCES main.property_transactions(transaction_id),
    registration_number     VARCHAR(100),
    registration_date       DATE,
    registration_fee        NUMERIC(18, 2),
    tax_amount              NUMERIC(18, 2),
    other_fee               NUMERIC(18, 2),
    total_amount_paid       NUMERIC(18, 2),
    currency                VARCHAR(10) DEFAULT 'AED',
    registration_status     VARCHAR(50)
);

-- 9. blockchain_transactions
CREATE TABLE main.blockchain_transactions (
    blockchain_tx_id        BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT UNIQUE REFERENCES main.property_transactions(transaction_id),
    property_id             TEXT REFERENCES main.properties(property_id),
    tx_hash                 VARCHAR(255) UNIQUE NOT NULL,
    previous_hash           VARCHAR(255),
    property_hash           VARCHAR(255),
    block_number            BIGINT,
    block_timestamp         TIMESTAMP,
    from_wallet             VARCHAR(255),
    to_wallet               VARCHAR(255),
    transaction_type        VARCHAR(100),
    transaction_value       NUMERIC(18, 2),
    smart_contract_address  VARCHAR(255),
    digital_signature       TEXT,
    transaction_status      VARCHAR(50),
    consensus_verification  TEXT,
    gas_fee                 NUMERIC(18, 4),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 10. risk_assessments (Category C — runtime)
CREATE TABLE main.risk_assessments (
    assessment_id           BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT NOT NULL REFERENCES main.property_transactions(transaction_id),
    property_id             TEXT NOT NULL REFERENCES main.properties(property_id),
    risk_score              NUMERIC(5, 2),
    risk_level              VARCHAR(20),
    model_name              VARCHAR(100),
    model_version           VARCHAR(50),
    assessment_status       VARCHAR(50) DEFAULT 'Completed',
    explanation             TEXT,
    reviewed_by             TEXT REFERENCES main.users(user_id),
    review_status           VARCHAR(50),
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 11. risk_indicators (Category C — runtime)
CREATE TABLE main.risk_indicators (
    indicator_id            BIGSERIAL PRIMARY KEY,
    assessment_id           BIGINT NOT NULL REFERENCES main.risk_assessments(assessment_id),
    indicator_code          VARCHAR(50) NOT NULL,
    indicator_name          VARCHAR(255),
    indicator_value         NUMERIC(18, 4),
    severity                VARCHAR(20),
    description             TEXT,
    evidence_reference      TEXT
);

-- 12. transaction_features
CREATE TABLE main.transaction_features (
    feature_id                          BIGSERIAL PRIMARY KEY,
    transaction_id                      TEXT NOT NULL UNIQUE REFERENCES main.property_transactions(transaction_id),
    property_id                         TEXT NOT NULL REFERENCES main.properties(property_id),
    price_per_area                      NUMERIC(18, 4),
    price_deviation_from_area_median    NUMERIC(18, 4),
    ownership_change_count              INT,
    transactions_last_90_days           INT,
    transactions_last_365_days          INT,
    days_since_previous_transaction     INT,
    value_change_pct                    NUMERIC(18, 4),
    document_count                      INT,
    missing_document_count              INT,
    hash_chain_valid                    BOOLEAN,
    seller_matches_owner                BOOLEAN,
    has_active_encumbrance              BOOLEAN,
    duplicate_document_count            INT
);

-- 13. query_logs
CREATE TABLE main.query_logs (
    query_id                TEXT PRIMARY KEY,
    user_id                 TEXT REFERENCES main.users(user_id),
    query_text              TEXT,
    log_timestamp           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_response          TEXT,
    confidence_score        NUMERIC(6, 4),
    relevance_score         NUMERIC(6, 4),
    flagged_suspicious      BOOLEAN DEFAULT FALSE,
    agent_used              VARCHAR(100),
    response_time_ms        INT
);

-- 14. query_retrievals
CREATE TABLE main.query_retrievals (
    retrieval_id            BIGSERIAL PRIMARY KEY,
    query_id                TEXT NOT NULL REFERENCES main.query_logs(query_id),
    transaction_id          TEXT REFERENCES main.property_transactions(transaction_id),
    document_id             BIGINT REFERENCES main.property_documents(document_id),
    rank                    INT,
    relevance_score         NUMERIC(6, 4)
);

-- 15. agent_runs (Category C — runtime)
CREATE TABLE main.agent_runs (
    agent_run_id            BIGSERIAL PRIMARY KEY,
    query_id                TEXT REFERENCES main.query_logs(query_id),
    agent_name              VARCHAR(100) NOT NULL,
    input_data              JSONB,
    output_data             JSONB,
    status                  VARCHAR(50),
    confidence_score        NUMERIC(6, 4),
    started_at              TIMESTAMP,
    completed_at            TIMESTAMP,
    error_message           TEXT
);

-- 16. locations
CREATE TABLE main.locations (
    location_id             BIGSERIAL PRIMARY KEY,
    property_id             TEXT NOT NULL REFERENCES main.properties(property_id),
    district                VARCHAR(255),
    city                    VARCHAR(100) DEFAULT 'Dubai',
    latitude                NUMERIC(12, 8),
    longitude               NUMERIC(12, 8),
    area_name               VARCHAR(255),
    building_name           VARCHAR(255),
    project_name            VARCHAR(255),
    master_project          VARCHAR(255),
    nearest_landmark        VARCHAR(255),
    nearest_metro           VARCHAR(255),
    nearest_mall            VARCHAR(255)
);
