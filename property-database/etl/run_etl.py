"""Run full ETL: staging already loaded → transform into 12 final tables."""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python etl/run_etl.py` from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from db import get_engine
from transform import run_all_transforms


def main():
    engine = get_engine()
    # One transaction: failure rolls back all final-table writes
    with engine.begin() as conn:
        run_all_transforms(conn)
    print("ETL finished successfully.")


if __name__ == "__main__":
    main()
