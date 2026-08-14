"""Load cleaned CSVs into pre-created staging tables (truncate + append)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import ROOT, get_engine

DATA_DIR = ROOT / "data" / "cleaned"

LOAD_MAP = [
    ("users_stakeholders_cleaned.csv", "staging_users"),
    ("property_enriched_cleaned.csv", "staging_property_enriched"),
    ("transactions_cleaned.csv", "staging_transactions"),
    ("blockchain_ledger_cleaned.csv", "staging_blockchain"),
    ("query_logs_cleaned.csv", "staging_query_logs"),
]


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def load_csv(engine, filename: str, table_name: str) -> int:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(path)

    df = _read_csv(path)

    with engine.begin() as conn:
        # Keep schema from sql/02_staging_tables.sql; only refresh data.
        conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY"))

    # Only write columns that exist in both CSV and staging table
    with engine.connect() as conn:
        staging_cols = (
            pd.read_sql(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = :t
                      AND column_name NOT IN ('staging_id', 'loaded_at')
                    ORDER BY ordinal_position
                    """
                ),
                conn,
                params={"t": table_name},
            )["column_name"]
            .tolist()
        )

    keep = [c for c in staging_cols if c in df.columns]
    missing = [c for c in staging_cols if c not in df.columns]
    if missing:
        print(f"  note: {table_name} staging columns missing from CSV (left NULL): {missing}")

    out = df[keep].copy()
    out.to_sql(
        table_name,
        engine,
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )
    print(f"Loaded {len(out):,} rows → {table_name}")
    return len(out)


def main():
    engine = get_engine()
    total = 0
    for filename, table in LOAD_MAP:
        total += load_csv(engine, filename, table)
    print(f"Done. Total staging rows written: {total:,}")


if __name__ == "__main__":
    main()
