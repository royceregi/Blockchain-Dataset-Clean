import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from schemas import (
    BLOCKCHAIN_COLUMNS,
    PROPERTY_COLUMNS,
    QUERY_COLUMNS,
    USERS_COLUMNS,
    build_blockchain_ledger,
    build_property_records,
    build_query_logs,
    build_users_stakeholders,
)

CLEAN_DIR = Path("data/cleaned")
FINAL_DIR = Path("data/finalized")
FINAL_DIR.mkdir(parents=True, exist_ok=True)

PROPERTY_INPUT = CLEAN_DIR / "property_features_ready.csv"
BLOCKCHAIN_INPUT = CLEAN_DIR / "blockchain_ledger_cleaned.csv"
USERS_INPUT = CLEAN_DIR / "users_stakeholders_cleaned.csv"
QUERY_INPUT = CLEAN_DIR / "query_logs_cleaned.csv"

OUTPUTS = {
    "property_land_title_records.csv": PROPERTY_COLUMNS,
    "blockchain_transaction_ledger.csv": BLOCKCHAIN_COLUMNS,
    "users_stakeholders.csv": USERS_COLUMNS,
    "query_interaction_logs.csv": QUERY_COLUMNS,
}


def finalize_dataframe(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = df.copy()
    text_cols = out.select_dtypes(include=["object", "string"]).columns
    for col in text_cols:
        out[col] = out[col].astype("string").str.strip()
    return out[columns]


def main() -> None:
    property_df = pd.read_csv(PROPERTY_INPUT, low_memory=False)
    property_final = finalize_dataframe(build_property_records(property_df), PROPERTY_COLUMNS)
    property_final.to_csv(FINAL_DIR / "property_land_title_records.csv", index=False)

    blockchain_final = finalize_dataframe(build_blockchain_ledger(property_df), BLOCKCHAIN_COLUMNS)
    blockchain_final.to_csv(FINAL_DIR / "blockchain_transaction_ledger.csv", index=False)

    users_df = pd.read_csv(USERS_INPUT, low_memory=False) if USERS_INPUT.exists() else pd.DataFrame()
    users_final = finalize_dataframe(build_users_stakeholders(users_df, property_df), USERS_COLUMNS)
    users_final.to_csv(FINAL_DIR / "users_stakeholders.csv", index=False)

    query_df = pd.read_csv(QUERY_INPUT, low_memory=False) if QUERY_INPUT.exists() else pd.DataFrame()
    query_final = finalize_dataframe(build_query_logs(query_df), QUERY_COLUMNS)
    query_final.to_csv(FINAL_DIR / "query_interaction_logs.csv", index=False)

    manifest = []
    for filename, columns in OUTPUTS.items():
        path = FINAL_DIR / filename
        df = pd.read_csv(path, low_memory=False)
        manifest.append({
            "file": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "mandatory_columns": ", ".join(columns),
            "missing_values": int(df.isna().sum().sum()),
        })

    pd.DataFrame(manifest).to_csv(FINAL_DIR / "finalized_manifest.csv", index=False)

    print("Finalized datasets created in:", FINAL_DIR.resolve())
    for row in manifest:
        print(f"- {row['file']}: {row['rows']:,} rows, {row['columns']} columns")


if __name__ == "__main__":
    main()
