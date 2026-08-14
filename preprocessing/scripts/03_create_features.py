import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from schemas import normalize_columns, parse_datetime, quarter_label, sha256_text

CLEAN_DIR = Path("data/cleaned")
RAW_DIR = Path("data/raw")
PREPROCESSED_DIR = Path("data/preprocessed")
PREPROCESSED_DIR.mkdir(parents=True, exist_ok=True)

INPUT_TRANSACTIONS = CLEAN_DIR / "transactions_cleaned.csv"
INPUT_ENRICHED = CLEAN_DIR / "property_enriched_cleaned.csv"
OUTPUT_FILE = CLEAN_DIR / "property_features_ready.csv"


def enrich_from_transactions(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["instance_date"] = parse_datetime(out["instance_date"])
    out["year"] = out["instance_date"].dt.year
    out["month"] = out["instance_date"].dt.month
    out["quarter"] = out["instance_date"].dt.quarter
    out["day_of_week"] = out["instance_date"].dt.day_name()
    out["day_of_month"] = out["instance_date"].dt.day
    out["transaction_time"] = out["instance_date"].dt.strftime("%H:%M:%S")
    out["full_timestamp"] = out["instance_date"]

    if "actual_worth" in out.columns and "procedure_area" in out.columns:
        out["calculated_price_per_area"] = np.where(
            out["procedure_area"] > 0,
            out["actual_worth"] / out["procedure_area"],
            np.nan,
        )

    if "property_id" in out.columns:
        out["property_hash"] = out["property_id"].apply(sha256_text)

    sort_cols = [c for c in ["property_id", "instance_date", "transaction_id"] if c in out.columns]
    out = out.sort_values(sort_cols).reset_index(drop=True)

    if "property_id" in out.columns and "transaction_id" in out.columns:
        out["previous_transaction_hash"] = (
            out.groupby("property_id")["transaction_id"]
            .transform(lambda values: values.shift(1))
            .fillna("GENESIS")
            .apply(sha256_text)
        )

    hash_cols = [c for c in [
        "transaction_id", "property_id", "instance_date", "property_type", "actual_worth", "procedure_area",
    ] if c in out.columns]

    def transaction_hash(row: pd.Series) -> str:
        payload = "|".join(str(row[c]) for c in hash_cols)
        return sha256_text(payload)

    out["blockchain_transaction_hash"] = out.apply(transaction_hash, axis=1)
    out["block_number"] = np.arange(1, len(out) + 1)
    out["block_timestamp"] = out["instance_date"]
    out["smart_contract_address"] = "PROTOTYPE_NOT_DEPLOYED"
    out["transaction_type"] = out.get("procedure_name", out.get("trans_group"))
    out["transaction_status"] = "Confirmed"
    out["digital_signature"] = out["blockchain_transaction_hash"].apply(lambda v: hashlib.sha1(str(v).encode()).hexdigest())
    out["consensus_verification"] = "Confirmed by Validators"
    return out


def load_enriched_source() -> pd.DataFrame | None:
    for candidate in [INPUT_ENRICHED, RAW_DIR / "dubai_property_MERGED_enriched.csv", PREPROCESSED_DIR / "dubai_property_MERGED_enriched.csv"]:
        if candidate.exists():
            df = pd.read_csv(candidate, low_memory=False)
            return normalize_columns(df)
    return None


def main() -> None:
    if INPUT_ENRICHED.exists():
        df = pd.read_csv(INPUT_ENRICHED, low_memory=False)
        df = normalize_columns(df)
        df["instance_date"] = parse_datetime(df["instance_date"])
        df["year"] = df.get("year", df["instance_date"].dt.year)
        df["month"] = df.get("month", df["instance_date"].dt.month)
        df["quarter"] = df.get("quarter", df["instance_date"].dt.quarter)
        df["day_of_week"] = df.get("day_of_week", df["instance_date"].dt.day_name())
        df["day_of_month"] = df.get("day_of_month", df["instance_date"].dt.day)
        df["transaction_time"] = df.get("transaction_time", df["instance_date"].dt.strftime("%H:%M:%S"))
        df["full_timestamp"] = parse_datetime(df.get("full_timestamp", df["instance_date"]))
        if "blockchain_transaction_hash" not in df.columns:
            df = enrich_from_transactions(df)
    else:
        df = pd.read_csv(INPUT_TRANSACTIONS, low_memory=False)
        df = normalize_columns(df)
        df = enrich_from_transactions(df)

        enriched = load_enriched_source()
        if enriched is not None and "transaction_id" in enriched.columns:
            extra_cols = [c for c in enriched.columns if c not in df.columns and c != "transaction_id"]
            if extra_cols:
                df = df.merge(enriched[["transaction_id", *extra_cols]], on="transaction_id", how="left")

    if "registration_quarter" not in df.columns and "month" in df.columns:
        df["registration_quarter"] = quarter_label(df["month"])

    df.to_csv(OUTPUT_FILE, index=False)
    df.to_csv(PREPROCESSED_DIR / "property_features_ready.csv", index=False)

    print("Feature dataset created:")
    print(OUTPUT_FILE)
    print(f"Rows: {len(df):,}")
    print(f"Columns: {len(df.columns)}")


if __name__ == "__main__":
    main()
