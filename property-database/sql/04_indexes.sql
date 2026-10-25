-- Performance indexes for the 16-table main schema. Run after ETL load.

CREATE INDEX IF NOT EXISTS idx_users_email ON main.users (email);
CREATE INDEX IF NOT EXISTS idx_users_nic_hash ON main.users (nic_hash);

CREATE INDEX IF NOT EXISTS idx_properties_title_deed ON main.properties (title_deed_number);
CREATE INDEX IF NOT EXISTS idx_properties_survey_plan ON main.properties (survey_plan_number);
CREATE INDEX IF NOT EXISTS idx_properties_current_owner ON main.properties (current_owner_id);

CREATE INDEX IF NOT EXISTS idx_locations_property ON main.locations (property_id);
CREATE INDEX IF NOT EXISTS idx_locations_area ON main.locations (area_name);

CREATE INDEX IF NOT EXISTS idx_pt_property_datetime ON main.property_transactions (property_id, transaction_datetime);
CREATE INDEX IF NOT EXISTS idx_pt_type ON main.property_transactions (transaction_type_id);
CREATE INDEX IF NOT EXISTS idx_pt_area ON main.property_transactions (area_id, area_name);

CREATE INDEX IF NOT EXISTS idx_ownership_property_owner ON main.property_ownership_history (property_id, owner_id);
CREATE INDEX IF NOT EXISTS idx_ownership_open ON main.property_ownership_history (property_id) WHERE ownership_end_date IS NULL;

CREATE INDEX IF NOT EXISTS idx_parties_tx_role ON main.transaction_parties (transaction_id, role);
CREATE INDEX IF NOT EXISTS idx_parties_user ON main.transaction_parties (user_id);

CREATE INDEX IF NOT EXISTS idx_documents_hash ON main.property_documents (document_hash);
CREATE INDEX IF NOT EXISTS idx_documents_property ON main.property_documents (property_id);
CREATE INDEX IF NOT EXISTS idx_documents_transaction ON main.property_documents (transaction_id);

CREATE INDEX IF NOT EXISTS idx_registration_tx ON main.registration_details (transaction_id);

CREATE INDEX IF NOT EXISTS idx_blockchain_tx_hash ON main.blockchain_transactions (tx_hash);
CREATE INDEX IF NOT EXISTS idx_blockchain_property ON main.blockchain_transactions (property_id);
CREATE INDEX IF NOT EXISTS idx_blockchain_transaction ON main.blockchain_transactions (transaction_id);

CREATE INDEX IF NOT EXISTS idx_risk_assessments_tx ON main.risk_assessments (transaction_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_property ON main.risk_assessments (property_id);
CREATE INDEX IF NOT EXISTS idx_risk_assessments_level ON main.risk_assessments (risk_level);
CREATE INDEX IF NOT EXISTS idx_risk_indicators_assessment ON main.risk_indicators (assessment_id);

CREATE INDEX IF NOT EXISTS idx_transaction_features_property ON main.transaction_features (property_id);

CREATE INDEX IF NOT EXISTS idx_query_logs_user ON main.query_logs (user_id, log_timestamp);
CREATE INDEX IF NOT EXISTS idx_query_retrievals_query ON main.query_retrievals (query_id);
CREATE INDEX IF NOT EXISTS idx_query_retrievals_tx ON main.query_retrievals (transaction_id);

CREATE INDEX IF NOT EXISTS idx_agent_runs_query ON main.agent_runs (query_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON main.agent_runs (agent_name);
