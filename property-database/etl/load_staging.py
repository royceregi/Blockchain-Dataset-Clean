"""Load cleaned CSVs into staging schema tables (truncate + append)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import ROOT, get_engine

DATA_DIR = ROOT / "data" / "cleaned"
FALLBACK_DATA_DIR = ROOT.parent / "preprocessing" / "data" / "cleaned"

LOAD_MAP = [
    # staging.users → main.users (stakeholders); system JWT users also seeded in ETL
    ("users_stakeholders_cleaned.csv", "staging.users"),
    ("property_enriched_cleaned.csv", "staging.property_enriched"),
    ("transactions_cleaned.csv", "staging.transactions"),
    ("blockchain_ledger_cleaned.csv", "staging.blockchain"),
    ("query_logs_cleaned.csv", "staging.query_logs"),
]


def _resolve_data_dir() -> Path:
    if DATA_DIR.exists() and any(DATA_DIR.glob("*.csv")):
        return DATA_DIR
    if FALLBACK_DATA_DIR.exists():
        return FALLBACK_DATA_DIR
    return DATA_DIR


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=True)


def _staging_columns(conn, table_name: str) -> list[str]:
    schema, name = table_name.split(".", 1)
    return (
        pd.read_sql(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = :schema
                  AND table_name = :table
                  AND column_name NOT IN ('staging_id', 'loaded_at')
                ORDER BY ordinal_position
                """
            ),
            conn,
            params={"schema": schema, "table": name},
        )["column_name"]
        .tolist()
    )


def load_csv(engine, filename: str, table_name: str, data_dir: Path) -> int:
    path = data_dir / filename
    if not path.exists():
        raise FileNotFoundError(path)

    df = _read_csv(path)

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY"))

    with engine.connect() as conn:
        staging_cols = _staging_columns(conn, table_name)

    keep = [c for c in staging_cols if c in df.columns]
    missing = [c for c in staging_cols if c not in df.columns]
    if missing:
        print(f"  note: {table_name} staging columns missing from CSV (left NULL): {missing}")

    out = df[keep].copy()
    out.to_sql(
        table_name.split(".", 1)[1],
        engine,
        schema=table_name.split(".", 1)[0],
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )
    print(f"Loaded {len(out):,} rows → {table_name}")
    return len(out)


def main():
    engine = get_engine()
    data_dir = _resolve_data_dir()
    print(f"Using data directory: {data_dir}")
    total = 0
    for filename, table in LOAD_MAP:
        total += load_csv(engine, filename, table, data_dir)
    print(f"Done. Total staging rows written: {total:,}")


if __name__ == "__main__":
    main()
