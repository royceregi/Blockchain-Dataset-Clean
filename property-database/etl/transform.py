"""Transform staging → 12 normalized tables (table.md design)."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import text

from utils import (
    clean_str,
    normalize_property_id,
    sha256_text,
    to_bool,
    to_date,
    to_float,
    to_int,
    to_time,
    to_timestamp,
    username_from_user_id,
)


def _read(conn, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), conn)


def _clear_final_tables(conn) -> None:
    # Child → parent order
    tables = [
        "query_logs",
        "blockchain_transactions",
        "property_documents",
        "registration_details",
        "transaction_parties",
        "property_classifications",
        "property_ownership_history",
        "property_transactions",
        "transaction_types",
        "locations",
        "properties",
        "users",
    ]
    for t in tables:
        conn.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))


def transform_users(conn, enriched: pd.DataFrame) -> dict[str, dict]:
    users_df = _read(conn, "SELECT * FROM staging_users")
    users: dict[str, dict] = {}

    def upsert(user_id, name=None, role=None, email=None, contact=None,
               wallet=None, password_hash=None, nic=None, kyc=None,
               access=None, mfa=None):
        uid = clean_str(user_id)
        if uid is None:
            return
        row = users.get(uid, {
            "user_id": uid,
            "username": username_from_user_id(uid),
            "name": None,
            "email": None,
            "contact": None,
            "role": None,
            "wallet_address": None,
            "password_hash": None,
            "nic_hash": None,
            "kyc_status": None,
            "access_level": None,
            "mfa_enabled": False,
            "is_active": True,
        })
        if name:
            row["name"] = clean_str(name) or row["name"]
        if role:
            row["role"] = clean_str(role) or row["role"]
        if email:
            row["email"] = clean_str(email) or row["email"]
        if contact:
            row["contact"] = clean_str(contact) or row["contact"]
        if wallet:
            row["wallet_address"] = clean_str(wallet) or row["wallet_address"]
        if password_hash:
            row["password_hash"] = clean_str(password_hash) or row["password_hash"]
        if nic:
            row["nic_hash"] = sha256_text(nic) or row["nic_hash"]
        if kyc:
            row["kyc_status"] = clean_str(kyc) or row["kyc_status"]
        if access:
            row["access_level"] = clean_str(access) or row["access_level"]
        if mfa is not None:
            b = to_bool(mfa)
            if b is not None:
                row["mfa_enabled"] = b
        users[uid] = row

    for r in users_df.itertuples(index=False):
        upsert(
            r.user_id,
            name=r.full_name,
            role=r.role,
            email=r.email,
            contact=r.phone_number,
            wallet=r.wallet_address,
            password_hash=r.auth_password_hash,
            nic=r.owner_nic,
            kyc=r.kyc_status,
            access=r.access_level,
            mfa=r.mfa_enabled,
        )

    # Extra people from enriched (owners / sellers). Witnesses/notaries often have names only.
    for r in enriched.itertuples(index=False):
        upsert(r.owner_id, name=r.owner_name, role="Owner", wallet=r.owner_wallet_address, nic=r.owner_nic)
        upsert(r.seller_id, name=r.seller_name, role="Seller", wallet=r.seller_wallet_address)

    rows = list(users.values())
    if rows:
        pd.DataFrame(rows).to_sql("users", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"  users: {len(rows):,}")
    return users


def transform_properties_and_locations(conn, enriched: pd.DataFrame) -> set[str]:
    # Latest transaction per property drives "current" property attributes
    df = enriched.copy()
    df["property_id_n"] = df["property_id"].map(normalize_property_id)
    df["tx_dt"] = pd.to_datetime(df["full_timestamp"], errors="coerce")
    df = df.dropna(subset=["property_id_n"])
    df = df.sort_values(["property_id_n", "tx_dt"])
    latest = df.groupby("property_id_n", as_index=False).tail(1)

    prop_rows = []
    loc_rows = []
    for r in latest.itertuples(index=False):
        pid = r.property_id_n
        prop_rows.append({
            "property_id": pid,
            "title_deed_number": clean_str(r.title_deed_number),
            "property_name": clean_str(r.property_name),
            "address": clean_str(r.area_name),
            "district": clean_str(r.area_name),
            "city": "Dubai",
            "latitude": to_float(r.gps_latitude),
            "longitude": to_float(r.gps_longitude),
            "land_area": to_float(r.procedure_area),
            "area_unit": "sqm",
            "land_type": clean_str(r.land_use_zone) or clean_str(r.property_usage),
            "survey_plan_number": clean_str(r.survey_plan_number),
            "current_owner_id": clean_str(r.owner_id),
            "current_usage_type": clean_str(r.property_usage),
            "current_subtype": clean_str(r.property_sub_type),
            "current_value": to_float(r.actual_worth),
            "legal_status": clean_str(r.legal_status),
            "verification_status": clean_str(r.verification_status),
            "encumbrances": clean_str(r.encumbrances),
            "boundary_north": clean_str(r.boundary_north),
            "boundary_south": clean_str(r.boundary_south),
            "boundary_east": clean_str(r.boundary_east),
            "boundary_west": clean_str(r.boundary_west),
        })
        loc_rows.append({
            "property_id": pid,
            "district": clean_str(r.area_name),
            "city": "Dubai",
            "latitude": to_float(r.gps_latitude),
            "longitude": to_float(r.gps_longitude),
            "area_name": clean_str(r.area_name),
            "building_name": clean_str(r.building_name),
            "project_name": clean_str(r.project_name),
            "master_project": clean_str(r.master_project),
            "nearest_landmark": clean_str(r.nearest_landmark),
            "nearest_metro": clean_str(r.nearest_metro),
            "nearest_mall": clean_str(r.nearest_mall),
        })

    # Drop FK to missing users for current_owner_id
    existing_users = set(_read(conn, "SELECT user_id FROM users")["user_id"].tolist())
    for row in prop_rows:
        if row["current_owner_id"] not in existing_users:
            row["current_owner_id"] = None

    if prop_rows:
        pd.DataFrame(prop_rows).to_sql("properties", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    if loc_rows:
        pd.DataFrame(loc_rows).to_sql("locations", conn, if_exists="append", index=False, method="multi", chunksize=1000)

    print(f"  properties: {len(prop_rows):,}")
    print(f"  locations: {len(loc_rows):,}")
    return {r["property_id"] for r in prop_rows}


def transform_transaction_types(conn, enriched: pd.DataFrame) -> dict[str, int]:
    names = sorted({
        clean_str(x)
        for x in enriched["procedure_name"].tolist() + enriched["reg_type"].tolist()
        if clean_str(x)
    })
    # Prefer procedure_name as the transaction type label; also keep reg_type values available
    type_map: dict[str, int] = {}
    rows = [{"transaction_type_name": n, "description": n} for n in names]
    if rows:
        pd.DataFrame(rows).to_sql("transaction_types", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    mapping_df = _read(conn, "SELECT transaction_type_id, transaction_type_name FROM transaction_types")
    type_map = dict(zip(mapping_df["transaction_type_name"], mapping_df["transaction_type_id"]))
    print(f"  transaction_types: {len(type_map):,}")
    return type_map


def transform_transactions(conn, enriched: pd.DataFrame, property_ids: set[str], type_map: dict[str, int]) -> set[str]:
    rows = []
    seen = set()
    for r in enriched.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        pid = normalize_property_id(r.property_id)
        if tid is None or pid is None or tid in seen:
            continue
        if pid not in property_ids:
            continue
        seen.add(tid)
        tname = clean_str(r.procedure_name) or clean_str(r.reg_type)
        rows.append({
            "transaction_id": tid,
            "property_id": pid,
            "transaction_type_id": type_map.get(tname) if tname else None,
            "transaction_group": clean_str(r.trans_group),
            "registration_type": clean_str(r.reg_type),
            "procedure_name": clean_str(r.procedure_name),
            "transaction_date": to_date(r.instance_date),
            "transaction_time": to_time(r.transaction_time),
            "transaction_datetime": to_timestamp(r.full_timestamp),
            "year": to_int(r.year),
            "month": to_int(r.month),
            "quarter": to_int(r.quarter),
            "day_of_week": clean_str(r.day_of_week),
            "day_of_month": to_int(r.day_of_month),
            "current_value": to_float(r.actual_worth),
            "previous_value": to_float(r.previous_value),
            "transaction_value": to_float(r.actual_worth),
            "value_change_pct": to_float(r.value_change_pct),
            "procedure_area": to_float(r.procedure_area),
            "meter_sale_price": to_float(r.meter_sale_price),
            "currency": "AED",
            "rooms": clean_str(r.rooms),
            "has_parking": to_bool(r.has_parking),
            "status": "Completed",
        })

    if rows:
        pd.DataFrame(rows).to_sql(
            "property_transactions", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  property_transactions: {len(rows):,}")
    return {r["transaction_id"] for r in rows}


def transform_ownership(conn, enriched: pd.DataFrame, property_ids: set[str], tx_ids: set[str]) -> None:
    df = enriched.copy()
    df["property_id_n"] = df["property_id"].map(normalize_property_id)
    df["tx_dt"] = pd.to_datetime(df["full_timestamp"], errors="coerce")
    df = df.dropna(subset=["property_id_n"])
    df = df.sort_values(["property_id_n", "tx_dt", "transaction_id"])

    existing_users = set(_read(conn, "SELECT user_id FROM users")["user_id"].tolist())
    rows = []

    for pid, group in df.groupby("property_id_n", sort=False):
        if pid not in property_ids:
            continue
        prev_idx = None
        for r in group.itertuples(index=False):
            tid = clean_str(r.transaction_id)
            owner_id = clean_str(r.owner_id)
            if owner_id not in existing_users:
                owner_id = None
            start = to_date(r.instance_date) or (to_timestamp(r.full_timestamp).date() if to_timestamp(r.full_timestamp) else None)
            if prev_idx is not None:
                rows[prev_idx]["ownership_end_date"] = start
                rows[prev_idx]["ownership_status"] = "Closed"
            rows.append({
                "property_id": pid,
                "owner_id": owner_id,
                "ownership_start_date": start,
                "ownership_end_date": None,
                "ownership_type": clean_str(r.procedure_name) or "Transfer",
                "transaction_id": tid if tid in tx_ids else None,
                "ownership_status": "Current",
            })
            prev_idx = len(rows) - 1

    if rows:
        pd.DataFrame(rows).to_sql(
            "property_ownership_history", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  property_ownership_history: {len(rows):,}")


def transform_classifications(conn, enriched: pd.DataFrame, property_ids: set[str], tx_ids: set[str]) -> None:
    rows = []
    for r in enriched.itertuples(index=False):
        pid = normalize_property_id(r.property_id)
        tid = clean_str(r.transaction_id)
        if pid not in property_ids or tid not in tx_ids:
            continue
        rows.append({
            "property_id": pid,
            "transaction_id": tid,
            "property_group": clean_str(r.property_group),
            "property_type": clean_str(r.property_type),
            "previous_subtype": clean_str(r.previous_sub_type),
            "current_subtype": clean_str(r.property_sub_type),
            "previous_usage_type": clean_str(r.previous_usage_type),
            "current_usage_type": clean_str(r.property_usage),
            "registration_type": clean_str(r.reg_type),
            "land_type": clean_str(r.land_use_zone),
            "land_use_zone": clean_str(r.land_use_zone),
            "effective_date": to_date(r.instance_date),
        })
    if rows:
        pd.DataFrame(rows).to_sql(
            "property_classifications", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  property_classifications: {len(rows):,}")


def transform_parties(conn, enriched: pd.DataFrame, tx_ids: set[str]) -> None:
    existing_users = set(_read(conn, "SELECT user_id FROM users")["user_id"].tolist())
    rows = []
    seen = set()

    def add(tid, role, user_id=None, name=None, primary=False):
        if tid not in tx_ids:
            return
        uid = clean_str(user_id)
        pname = clean_str(name)
        if uid is None and pname is None:
            return
        if uid is not None and uid not in existing_users:
            uid = None
        key = (tid, role, pname or uid or "")
        if key in seen:
            return
        seen.add(key)
        rows.append({
            "transaction_id": tid,
            "user_id": uid,
            "party_name": pname,
            "role": role,
            "is_primary": primary,
        })

    for r in enriched.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        if tid is None:
            continue
        add(tid, "Owner", r.owner_id, r.owner_name, primary=True)
        add(tid, "Seller", r.seller_id, r.seller_name)
        add(tid, "Notary", None, r.notary_name)
        add(tid, "Witness", None, r.witness_1_name)
        add(tid, "Witness", None, r.witness_2_name)

    if rows:
        pd.DataFrame(rows).to_sql(
            "transaction_parties", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  transaction_parties: {len(rows):,}")


def transform_registration(conn, enriched: pd.DataFrame, tx_ids: set[str]) -> None:
    rows = []
    seen = set()
    for r in enriched.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        if tid is None or tid not in tx_ids or tid in seen:
            continue
        seen.add(tid)
        rows.append({
            "transaction_id": tid,
            "registration_number": clean_str(r.title_deed_number),
            "registration_date": to_date(r.instance_date),
            "registration_fee": to_float(r.registration_fee_aed),
            "tax_amount": None,
            "other_fee": to_float(r.trustee_office_fee_aed),
            "total_amount_paid": to_float(r.total_fees_paid_aed),
            "currency": "AED",
            "registration_status": clean_str(r.verification_status) or "Registered",
        })
    if rows:
        pd.DataFrame(rows).to_sql(
            "registration_details", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  registration_details: {len(rows):,}")


def transform_documents(conn, enriched: pd.DataFrame, property_ids: set[str], tx_ids: set[str]) -> None:
    rows = []
    for r in enriched.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        pid = normalize_property_id(r.property_id)
        if tid not in tx_ids or pid not in property_ids:
            continue
        doc_text = clean_str(r.document_text)
        doc_hash = clean_str(r.document_hash) or sha256_text(doc_text)
        if doc_text is None and doc_hash is None:
            continue
        rows.append({
            "property_id": pid,
            "transaction_id": tid,
            "document_type": "Title Deed",
            "document_number": clean_str(r.title_deed_number),
            "document_text": doc_text,
            "document_hash": doc_hash,
            "document_url": None,
            "issued_date": to_date(r.instance_date),
            "verification_status": clean_str(r.verification_status),
        })
    if rows:
        pd.DataFrame(rows).to_sql(
            "property_documents", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  property_documents: {len(rows):,}")


def transform_blockchain(conn, property_ids: set[str], tx_ids: set[str]) -> None:
    bc = _read(conn, "SELECT * FROM staging_blockchain")
    rows = []
    seen_hash = set()
    for r in bc.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        pid = normalize_property_id(r.property_id)
        tx_hash = clean_str(r.blockchain_transaction_hash)
        if tx_hash is None or tx_hash in seen_hash:
            continue
        # Prefer linking when transaction exists; otherwise still store ledger row without FK if needed
        if tid not in tx_ids:
            tid = None
        if pid not in property_ids:
            pid = None
        seen_hash.add(tx_hash)
        rows.append({
            "transaction_id": tid,
            "property_id": pid,
            "tx_hash": tx_hash,
            "previous_hash": clean_str(r.previous_transaction_hash),
            "property_hash": clean_str(r.property_hash),
            "block_number": to_int(r.block_number),
            "block_timestamp": to_timestamp(r.block_timestamp),
            "from_wallet": clean_str(r.from_wallet),
            "to_wallet": clean_str(r.to_wallet),
            "transaction_type": clean_str(r.transaction_type),
            "transaction_value_aed": to_float(r.transaction_value_aed),
            "smart_contract_address": clean_str(r.smart_contract_address),
            "digital_signature": clean_str(r.digital_signature),
            "transaction_status": clean_str(r.transaction_status),
            "consensus_verification": clean_str(r.consensus_verification),
            "gas_fee_aed": to_float(r.gas_fee_aed),
        })
    if rows:
        pd.DataFrame(rows).to_sql(
            "blockchain_transactions", conn, if_exists="append", index=False, method="multi", chunksize=1000
        )
    print(f"  blockchain_transactions: {len(rows):,}")


def transform_query_logs(conn) -> None:
    ql = _read(conn, "SELECT * FROM staging_query_logs")
    existing_users = set(_read(conn, "SELECT user_id FROM users")["user_id"].tolist())
    rows = []
    seen = set()
    for r in ql.itertuples(index=False):
        qid = clean_str(r.query_id)
        if qid is None or qid in seen:
            continue
        seen.add(qid)
        uid = clean_str(r.user_id)
        if uid not in existing_users:
            uid = None
        rows.append({
            "query_id": qid,
            "user_id": uid,
            "query_text": clean_str(r.query_text),
            "retrieved_transaction_ids": clean_str(r.retrieved_transaction_ids),
            "relevance_score": to_float(r.relevance_score),
            "flagged_suspicious": to_bool(r.flagged_suspicious) or False,
            "response_time_ms": to_int(r.response_latency_ms),
            "agent_used": "IR",
        })
    if rows:
        pd.DataFrame(rows).to_sql("query_logs", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    print(f"  query_logs: {len(rows):,}")


def run_all_transforms(conn) -> None:
    print("Clearing final tables…")
    _clear_final_tables(conn)

    print("Reading staging_property_enriched…")
    enriched = _read(conn, "SELECT * FROM staging_property_enriched")
    # Deduplicate exact duplicate transaction_ids keeping first
    enriched = enriched.drop_duplicates(subset=["transaction_id"], keep="first")

    print("Transforming…")
    transform_users(conn, enriched)
    property_ids = transform_properties_and_locations(conn, enriched)
    type_map = transform_transaction_types(conn, enriched)
    tx_ids = transform_transactions(conn, enriched, property_ids, type_map)
    transform_ownership(conn, enriched, property_ids, tx_ids)
    transform_classifications(conn, enriched, property_ids, tx_ids)
    transform_parties(conn, enriched, tx_ids)
    transform_registration(conn, enriched, tx_ids)
    transform_documents(conn, enriched, property_ids, tx_ids)
    transform_blockchain(conn, property_ids, tx_ids)
    transform_query_logs(conn)
    print("Transforms complete.")
