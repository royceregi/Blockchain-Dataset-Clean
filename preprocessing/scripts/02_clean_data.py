import numpy as np
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from schemas import clean_text_columns, normalize_columns, parse_datetime

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path("data/cleaned")
REPORT_DIR = Path("reports")
CLEAN_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

STUDY_START = "2021-01-01"
STUDY_END = "2023-12-31"

SUMMARY = []


def save_cleaned(df: pd.DataFrame, name: str) -> pd.DataFrame:
    output = CLEAN_DIR / name
    df.to_csv(output, index=False)
    SUMMARY.append({"dataset": name, "rows": len(df), "columns": len(df.columns)})
    return df


def clean_transactions() -> pd.DataFrame:
    raw_file = RAW_DIR / "Transactions.csv"
    df = pd.read_csv(raw_file, low_memory=False)
    original_rows = len(df)

    df = normalize_columns(df)
    df["instance_date"] = parse_datetime(df["instance_date"])
    invalid_dates = int(df["instance_date"].isna().sum())
    df = df[df["instance_date"].between(STUDY_START, STUDY_END)].copy()

    exact_duplicates = int(df.duplicated().sum())
    df = df.drop_duplicates()

    duplicate_transaction_ids = 0
    if "transaction_id" in df.columns:
        duplicate_transaction_ids = int(df["transaction_id"].duplicated().sum())
        df = df.drop_duplicates(subset=["transaction_id"], keep="first")

    df = clean_text_columns(df)

    numeric_cols = [
        "procedure_area", "actual_worth", "meter_sale_price",
        "rent_value", "meter_rent_price",
        "no_of_parties_role_1", "no_of_parties_role_2", "no_of_parties_role_3",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["procedure_area", "actual_worth", "meter_sale_price", "rent_value", "meter_rent_price"]:
        if col in df.columns:
            df.loc[df[col] < 0, col] = np.nan

    for col in ["property_type", "property_sub_type", "property_usage", "reg_type", "trans_group"]:
        if col in df.columns:
            df[col] = df[col].astype("string").str.replace(r"\s+", " ", regex=True)

    identity_cols = [c for c in [
        "area_name", "building_name", "project_number", "project_name",
        "property_type", "property_sub_type",
    ] if c in df.columns]
    if identity_cols:
        identity = df[identity_cols].fillna("UNKNOWN").astype(str).agg("|".join, axis=1)
        df["property_id"] = pd.util.hash_pandas_object(identity, index=False).astype("uint64").astype(str)

    SUMMARY.extend([
        {"metric": "transactions_original_rows", "value": original_rows},
        {"metric": "transactions_invalid_dates", "value": invalid_dates},
        {"metric": "transactions_exact_duplicates", "value": exact_duplicates},
        {"metric": "transactions_duplicate_ids", "value": duplicate_transaction_ids},
        {"metric": "transactions_final_rows", "value": len(df)},
    ])
    return save_cleaned(df, "transactions_cleaned.csv")


def clean_generic_csv(filename: str, output_name: str, date_cols: list[str] | None = None) -> pd.DataFrame:
    raw_file = RAW_DIR / filename
    if not raw_file.exists():
        return pd.DataFrame()

    df = pd.read_csv(raw_file, low_memory=False)
    original_rows = len(df)
    df = normalize_columns(df)
    df = df.drop_duplicates()
    df = clean_text_columns(df)

    if date_cols:
        for col in date_cols:
            if col in df.columns:
                df[col] = parse_datetime(df[col])

    SUMMARY.extend([
        {"metric": f"{output_name}_original_rows", "value": original_rows},
        {"metric": f"{output_name}_final_rows", "value": len(df)},
    ])
    return save_cleaned(df, output_name)


def main() -> None:
    clean_transactions()

    enriched_source = RAW_DIR / "dubai_property_MERGED_enriched.csv"
    if enriched_source.exists():
        enriched = pd.read_csv(enriched_source, low_memory=False)
        enriched = normalize_columns(enriched)
        enriched["instance_date"] = parse_datetime(enriched["instance_date"])
        enriched = enriched[enriched["instance_date"].between(STUDY_START, STUDY_END)].copy()
        enriched = enriched.drop_duplicates(subset=["transaction_id"], keep="first")
        enriched = clean_text_columns(enriched)
        save_cleaned(enriched, "property_enriched_cleaned.csv")

    clean_generic_csv(
        "blockchain_transaction_ledger_dubai.csv",
        "blockchain_ledger_cleaned.csv",
        date_cols=["block_timestamp"],
    )
    clean_generic_csv(
        "users_stakeholders_dubai.csv",
        "users_stakeholders_cleaned.csv",
    )
    clean_generic_csv(
        "query_interaction_logs_dubai.csv",
        "query_logs_cleaned.csv",
    )

    query_file = CLEAN_DIR / "query_logs_cleaned.csv"
    if query_file.exists():
        query_df = pd.read_csv(query_file, low_memory=False)
        query_df = normalize_columns(query_df)
        if "timestamp" not in query_df.columns:
            seed = pd.util.hash_pandas_object(
                query_df.get("query_id", pd.Series(range(len(query_df)))),
                index=False,
            )
            start = pd.Timestamp("2021-01-01")
            end = pd.Timestamp("2023-12-31")
            span = (end - start).total_seconds()
            offsets = (seed % int(span)).astype(int)
            query_df["timestamp"] = start + pd.to_timedelta(offsets, unit="s")
            query_df.to_csv(query_file, index=False)

    pd.DataFrame(SUMMARY).to_csv(REPORT_DIR / "cleaning_summary.csv", index=False)
    print("Cleaning completed.")
    print(f"Output directory: {CLEAN_DIR.resolve()}")


if __name__ == "__main__":
    main()
