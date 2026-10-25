"""Transform staging → 16 normalized main tables (1.txt / PropGuard model)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import text

from utils import (
    clean_str,
    normalize_property_id,
    prefer_existing_or_plain,
    split_csv_ids,
    to_bool,
    to_date,
    to_float,
    to_int,
    to_timestamp,
    username_from_user_id,
)

MAIN = "main"

# Enriched-only columns: overlay from property_enriched when merging with transactions
ENRICHMENT_COLUMNS = {
    "owner_id", "owner_name", "owner_nic", "owner_wallet_address",
    "seller_id", "seller_name", "seller_wallet_address",
    "witness_1_name", "witness_2_name", "notary_name",
    "property_name", "property_group", "legal_status", "encumbrances",
    "verification_status", "title_deed_number", "survey_plan_number",
    "boundary_north", "boundary_south", "boundary_east", "boundary_west",
    "gps_latitude", "gps_longitude", "document_text", "document_hash",
    "property_hash", "previous_transaction_hash", "blockchain_transaction_hash",
    "block_number", "block_timestamp", "smart_contract_address",
    "day_of_week", "day_of_month", "transaction_time", "full_timestamp",
    "previous_usage_type", "previous_sub_type", "previous_value", "value_change_pct",
    "land_use_zone", "registration_fee_aed", "trustee_office_fee_aed", "total_fees_paid_aed",
    "calculated_price_per_area", "year", "month", "quarter",
}


def _read(conn, sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), conn)


def _write_df(conn, table: str, rows: list[dict], chunksize: int = 1000) -> int:
    if not rows:
        print(f"  {MAIN}.{table}: 0", flush=True)
        return 0
    pd.DataFrame(rows).to_sql(
        table, conn, schema=MAIN, if_exists="append", index=False, method="multi", chunksize=chunksize
    )
    print(f"  {MAIN}.{table}: {len(rows):,}", flush=True)
    return len(rows)


def _clear_final_tables(conn) -> None:
    """Truncate all main dataset tables (users reloaded from seed + staging)."""
    tables = [
        "agent_runs",
        "query_retrievals",
        "query_logs",
        "risk_indicators",
        "risk_assessments",
        "transaction_features",
        "blockchain_transactions",
        "property_documents",
        "registration_details",
        "transaction_parties",
        "property_ownership_history",
        "property_transactions",
        "transaction_types",
        "locations",
        "properties",
        "users",
    ]
    for t in tables:
        conn.execute(text(f"TRUNCATE TABLE {MAIN}.{t} RESTART IDENTITY CASCADE"))


# Demo system accounts (same as sql/07_seed_users.sql). password_hash / nic_hash already hashed.
SYSTEM_USERS = [
    {
        "user_id": "SYS000001",
        "username": "superadmin",
        "full_name": "Super Admin",
        "email": "superadmin@propguard.ai",
        "phone_number": "+971500000001",
        "password_hash": "pbkdf2_sha256$10000$fd995af5b343dad5fad10b83935e4d8a$72b8563f0cbe253c26dc381b845381b33001b785e6e0be6134fb25f79bcfb4d3",
        "role": "SUPER_ADMIN",
        "wallet_address": "0xSuperAdminWallet001",
        "nic_hash": "2369e2bf0ed3029a338aa60c9660316d0ae901ff77fb072c46a8d00b72dc85d6",
        "kyc_status": "Verified",
        "access_level": "Full",
        "mfa_enabled": True,
        "is_active": True,
    },
    {
        "user_id": "SYS000002",
        "username": "landregistry",
        "full_name": "Land Registry Officer",
        "email": "registry@propguard.ai",
        "phone_number": "+971500000002",
        "password_hash": "pbkdf2_sha256$10000$2f0b94c24f59e75a3b35686899670651$ba947dab744e5626e55442f0d37ceb4118fbafef3ad68f0ad452ab8b064782da",
        "role": "LAND_REGISTRY",
        "wallet_address": "0xLandRegistryWallet002",
        "nic_hash": "46d7b6ce605e42ff2d10773a32aeb8c570944258f33deb531c4cd3569c7074da",
        "kyc_status": "Verified",
        "access_level": "Registry",
        "mfa_enabled": True,
        "is_active": True,
    },
    {
        "user_id": "SYS000003",
        "username": "realestate",
        "full_name": "Real Estate Company",
        "email": "realestate@propguard.ai",
        "phone_number": "+971500000003",
        "password_hash": "pbkdf2_sha256$10000$daa3d3f8025006436dbedfcdd13ddae6$6200f997373d7124d5f5aa2ad2a48916980bce929c86df789c6fa751154b20c0",
        "role": "REAL_ESTATE_COMPANY",
        "wallet_address": "0xRealEstateWallet003",
        "nic_hash": "762f33f3d9cb6bdb55978621ebc031dcf4238000e49b8eb6b1ad377f7841e33f",
        "kyc_status": "Verified",
        "access_level": "Company",
        "mfa_enabled": False,
        "is_active": True,
    },
    {
        "user_id": "SYS000004",
        "username": "publicuser",
        "full_name": "Public User Demo",
        "email": "public@propguard.ai",
        "phone_number": "+971500000004",
        "password_hash": "pbkdf2_sha256$10000$8c113efdf5cf5d05261f2e02ac02471f$daad8b8a5bc595a691ec82b21603ed0f0ea6038a9eb2d8663e19d6a4c1481a7e",
        "role": "PUBLIC_USER",
        "wallet_address": "0xPublicUserWallet004",
        "nic_hash": "3d2a7ac6db78efe216083b864ba755c115266ec3754ed08b993f4ee13e2d9290",
        "kyc_status": "Pending",
        "access_level": "Basic",
        "mfa_enabled": False,
        "is_active": True,
    },
]


def transform_users(conn) -> set[str]:
    """Load system seeds + cleaned stakeholders into main.users.

    Hash policy: keep existing password/nic hashes when present; otherwise store plain NIC.
    """
    rows = list(SYSTEM_USERS)
    seen = {r["user_id"] for r in rows}
    seen_usernames = {r["username"] for r in rows}

    staging_users = _read(conn, "SELECT * FROM staging.users")
    for r in staging_users.itertuples(index=False):
        uid = clean_str(r.user_id)
        if uid is None or uid in seen:
            continue
        username = username_from_user_id(uid)
        if username in seen_usernames:
            username = f"{username}_{uid[-4:]}"
        seen.add(uid)
        seen_usernames.add(username)
        rows.append({
            "user_id": uid,
            "username": username,
            "full_name": clean_str(r.full_name),
            "email": clean_str(r.email),
            "phone_number": clean_str(r.phone_number),
            # CSV auth_password_hash is already hashed → keep it; else leave None
            "password_hash": prefer_existing_or_plain(getattr(r, "auth_password_hash", None)),
            "role": clean_str(r.role) or "PUBLIC_USER",
            "wallet_address": clean_str(r.wallet_address),
            # owner_nic is plain in CSV; store plain in nic_hash for now (app will hash later)
            "nic_hash": prefer_existing_or_plain(None, getattr(r, "owner_nic", None)),
            "kyc_status": clean_str(r.kyc_status),
            "access_level": clean_str(r.access_level),
            "mfa_enabled": to_bool(r.mfa_enabled) or False,
            "is_active": True,
        })

    _write_df(conn, "users", rows, chunksize=2000)
    return {r["user_id"] for r in rows}


def merge_transaction_sources(transactions: pd.DataFrame, enriched: pd.DataFrame) -> pd.DataFrame:
    """Merge DLD transactions with enrichment on transaction_id — no duplicate fact rows."""
    tx = transactions.copy()
    enr = enriched.copy()

    for df in (tx, enr):
        if "transaction_id" in df.columns:
            df["transaction_id"] = df["transaction_id"].map(clean_str)

    tx = tx.dropna(subset=["transaction_id"]).drop_duplicates(subset=["transaction_id"], keep="first")
    enr = enr.dropna(subset=["transaction_id"]).drop_duplicates(subset=["transaction_id"], keep="first")

    tx = tx.set_index("transaction_id")
    enr = enr.set_index("transaction_id")
    all_ids = tx.index.union(enr.index)

    merged = pd.DataFrame(index=all_ids)
    for col in tx.columns:
        merged[col] = tx[col]

    for col in enr.columns:
        if col not in merged.columns:
            merged[col] = enr[col]
        elif col in ENRICHMENT_COLUMNS:
            merged[col] = enr[col].combine_first(merged[col])
        else:
            merged[col] = merged[col].combine_first(enr[col])

    merged["property_id"] = merged.apply(
        lambda r: normalize_property_id(r.get("property_id")),
        axis=1,
    )

    # Prefer enriched timestamps when present
    if "full_timestamp" in merged.columns:
        merged["transaction_datetime_src"] = merged["full_timestamp"].combine_first(merged.get("instance_date"))
    else:
        merged["transaction_datetime_src"] = merged.get("instance_date")

    merged.index.name = "transaction_id"
    return merged.reset_index()


def transform_properties_and_locations(conn, merged: pd.DataFrame, user_ids: set[str]) -> set[str]:
    df = merged.copy()
    df["property_id_n"] = df["property_id"].map(normalize_property_id)
    df["tx_dt"] = pd.to_datetime(df["transaction_datetime_src"], errors="coerce")
    df = df.dropna(subset=["property_id_n"])
    df = df.sort_values(["property_id_n", "tx_dt"])

    prop_rows = []
    loc_rows = []
    seen_deed: set[str] = set()
    seen_survey: set[str] = set()

    for pid, group in df.groupby("property_id_n", sort=False):
        r = group.iloc[-1]
        deed = clean_str(getattr(r, "title_deed_number", None))
        survey = clean_str(getattr(r, "survey_plan_number", None))
        if deed and deed in seen_deed:
            deed = f"{deed}-{pid[:8]}"
        if survey and survey in seen_survey:
            survey = f"{survey}-{pid[:8]}"
        if deed:
            seen_deed.add(deed)
        if survey:
            seen_survey.add(survey)

        # Prefer latest row that has a known owner_id (enrichment may not be on last tx)
        owner_id = None
        for cand in reversed(list(group.itertuples(index=False))):
            oid = clean_str(getattr(cand, "owner_id", None))
            if oid in user_ids:
                owner_id = oid
                break

        prop_rows.append({
            "property_id": pid,
            "title_deed_number": deed,
            "property_name": clean_str(getattr(r, "property_name", None)),
            "address": clean_str(getattr(r, "area_name", None)),
            "district": clean_str(getattr(r, "area_name", None)),
            "city": "Dubai",
            "latitude": to_float(getattr(r, "gps_latitude", None)),
            "longitude": to_float(getattr(r, "gps_longitude", None)),
            "land_area": to_float(getattr(r, "procedure_area", None)),
            "area_unit": "sqm",
            "land_type": clean_str(getattr(r, "land_use_zone", None)) or clean_str(getattr(r, "property_usage", None)),
            "survey_plan_number": survey,
            "current_owner_id": owner_id,
            "current_usage_type": clean_str(getattr(r, "property_usage", None)),
            "current_subtype": clean_str(getattr(r, "property_sub_type", None)),
            "current_value": to_float(getattr(r, "actual_worth", None)),
            "legal_status": clean_str(getattr(r, "legal_status", None)),
            "verification_status": clean_str(getattr(r, "verification_status", None)),
            "encumbrances": clean_str(getattr(r, "encumbrances", None)),
            "boundary_north": clean_str(getattr(r, "boundary_north", None)),
            "boundary_south": clean_str(getattr(r, "boundary_south", None)),
            "boundary_east": clean_str(getattr(r, "boundary_east", None)),
            "boundary_west": clean_str(getattr(r, "boundary_west", None)),
        })
        loc_rows.append({
            "property_id": pid,
            "district": clean_str(getattr(r, "area_name", None)),
            "city": "Dubai",
            "latitude": to_float(getattr(r, "gps_latitude", None)),
            "longitude": to_float(getattr(r, "gps_longitude", None)),
            "area_name": clean_str(getattr(r, "area_name", None)),
            "building_name": clean_str(getattr(r, "building_name", None)),
            "project_name": clean_str(getattr(r, "project_name", None)),
            "master_project": clean_str(getattr(r, "master_project", None)),
            "nearest_landmark": clean_str(getattr(r, "nearest_landmark", None)),
            "nearest_metro": clean_str(getattr(r, "nearest_metro", None)),
            "nearest_mall": clean_str(getattr(r, "nearest_mall", None)),
        })

    _write_df(conn, "properties", prop_rows)
    _write_df(conn, "locations", loc_rows)
    return {r["property_id"] for r in prop_rows}


def transform_transaction_types(conn, merged: pd.DataFrame) -> dict[str, int]:
    names = sorted({
        clean_str(x)
        for x in merged.get("procedure_name", pd.Series(dtype=str)).tolist()
        + merged.get("reg_type", pd.Series(dtype=str)).tolist()
        if clean_str(x)
    })
    rows = [{"transaction_type_name": n, "description": n} for n in names]
    _write_df(conn, "transaction_types", rows)
    mapping_df = _read(conn, f"SELECT transaction_type_id, transaction_type_name FROM {MAIN}.transaction_types")
    return dict(zip(mapping_df["transaction_type_name"], mapping_df["transaction_type_id"]))


def transform_transactions(conn, merged: pd.DataFrame, property_ids: set[str], type_map: dict[str, int]) -> set[str]:
    rows = []
    seen: set[str] = set()
    for r in merged.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        pid = normalize_property_id(getattr(r, "property_id", None))
        if tid is None or pid is None or tid in seen or pid not in property_ids:
            continue
        seen.add(tid)
        tname = clean_str(getattr(r, "procedure_name", None)) or clean_str(getattr(r, "reg_type", None))
        tx_dt = to_timestamp(getattr(r, "transaction_datetime_src", None)) or to_timestamp(getattr(r, "instance_date", None))
        rows.append({
            "transaction_id": tid,
            "property_id": pid,
            "transaction_type_id": type_map.get(tname) if tname else None,
            "transaction_group": clean_str(getattr(r, "trans_group", None)),
            "registration_type": clean_str(getattr(r, "reg_type", None)),
            "procedure_name": clean_str(getattr(r, "procedure_name", None)),
            "transaction_datetime": tx_dt,
            "transaction_value": to_float(getattr(r, "actual_worth", None)),
            "previous_value": to_float(getattr(r, "previous_value", None)),
            "value_change_pct": to_float(getattr(r, "value_change_pct", None)),
            "procedure_area": to_float(getattr(r, "procedure_area", None)),
            "meter_sale_price": to_float(getattr(r, "meter_sale_price", None)),
            "currency": "AED",
            "status": "Completed",
            "procedure_id": clean_str(getattr(r, "procedure_id", None)),
            "trans_group_id": clean_str(getattr(r, "trans_group_id", None)),
            "area_id": clean_str(getattr(r, "area_id", None)),
            "area_name": clean_str(getattr(r, "area_name", None)),
            "project_number": clean_str(getattr(r, "project_number", None)),
            "project_name": clean_str(getattr(r, "project_name", None)),
            "master_project": clean_str(getattr(r, "master_project", None)),
            "nearest_landmark": clean_str(getattr(r, "nearest_landmark", None)),
            "rooms": clean_str(getattr(r, "rooms", None)),
            "has_parking": to_bool(getattr(r, "has_parking", None)),
            "created_at": tx_dt or datetime.utcnow(),
        })

    _write_df(conn, "property_transactions", rows)
    return {r["transaction_id"] for r in rows}


def transform_ownership(conn, merged: pd.DataFrame, property_ids: set[str], tx_ids: set[str]) -> None:
    df = merged.copy()
    df["property_id_n"] = df["property_id"].map(normalize_property_id)
    df["tx_dt"] = pd.to_datetime(df["transaction_datetime_src"], errors="coerce")
    df = df.dropna(subset=["property_id_n"]).sort_values(["property_id_n", "tx_dt", "transaction_id"])

    rows = []

    for pid, group in df.groupby("property_id_n", sort=False):
        if pid not in property_ids:
            continue
        prev_idx = None
        for r in group.itertuples(index=False):
            tid = clean_str(r.transaction_id)
            owner_id = clean_str(getattr(r, "owner_id", None))
            start = to_date(getattr(r, "instance_date", None)) or (
                to_timestamp(getattr(r, "transaction_datetime_src", None)).date()
                if to_timestamp(getattr(r, "transaction_datetime_src", None)) else None
            )
            if prev_idx is not None:
                rows[prev_idx]["ownership_end_date"] = start
                rows[prev_idx]["ownership_status"] = "Closed"
            rows.append({
                "property_id": pid,
                "owner_id": owner_id,
                "ownership_start_date": start,
                "ownership_end_date": None,
                "ownership_type": clean_str(getattr(r, "procedure_name", None)) or "Transfer",
                "transaction_id": tid if tid in tx_ids else None,
                "ownership_status": "Current",
            })
            prev_idx = len(rows) - 1

    _write_df(conn, "property_ownership_history", rows)


def transform_parties(conn, merged: pd.DataFrame, tx_ids: set[str], user_ids: set[str]) -> None:
    rows = []
    seen: set[tuple] = set()

    def add(tid, role, user_id=None, name=None, primary=False):
        if tid not in tx_ids:
            return
        uid = clean_str(user_id)
        pname = clean_str(name)
        if uid is None and pname is None:
            return
        if uid is not None and uid not in user_ids:
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

    for r in merged.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        if tid is None:
            continue
        add(tid, "Owner", getattr(r, "owner_id", None), getattr(r, "owner_name", None), primary=True)
        add(tid, "Seller", getattr(r, "seller_id", None), getattr(r, "seller_name", None))
        add(tid, "Notary", None, getattr(r, "notary_name", None))
        add(tid, "Witness", None, getattr(r, "witness_1_name", None))
        add(tid, "Witness", None, getattr(r, "witness_2_name", None))

    _write_df(conn, "transaction_parties", rows)


def transform_registration(conn, merged: pd.DataFrame, tx_ids: set[str]) -> None:
    rows = []
    seen: set[str] = set()
    for r in merged.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        if tid is None or tid not in tx_ids or tid in seen:
            continue
        seen.add(tid)
        rows.append({
            "transaction_id": tid,
            "registration_number": clean_str(getattr(r, "title_deed_number", None)),
            "registration_date": to_date(getattr(r, "instance_date", None)),
            "registration_fee": to_float(getattr(r, "registration_fee_aed", None)),
            "tax_amount": None,
            "other_fee": to_float(getattr(r, "trustee_office_fee_aed", None)),
            "total_amount_paid": to_float(getattr(r, "total_fees_paid_aed", None)),
            "currency": "AED",
            "registration_status": clean_str(getattr(r, "verification_status", None)) or "Registered",
        })
    _write_df(conn, "registration_details", rows)


def transform_documents(conn, merged: pd.DataFrame, property_ids: set[str], tx_ids: set[str]) -> dict[str, int]:
    rows = []
    tx_to_doc: dict[str, int] = {}
    for r in merged.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        pid = normalize_property_id(getattr(r, "property_id", None))
        if tid not in tx_ids or pid not in property_ids:
            continue
        doc_text = clean_str(getattr(r, "document_text", None))
        # Prefer existing document_hash; else keep plain document_text (app hashes later)
        doc_hash = prefer_existing_or_plain(getattr(r, "document_hash", None), doc_text)
        if doc_text is None and doc_hash is None:
            continue
        rows.append({
            "property_id": pid,
            "transaction_id": tid,
            "document_type": "Title Deed",
            "document_number": clean_str(getattr(r, "title_deed_number", None)),
            "document_text": doc_text,
            "document_hash": doc_hash,
            "document_url": None,
            "issued_date": to_date(getattr(r, "instance_date", None)),
            "verification_status": clean_str(getattr(r, "verification_status", None)),
            "created_at": to_timestamp(getattr(r, "transaction_datetime_src", None)) or datetime.utcnow(),
        })

    if rows:
        pd.DataFrame(rows).to_sql(
            "property_documents", conn, schema=MAIN, if_exists="append", index=False, method="multi", chunksize=1000
        )
        docs = _read(conn, f"SELECT document_id, transaction_id FROM {MAIN}.property_documents")
        tx_to_doc = dict(zip(docs["transaction_id"], docs["document_id"]))
        print(f"  {MAIN}.property_documents: {len(rows):,}")
    else:
        print(f"  {MAIN}.property_documents: 0")
    return tx_to_doc


def transform_blockchain(conn, merged: pd.DataFrame, property_ids: set[str], tx_ids: set[str]) -> None:
    bc = _read(conn, "SELECT * FROM staging.blockchain")
    rows = []
    seen_hash: set[str] = set()

    # Index merged enrichment blockchain fields by transaction_id
    merged_bc = {}
    for r in merged.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        if tid:
            merged_bc[tid] = r

    def add_row(tid, pid, tx_hash, r_src):
        if tx_hash is None or tx_hash in seen_hash:
            return
        if tid is not None and tid not in tx_ids:
            tid = None
        if pid is not None and pid not in property_ids:
            pid = None
        seen_hash.add(tx_hash)
        rows.append({
            "transaction_id": tid,
            "property_id": pid,
            "tx_hash": tx_hash,
            "previous_hash": clean_str(getattr(r_src, "previous_transaction_hash", None)),
            "property_hash": clean_str(getattr(r_src, "property_hash", None)),
            "block_number": to_int(getattr(r_src, "block_number", None)),
            "block_timestamp": to_timestamp(getattr(r_src, "block_timestamp", None)),
            "from_wallet": clean_str(getattr(r_src, "from_wallet", None)),
            "to_wallet": clean_str(getattr(r_src, "to_wallet", None)),
            "transaction_type": clean_str(getattr(r_src, "transaction_type", None)),
            "transaction_value": to_float(getattr(r_src, "transaction_value_aed", None)),
            "smart_contract_address": clean_str(getattr(r_src, "smart_contract_address", None)),
            "digital_signature": clean_str(getattr(r_src, "digital_signature", None)),
            "transaction_status": clean_str(getattr(r_src, "transaction_status", None)),
            "consensus_verification": clean_str(getattr(r_src, "consensus_verification", None)),
            "gas_fee": to_float(getattr(r_src, "gas_fee_aed", None)),
            "created_at": to_timestamp(getattr(r_src, "block_timestamp", None)) or datetime.utcnow(),
        })

    for r in bc.itertuples(index=False):
        tid = clean_str(r.transaction_id)
        pid = normalize_property_id(r.property_id)
        tx_hash = clean_str(r.blockchain_transaction_hash)
        add_row(tid, pid, tx_hash, r)

    # Supplement from merged enrichment where ledger row may be missing
    for tid, r in merged_bc.items():
        tx_hash = clean_str(getattr(r, "blockchain_transaction_hash", None))
        if tx_hash:
            pid = normalize_property_id(getattr(r, "property_id", None))
            add_row(tid, pid, tx_hash, r)

    _write_df(conn, "blockchain_transactions", rows)


def transform_transaction_features(
    conn, merged: pd.DataFrame, property_ids: set[str], tx_ids: set[str], tx_to_doc: dict[str, int]
) -> None:
    df = merged.copy()
    df["property_id_n"] = df["property_id"].map(normalize_property_id)
    df["tx_dt"] = pd.to_datetime(df["transaction_datetime_src"], errors="coerce")
    df = df.dropna(subset=["property_id_n", "transaction_id"])
    df["transaction_id"] = df["transaction_id"].map(clean_str)
    df = df[df["transaction_id"].isin(tx_ids) & df["property_id_n"].isin(property_ids)]
    df = df.sort_values(["property_id_n", "tx_dt", "transaction_id"])

    df["actual_worth_f"] = df["actual_worth"].map(to_float)
    df["procedure_area_f"] = df["procedure_area"].map(to_float)
    df["price_per_area"] = df["actual_worth_f"] / df["procedure_area_f"]
    df.loc[df["procedure_area_f"].isna() | (df["procedure_area_f"] == 0), "price_per_area"] = pd.NA

    area_medians = (
        df.groupby(df["area_name"].fillna("UNKNOWN"))["price_per_area"]
        .median()
        .to_dict()
    )

    rows = []
    for pid, group in df.groupby("property_id_n", sort=False):
        group = group.reset_index(drop=True)
        tx_dts = group["tx_dt"]
        for i in range(len(group)):
            r = group.iloc[i]
            tid = r["transaction_id"]
            tx_dt = r["tx_dt"]
            prop_hist_len = i + 1
            if pd.notna(tx_dt):
                last_90 = int(((tx_dts <= tx_dt) & (tx_dts >= tx_dt - pd.Timedelta(days=90))).sum())
                last_365 = int(((tx_dts <= tx_dt) & (tx_dts >= tx_dt - pd.Timedelta(days=365))).sum())
                prev = tx_dts[tx_dts < tx_dt]
                days_since = int((tx_dt - prev.max()).days) if len(prev) else None
            else:
                last_90 = last_365 = 0
                days_since = None

            doc_text = clean_str(r.get("document_text"))
            doc_hash = clean_str(r.get("document_hash"))
            doc_count = 1 if doc_text or doc_hash else 0
            enc = clean_str(r.get("encumbrances"))
            has_encumbrance = enc is not None and enc.lower() not in {"none", "clear", "no encumbrances"}
            owner_id = clean_str(r.get("owner_id"))
            seller_id = clean_str(r.get("seller_id"))
            seller_matches = owner_id == seller_id if owner_id and seller_id else None
            prev_hash = clean_str(r.get("previous_transaction_hash"))
            tx_hash = clean_str(r.get("blockchain_transaction_hash"))
            hash_chain_valid = bool(prev_hash and tx_hash)

            area = str(r.get("area_name") or "UNKNOWN")
            median = area_medians.get(area)
            ppa = to_float(r.get("price_per_area"))
            deviation = ((ppa - median) / median * 100) if ppa and median and not pd.isna(median) else None

            rows.append({
                "transaction_id": tid,
                "property_id": pid,
                "price_per_area": ppa,
                "price_deviation_from_area_median": deviation,
                "ownership_change_count": prop_hist_len,
                "transactions_last_90_days": int(last_90),
                "transactions_last_365_days": int(last_365),
                "days_since_previous_transaction": days_since,
                "value_change_pct": to_float(r.get("value_change_pct")),
                "document_count": doc_count,
                "missing_document_count": 0 if doc_count else 1,
                "hash_chain_valid": hash_chain_valid,
                "seller_matches_owner": seller_matches,
                "has_active_encumbrance": has_encumbrance,
                "duplicate_document_count": 0,
            })

    _write_df(conn, "transaction_features", rows)


def transform_query_logs_and_retrievals(conn, tx_ids: set[str], tx_to_doc: dict[str, int], user_ids: set[str]) -> None:
    ql = _read(conn, "SELECT * FROM staging.query_logs")

    log_rows = []
    retrieval_rows = []
    seen: set[str] = set()

    for r in ql.itertuples(index=False):
        qid = clean_str(r.query_id)
        if qid is None or qid in seen:
            continue
        seen.add(qid)
        uid = clean_str(r.user_id)
        if uid not in user_ids:
            uid = None
        relevance = to_float(r.relevance_score)
        latency = to_int(r.response_latency_ms)
        log_rows.append({
            "query_id": qid,
            "user_id": uid,
            "query_text": clean_str(r.query_text),
            "log_timestamp": datetime.utcnow() - timedelta(milliseconds=latency or 0),
            "agent_response": f"Retrieved relevant property records for query {qid}.",
            "confidence_score": relevance,
            "relevance_score": relevance,
            "flagged_suspicious": to_bool(r.flagged_suspicious) or False,
            "agent_used": "IR-Agent",
            "response_time_ms": latency,
        })

        for rank, tx_id in enumerate(split_csv_ids(r.retrieved_transaction_ids), start=1):
            tid = clean_str(tx_id)
            if tid and tid not in tx_ids:
                tid = None
            retrieval_rows.append({
                "query_id": qid,
                "transaction_id": tid,
                "document_id": tx_to_doc.get(tid) if tid else None,
                "rank": rank,
                "relevance_score": relevance,
            })

    _write_df(conn, "query_logs", log_rows)
    _write_df(conn, "query_retrievals", retrieval_rows)


def run_all_transforms(conn) -> None:
    print("Clearing main tables…")
    _clear_final_tables(conn)

    print("Loading users (system seeds + staging stakeholders)…")
    user_ids = transform_users(conn)

    print("Reading staging sources…")
    transactions = _read(conn, "SELECT * FROM staging.transactions")
    enriched = _read(conn, "SELECT * FROM staging.property_enriched")

    print("Merging transactions + enrichment on transaction_id…")
    merged = merge_transaction_sources(transactions, enriched)
    print(f"  merged transaction rows: {len(merged):,}")

    print("Transforming into main.* …")
    property_ids = transform_properties_and_locations(conn, merged, user_ids)
    type_map = transform_transaction_types(conn, merged)
    tx_ids = transform_transactions(conn, merged, property_ids, type_map)
    transform_ownership(conn, merged, property_ids, tx_ids)
    transform_parties(conn, merged, tx_ids, user_ids)
    transform_registration(conn, merged, tx_ids)
    tx_to_doc = transform_documents(conn, merged, property_ids, tx_ids)
    transform_blockchain(conn, merged, property_ids, tx_ids)
    transform_transaction_features(conn, merged, property_ids, tx_ids, tx_to_doc)
    transform_query_logs_and_retrievals(conn, tx_ids, tx_to_doc, user_ids)
    print("Transforms complete.")
    print("  (Category C runtime tables left empty: risk_assessments, risk_indicators, agent_runs)")
