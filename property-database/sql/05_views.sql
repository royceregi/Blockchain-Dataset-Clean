-- Helpful views for AI agents / demos

CREATE OR REPLACE VIEW v_current_ownership AS
SELECT
    p.property_id,
    p.property_name,
    p.title_deed_number,
    p.legal_status,
    p.current_value,
    u.user_id AS owner_id,
    u.name AS current_owner,
    oh.ownership_start_date,
    oh.transaction_id
FROM properties p
JOIN property_ownership_history oh
    ON p.property_id = oh.property_id
   AND oh.ownership_end_date IS NULL
LEFT JOIN users u ON oh.owner_id = u.user_id;

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
    u.name AS owner_name,
    oh.ownership_start_date,
    oh.ownership_end_date
FROM properties p
JOIN property_transactions pt ON p.property_id = pt.property_id
LEFT JOIN transaction_types tt ON pt.transaction_type_id = tt.transaction_type_id
LEFT JOIN property_ownership_history oh ON pt.transaction_id = oh.transaction_id
LEFT JOIN users u ON oh.owner_id = u.user_id
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
    COALESCE(u.name, tp.party_name) AS party_name,
    rd.registration_fee,
    rd.other_fee AS trustee_office_fee,
    rd.total_amount_paid,
    pd.document_hash,
    LEFT(pd.document_text, 200) AS document_preview
FROM property_transactions pt
JOIN properties p ON pt.property_id = p.property_id
LEFT JOIN transaction_types tt ON pt.transaction_type_id = tt.transaction_type_id
LEFT JOIN transaction_parties tp ON pt.transaction_id = tp.transaction_id
LEFT JOIN users u ON tp.user_id = u.user_id
LEFT JOIN registration_details rd ON pt.transaction_id = rd.transaction_id
LEFT JOIN property_documents pd ON pt.transaction_id = pd.transaction_id;

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
FROM property_transactions pt
JOIN properties p ON pt.property_id = p.property_id
LEFT JOIN blockchain_transactions bt ON pt.transaction_id = bt.transaction_id
LEFT JOIN property_documents pd ON pt.transaction_id = pd.transaction_id;