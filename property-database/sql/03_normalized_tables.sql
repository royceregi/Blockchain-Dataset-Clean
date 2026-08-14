-- Final 12-table schema (aligned with table.md + real cleaned CSV IDs).
-- Source IDs are TEXT (USER000001, 1-102-2021-1, large property ids as strings).
-- Connect to property_db before running.

DROP VIEW IF EXISTS v_blockchain_verification CASCADE;
DROP VIEW IF EXISTS v_transaction_with_parties_and_docs CASCADE;
DROP VIEW IF EXISTS v_property_full_history CASCADE;
DROP VIEW IF EXISTS v_current_ownership CASCADE;

DROP TABLE IF EXISTS query_logs CASCADE;
DROP TABLE IF EXISTS blockchain_transactions CASCADE;
DROP TABLE IF EXISTS property_documents CASCADE;
DROP TABLE IF EXISTS registration_details CASCADE;
DROP TABLE IF EXISTS transaction_parties CASCADE;
DROP TABLE IF EXISTS property_classifications CASCADE;
DROP TABLE IF EXISTS property_ownership_history CASCADE;
DROP TABLE IF EXISTS property_transactions CASCADE;
DROP TABLE IF EXISTS transaction_types CASCADE;
DROP TABLE IF EXISTS locations CASCADE;
DROP TABLE IF EXISTS properties CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- 10. users
CREATE TABLE users (
    user_id         TEXT PRIMARY KEY,
    username        VARCHAR(100) UNIQUE,
    name            VARCHAR(255),
    email           VARCHAR(255),
    contact         VARCHAR(50),
    role            VARCHAR(50),
    wallet_address  VARCHAR(255),
    password_hash   TEXT,
    nic_hash        VARCHAR(64),
    kyc_status      VARCHAR(50),
    access_level    VARCHAR(50),
    mfa_enabled     BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login      TIMESTAMP
);

-- 1. properties
CREATE TABLE properties (
    property_id             TEXT PRIMARY KEY,
    title_deed_number       VARCHAR(100),
    property_name           VARCHAR(255),
    address                 TEXT,
    district                VARCHAR(255),
    city                    VARCHAR(100) DEFAULT 'Dubai',
    latitude                DECIMAL(12, 8),
    longitude               DECIMAL(12, 8),
    land_area               DECIMAL(18, 4),
    area_unit               VARCHAR(20) DEFAULT 'sqm',
    land_type               VARCHAR(100),
    survey_plan_number      VARCHAR(100),
    current_owner_id        TEXT REFERENCES users(user_id),
    current_usage_type      VARCHAR(100),
    current_subtype         VARCHAR(100),
    current_value           DECIMAL(18, 2),
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

-- 12. locations
CREATE TABLE locations (
    location_id         BIGSERIAL PRIMARY KEY,
    property_id         TEXT NOT NULL UNIQUE REFERENCES properties(property_id),
    district            VARCHAR(255),
    city                VARCHAR(100) DEFAULT 'Dubai',
    latitude            DECIMAL(12, 8),
    longitude           DECIMAL(12, 8),
    area_name           VARCHAR(255),
    building_name       VARCHAR(255),
    project_name        VARCHAR(255),
    master_project      VARCHAR(255),
    nearest_landmark    VARCHAR(255),
    nearest_metro       VARCHAR(255),
    nearest_mall        VARCHAR(255)
);

-- 4. transaction_types
CREATE TABLE transaction_types (
    transaction_type_id     SERIAL PRIMARY KEY,
    transaction_type_name   VARCHAR(255) NOT NULL UNIQUE,
    description             TEXT
);

-- 3. property_transactions
CREATE TABLE property_transactions (
    transaction_id          TEXT PRIMARY KEY,
    property_id             TEXT NOT NULL REFERENCES properties(property_id),
    transaction_type_id     INT REFERENCES transaction_types(transaction_type_id),
    transaction_group       VARCHAR(100),
    registration_type       VARCHAR(100),
    procedure_name          VARCHAR(255),
    transaction_date        DATE,
    transaction_time        TIME,
    transaction_datetime    TIMESTAMP,
    year                    INT,
    month                   INT,
    quarter                 INT,
    day_of_week             VARCHAR(20),
    day_of_month            INT,
    current_value           DECIMAL(18, 2),
    previous_value          DECIMAL(18, 2),
    transaction_value       DECIMAL(18, 2),
    value_change_pct        DECIMAL(18, 4),
    procedure_area          DECIMAL(18, 4),
    meter_sale_price        DECIMAL(18, 4),
    currency                VARCHAR(10) DEFAULT 'AED',
    rooms                   VARCHAR(50),
    has_parking             BOOLEAN,
    status                  VARCHAR(50) DEFAULT 'Completed'
);

-- 2. property_ownership_history
CREATE TABLE property_ownership_history (
    ownership_id            BIGSERIAL PRIMARY KEY,
    property_id             TEXT NOT NULL REFERENCES properties(property_id),
    owner_id                TEXT REFERENCES users(user_id),
    ownership_start_date    DATE,
    ownership_end_date      DATE,
    ownership_type          VARCHAR(100),
    transaction_id          TEXT REFERENCES property_transactions(transaction_id),
    ownership_status        VARCHAR(50),
    recorded_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. property_classifications
CREATE TABLE property_classifications (
    classification_id       BIGSERIAL PRIMARY KEY,
    property_id             TEXT NOT NULL REFERENCES properties(property_id),
    transaction_id          TEXT REFERENCES property_transactions(transaction_id),
    property_group          VARCHAR(255),
    property_type           VARCHAR(100),
    previous_subtype        VARCHAR(100),
    current_subtype         VARCHAR(100),
    previous_usage_type     VARCHAR(100),
    current_usage_type      VARCHAR(100),
    registration_type       VARCHAR(100),
    land_type               VARCHAR(100),
    land_use_zone           VARCHAR(100),
    effective_date          DATE
);

-- 6. transaction_parties
CREATE TABLE transaction_parties (
    transaction_party_id    BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT NOT NULL REFERENCES property_transactions(transaction_id),
    user_id                 TEXT REFERENCES users(user_id),
    party_name              VARCHAR(255),
    role                    VARCHAR(50) NOT NULL,
    is_primary              BOOLEAN DEFAULT FALSE,
    UNIQUE (transaction_id, role, party_name)
);

-- 7. registration_details
CREATE TABLE registration_details (
    registration_id         BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT NOT NULL UNIQUE REFERENCES property_transactions(transaction_id),
    registration_number     VARCHAR(100),
    registration_date       DATE,
    registration_fee        DECIMAL(18, 2),
    tax_amount              DECIMAL(18, 2),
    other_fee               DECIMAL(18, 2),
    total_amount_paid       DECIMAL(18, 2),
    currency                VARCHAR(10) DEFAULT 'AED',
    registration_status     VARCHAR(50)
);

-- 8. property_documents
CREATE TABLE property_documents (
    document_id             BIGSERIAL PRIMARY KEY,
    property_id             TEXT REFERENCES properties(property_id),
    transaction_id          TEXT REFERENCES property_transactions(transaction_id),
    document_type           VARCHAR(100) DEFAULT 'Title Deed',
    document_number         VARCHAR(100),
    document_text           TEXT,
    document_hash           VARCHAR(255),
    document_url            TEXT,
    issued_date             DATE,
    verification_status     VARCHAR(50)
);

-- 9. blockchain_transactions
CREATE TABLE blockchain_transactions (
    blockchain_tx_id        BIGSERIAL PRIMARY KEY,
    transaction_id          TEXT REFERENCES property_transactions(transaction_id),
    property_id             TEXT REFERENCES properties(property_id),
    tx_hash                 VARCHAR(255) UNIQUE,
    previous_hash           VARCHAR(255),
    property_hash           VARCHAR(255),
    block_number            BIGINT,
    block_timestamp         TIMESTAMP,
    from_wallet             VARCHAR(255),
    to_wallet               VARCHAR(255),
    transaction_type        VARCHAR(100),
    transaction_value_aed   DECIMAL(18, 2),
    smart_contract_address  VARCHAR(255),
    digital_signature       TEXT,
    transaction_status      VARCHAR(50),
    consensus_verification  TEXT,
    gas_fee_aed             DECIMAL(18, 4)
);

-- 11. query_logs
CREATE TABLE query_logs (
    query_id                    TEXT PRIMARY KEY,
    user_id                     TEXT REFERENCES users(user_id),
    query_text                  TEXT,
    log_timestamp               TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retrieved_transaction_ids   TEXT,
    agent_response              TEXT,
    confidence_score            DECIMAL(6, 4),
    relevance_score             DECIMAL(6, 4),
    flagged_suspicious          BOOLEAN DEFAULT FALSE,
    agent_used                  VARCHAR(100),
    response_time_ms            INT
);