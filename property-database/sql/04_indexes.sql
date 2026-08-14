-- Run after ETL load is complete.

CREATE INDEX IF NOT EXISTS idx_properties_title_deed
    ON properties (title_deed_number);

CREATE INDEX IF NOT EXISTS idx_properties_current_owner
    ON properties (current_owner_id);

CREATE INDEX IF NOT EXISTS idx_locations_property
    ON locations (property_id);

CREATE INDEX IF NOT EXISTS idx_pt_property_date
    ON property_transactions (property_id, transaction_date);

CREATE INDEX IF NOT EXISTS idx_pt_type
    ON property_transactions (transaction_type_id);

CREATE INDEX IF NOT EXISTS idx_ownership_property_owner
    ON property_ownership_history (property_id, owner_id);

CREATE INDEX IF NOT EXISTS idx_ownership_open
    ON property_ownership_history (property_id)
    WHERE ownership_end_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_classifications_property
    ON property_classifications (property_id, transaction_id);

CREATE INDEX IF NOT EXISTS idx_parties_tx_role
    ON transaction_parties (transaction_id, role);

CREATE INDEX IF NOT EXISTS idx_parties_user
    ON transaction_parties (user_id);

CREATE INDEX IF NOT EXISTS idx_documents_hash
    ON property_documents (document_hash);

CREATE INDEX IF NOT EXISTS idx_documents_property
    ON property_documents (property_id);

CREATE INDEX IF NOT EXISTS idx_blockchain_tx_hash
    ON blockchain_transactions (tx_hash);

CREATE INDEX IF NOT EXISTS idx_blockchain_property
    ON blockchain_transactions (property_id);

CREATE INDEX IF NOT EXISTS idx_blockchain_transaction
    ON blockchain_transactions (transaction_id);

CREATE INDEX IF NOT EXISTS idx_query_logs_user
    ON query_logs (user_id, log_timestamp);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users (email);