"""Shared DB connection helpers."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[1]


def get_engine():
    load_dotenv(ROOT / ".env")
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is missing. Copy .env.example to .env and set it, e.g.\n"
            "DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/property_db"
        )
    return create_engine(url)
