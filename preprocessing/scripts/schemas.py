"""Mandatory column schemas and mapping helpers for finalized datasets."""

from __future__ import annotations

import hashlib
from typing import Iterable

import numpy as np
import pandas as pd

PLACEHOLDER_VALUES = ["", "NA", "N/A", "na", "n/a", "null", "NULL", "-", "--", "UNKNOWN", "null"]

PROPERTY_COLUMNS = [
    "Property_ID",
    "Property_Name",
    "Property_Group_ID",
    "Group_Name",
    "Title_Deed_Number",
    "Owner_Name",
    "Owner_ID",
    "Owner_NIC",
    "Property_Address",
    "Nearest_Landmark",
    "Land_Extent_Area",
    "Procedural_Area_Type",
    "Current_Usage_Type",
    "Previous_Usage_Type",
    "Current_Subtype",
    "Property_Subtype",
    "Land_Boundaries",
    "Registration_Type",
    "Registration_Year",
    "Registration_Month",
    "Registration_Quarter",
    "Registration_Date",
    "Registration_Day",
    "Registration_Time",
    "Notary_Name",
    "Witness_Details",
    "Registration_Fees_Paid",
    "Stamp_Duty_Taxes_Paid",
    "Current_Value",
    "Previous_Value",
    "Previous_Owners",
    "Legal_Status",
    "Encumbrances",
    "Document_Text",
    "Document_Hash",
    "Verification_Status",
    "Survey_Plan_Number",
]

BLOCKCHAIN_COLUMNS = [
    "Transaction_ID",
    "Block_Number",
    "Tx_Year",
    "Tx_Month",
    "Tx_Quarter",
    "Tx_Date",
    "Tx_Day",
    "Tx_Time",
    "Property_ID",
    "From_Wallet",
    "To_Wallet",
    "Transaction_Type",
    "Smart_Contract_Address",
    "Transaction_Status",
    "Digital_Signature",
    "Consensus_Verification",
]

USERS_COLUMNS = [
    "User_ID",
    "Role",
    "Name_Contact",
    "Wallet_Address",
    "Auth_Credentials_Hashed",
    "Associated_Property_IDs",
    "Data_Access_Scope",
    "KYC_Status",
    "Access_Level",
]

QUERY_COLUMNS = [
    "Query_ID",
    "User_ID",
    "Query_Text",
    "Log_Year",
    "Log_Month",
    "Log_Quarter",
    "Log_Date",
    "Log_Day",
    "Log_Time",
    "Retrieved_Document_IDs",
    "Agent_Response",
    "Confidence_Score",
    "Flagged_Suspicious",
]


def format_property_id(series: pd.Series) -> pd.Series:
    def fmt(value):
        if pd.isna(value):
            return pd.NA
        try:
            return str(int(float(value)))
        except (ValueError, TypeError):
            return str(value)

    return series.apply(fmt)


def sha256_text(value) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = (
        out.columns.str.strip()
        .str.lower()
        .str.replace(r"[^a-z0-9_]+", "_", regex=True)
        .str.strip("_")
    )
    return out


def clean_text_series(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    return cleaned.replace(PLACEHOLDER_VALUES, pd.NA)


def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    text_cols = out.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        out[col] = clean_text_series(out[col])
    return out


def parse_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def quarter_label(month: pd.Series) -> pd.Series:
    return month.map({1: "Q1", 2: "Q1", 3: "Q1", 4: "Q2", 5: "Q2", 6: "Q2",
                      7: "Q3", 8: "Q3", 9: "Q3", 10: "Q4", 11: "Q4", 12: "Q4"})


def split_timestamp(ts: pd.Series | None, prefix: str) -> dict[str, pd.Series]:
    if ts is None:
        empty = pd.Series(dtype="object")
        return {
            f"{prefix}_Year": empty,
            f"{prefix}_Month": empty,
            f"{prefix}_Quarter": empty,
            f"{prefix}_Date": empty,
            f"{prefix}_Day": empty,
            f"{prefix}_Time": empty,
        }

    dt = parse_datetime(ts)
    return {
        f"{prefix}_Year": dt.dt.year,
        f"{prefix}_Month": dt.dt.month,
        f"{prefix}_Quarter": quarter_label(dt.dt.month),
        f"{prefix}_Date": dt.dt.day,
        f"{prefix}_Day": dt.dt.day_name(),
        f"{prefix}_Time": dt.dt.strftime("%H:%M:%S"),
    }


def ensure_columns(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            out[col] = pd.NA
    return out[columns]


def compose_address(row: pd.Series) -> str | None:
    parts = []
    for key in ("building_name", "project_name", "area_name", "master_project"):
        value = row.get(key)
        if pd.notna(value):
            parts.append(str(value))
    if not parts:
        return pd.NA
    return ", ".join(dict.fromkeys(parts))


def compose_boundaries(row: pd.Series) -> str | None:
    parts = []
    mapping = {
        "North": row.get("boundary_north"),
        "South": row.get("boundary_south"),
        "East": row.get("boundary_east"),
        "West": row.get("boundary_west"),
    }
    for direction, value in mapping.items():
        if pd.notna(value):
            parts.append(f"{direction}: {value}")
    return "; ".join(parts) if parts else pd.NA


def compose_witness_details(row: pd.Series) -> str | None:
    witnesses = []
    for key in ("witness_1_name", "witness_2_name"):
        value = row.get(key)
        if pd.notna(value):
            witnesses.append(str(value))
    return "; ".join(witnesses) if witnesses else pd.NA


def build_property_records(df: pd.DataFrame) -> pd.DataFrame:
    src = normalize_columns(df)
    instance_date = parse_datetime(src.get("instance_date", src.get("full_timestamp")))
    reg_year = src.get("year", instance_date.dt.year)
    reg_month = src.get("month", instance_date.dt.month)
    reg_quarter = src.get("quarter")
    if reg_quarter is not None:
        reg_quarter = reg_quarter.map(lambda q: f"Q{int(q)}" if pd.notna(q) else pd.NA)
    else:
        reg_quarter = quarter_label(reg_month)

    out = pd.DataFrame({
        "Property_ID": format_property_id(src["property_id"]) if "property_id" in src.columns else pd.NA,
        "Property_Name": src.get("property_name", src.get("project_name")),
        "Property_Group_ID": src.get("property_group", src.get("project_number")),
        "Group_Name": src.get("property_group", src.get("project_name")),
        "Title_Deed_Number": src.get("title_deed_number"),
        "Owner_Name": src.get("owner_name"),
        "Owner_ID": src.get("owner_id"),
        "Owner_NIC": src.get("owner_nic"),
        "Property_Address": src.apply(compose_address, axis=1),
        "Nearest_Landmark": src.get("nearest_landmark"),
        "Land_Extent_Area": src.get("procedure_area"),
        "Procedural_Area_Type": src.get("land_use_zone", src.get("property_type")),
        "Current_Usage_Type": src.get("property_usage"),
        "Previous_Usage_Type": src.get("previous_usage_type"),
        "Current_Subtype": src.get("property_sub_type"),
        "Property_Subtype": src.get("property_sub_type"),
        "Land_Boundaries": src.apply(compose_boundaries, axis=1),
        "Registration_Type": src.get("reg_type", src.get("procedure_name")),
        "Registration_Year": reg_year,
        "Registration_Month": reg_month,
        "Registration_Quarter": reg_quarter,
        "Registration_Date": src.get("day_of_month", instance_date.dt.day),
        "Registration_Day": src.get("day_of_week", instance_date.dt.day_name()),
        "Registration_Time": src.get("transaction_time", instance_date.dt.strftime("%H:%M:%S")),
        "Notary_Name": src.get("notary_name"),
        "Witness_Details": src.apply(compose_witness_details, axis=1),
        "Registration_Fees_Paid": src.get("total_fees_paid_aed", src.get("registration_fee_aed")),
        "Stamp_Duty_Taxes_Paid": src.get("registration_fee_aed"),
        "Current_Value": src.get("actual_worth"),
        "Previous_Value": src.get("previous_value"),
        "Previous_Owners": src.get("seller_name"),
        "Legal_Status": src.get("legal_status"),
        "Encumbrances": src.get("encumbrances"),
        "Document_Text": src.get("document_text"),
        "Document_Hash": src.get("document_hash", src.get("property_hash")),
        "Verification_Status": src.get("verification_status"),
        "Survey_Plan_Number": src.get("survey_plan_number"),
    })
    return ensure_columns(out, PROPERTY_COLUMNS)


def build_blockchain_ledger(df: pd.DataFrame) -> pd.DataFrame:
    src = normalize_columns(df)
    ts = parse_datetime(src.get("block_timestamp", src.get("timestamp", src.get("instance_date"))))
    tx_parts = split_timestamp(ts, "Tx")

    out = pd.DataFrame({
        "Transaction_ID": src.get("blockchain_transaction_hash", src.get("transaction_id")),
        "Block_Number": src.get("block_number"),
        **tx_parts,
        "Property_ID": format_property_id(src["property_id"]) if "property_id" in src.columns else pd.NA,
        "From_Wallet": src.get("from_wallet", src.get("seller_wallet_address")),
        "To_Wallet": src.get("to_wallet", src.get("owner_wallet_address")),
        "Transaction_Type": src.get("transaction_type", src.get("procedure_name", src.get("trans_group"))),
        "Smart_Contract_Address": src.get("smart_contract_address"),
        "Transaction_Status": src.get("transaction_status", "Confirmed"),
        "Digital_Signature": src.get("digital_signature", src.get("blockchain_transaction_hash")),
        "Consensus_Verification": src.get("consensus_verification", "Confirmed by Validators"),
    })
    return ensure_columns(out, BLOCKCHAIN_COLUMNS)


def build_users_stakeholders(df: pd.DataFrame, property_df: pd.DataFrame | None = None) -> pd.DataFrame:
    src = normalize_columns(df)

    associated = pd.Series(pd.NA, index=src.index, dtype="object")
    if property_df is not None:
        prop = normalize_columns(property_df)
        if "owner_id" in prop.columns and "property_id" in prop.columns:
            grouped = (
                prop.dropna(subset=["owner_id"])
                .groupby("owner_id")["property_id"]
                .apply(lambda values: ", ".join(sorted({str(v) for v in values if pd.notna(v)})))
            )
            associated = src.get("user_id").map(grouped)

    name_contact = src.get("full_name", pd.Series(pd.NA, index=src.index)).astype("string")
    for col in ("email", "phone_number", "owner_nic"):
        if col in src.columns:
            contact = src[col].astype("string")
            name_contact = name_contact + " | " + contact.fillna("")

    out = pd.DataFrame({
        "User_ID": src.get("user_id"),
        "Role": src.get("role"),
        "Name_Contact": name_contact.str.strip(" |"),
        "Wallet_Address": src.get("wallet_address"),
        "Auth_Credentials_Hashed": src.get("auth_password_hash"),
        "Associated_Property_IDs": associated,
        "Data_Access_Scope": src.get("access_level", "Standard"),
        "KYC_Status": src.get("kyc_status"),
        "Access_Level": src.get("access_level"),
    })
    return ensure_columns(out, USERS_COLUMNS)


def build_query_logs(df: pd.DataFrame) -> pd.DataFrame:
    src = normalize_columns(df)
    if "timestamp" in src.columns:
        ts = src["timestamp"]
    else:
        seed = pd.util.hash_pandas_object(
            src.get("query_id", pd.Series(range(len(src)))),
            index=False,
        )
        start = pd.Timestamp("2021-01-01")
        end = pd.Timestamp("2023-12-31")
        span = int((end - start).total_seconds())
        offsets = (seed % span).astype(int)
        ts = start + pd.to_timedelta(offsets, unit="s")
    log_parts = split_timestamp(ts, "Log")

    out = pd.DataFrame({
        "Query_ID": src.get("query_id"),
        "User_ID": src.get("user_id"),
        "Query_Text": src.get("query_text"),
        **log_parts,
        "Retrieved_Document_IDs": src.get(
            "retrieved_document_ids",
            src.get("retrieved_transaction_ids"),
        ),
        "Agent_Response": src.get("agent_response_summary", src.get("agent_response")),
        "Confidence_Score": src.get("relevance_score", src.get("confidence_score")),
        "Flagged_Suspicious": src.get("flagged_suspicious"),
    })
    return ensure_columns(out, QUERY_COLUMNS)
