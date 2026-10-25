-- Agent-facing views over main.* tables for PropGuard AI demos

CREATE OR REPLACE VIEW v_current_ownership AS
SELECT
    p.property_id,
    p.property_name,
    p.title_deed_number,
    p.legal_status,
    p.current_value,
    oh.owner_id,
    tp.party_name AS current_owner_name,
    oh.ownership_start_date,
    oh.transaction_id
FROM main.properties p
JOIN main.property_ownership_history oh
    ON p.property_id = oh.property_id
   AND oh.ownership_end_date IS NULL
LEFT JOIN main.transaction_parties tp
    ON oh.transaction_id = tp.transaction_id
   AND tp.role = 'Owner'
   AND tp.is_primary = TRUE;

CREATE OR REPLACE VIEW v_property_full_history AS
SELECT
    p.property_id,
    p.property_name,
    pt.transaction_id,
    pt.transaction_datetime,
    tt.transaction_type_name,
    pt.procedure_name,
    pt.transaction_value,
    pt.previous_value,
    pt.value_change_pct,
    oh.owner_id,
    tp.party_name AS owner_name,
    oh.ownership_start_date,
    oh.ownership_end_date
FROM main.properties p
JOIN main.property_transactions pt ON p.property_id = pt.property_id
LEFT JOIN main.transaction_types tt ON pt.transaction_type_id = tt.transaction_type_id
LEFT JOIN main.property_ownership_history oh ON pt.transaction_id = oh.transaction_id
LEFT JOIN main.transaction_parties tp
    ON pt.transaction_id = tp.transaction_id
   AND tp.role = 'Owner'
   AND tp.is_primary = TRUE
ORDER BY p.property_id, pt.transaction_datetime;

CREATE OR REPLACE VIEW v_transaction_with_parties_and_docs AS
SELECT
    pt.transaction_id,
    p.property_id,
    p.property_name,
    tt.transaction_type_name,
    pt.transaction_datetime,
    pt.transaction_value,
    tp.role AS party_role,
    COALESCE(u.full_name, tp.party_name) AS party_name,
    rd.registration_fee,
    rd.other_fee AS trustee_office_fee,
    rd.total_amount_paid,
    pd.document_hash,
    LEFT(pd.document_text, 200) AS document_preview
FROM main.property_transactions pt
JOIN main.properties p ON pt.property_id = p.property_id
LEFT JOIN main.transaction_types tt ON pt.transaction_type_id = tt.transaction_type_id
LEFT JOIN main.transaction_parties tp ON pt.transaction_id = tp.transaction_id
LEFT JOIN main.users u ON tp.user_id = u.user_id
LEFT JOIN main.registration_details rd ON pt.transaction_id = rd.transaction_id
LEFT JOIN main.property_documents pd ON pt.transaction_id = pd.transaction_id;

CREATE OR REPLACE VIEW v_blockchain_verification AS
SELECT
    pt.transaction_id,
    p.property_id,
    p.property_name,
    bt.tx_hash,
    bt.previous_hash,
    bt.property_hash,
    bt.block_number,
    bt.block_timestamp,
    bt.from_wallet,
    bt.to_wallet,
    bt.transaction_status,
    bt.consensus_verification,
    pd.document_hash,
    CASE
        WHEN bt.tx_hash IS NOT NULL AND pd.document_hash IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS has_onchain_and_document_hash
FROM main.property_transactions pt
JOIN main.properties p ON pt.property_id = p.property_id
LEFT JOIN main.blockchain_transactions bt ON pt.transaction_id = bt.transaction_id
LEFT JOIN main.property_documents pd ON pt.transaction_id = pd.transaction_id;

CREATE OR REPLACE VIEW v_risk_summary AS
SELECT
    ra.assessment_id,
    pt.transaction_id,
    p.property_id,
    p.property_name,
    ra.risk_score,
    ra.risk_level,
    ra.model_name,
    ra.explanation,
    COUNT(ri.indicator_id) AS indicator_count
FROM main.risk_assessments ra
JOIN main.property_transactions pt ON ra.transaction_id = pt.transaction_id
JOIN main.properties p ON ra.property_id = p.property_id
LEFT JOIN main.risk_indicators ri ON ra.assessment_id = ri.assessment_id
GROUP BY ra.assessment_id, pt.transaction_id, p.property_id, p.property_name,
         ra.risk_score, ra.risk_level, ra.model_name, ra.explanation;
