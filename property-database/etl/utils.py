"""Parsing helpers for messy cleaned CSV / staging text columns."""

from __future__ import annotations

import hashlib
import math
import re
from datetime import datetime
from typing import Any, Optional

import pandas as pd


def is_blank(val: Any) -> bool:
    if val is None:
        return True
    if isinstance(val, float) and math.isnan(val):
        return True
    s = str(val).strip()
    return s == "" or s.lower() in {"nan", "none", "null", "nat"}


def clean_str(val: Any) -> Optional[str]:
    if is_blank(val):
        return None
    return str(val).strip()


def normalize_property_id(val: Any) -> Optional[str]:
    """Canonical property_id string. Handles scientific notation and .0 suffixes."""
    s = clean_str(val)
    if s is None:
        return None
    try:
        return str(int(float(s)))
    except (ValueError, OverflowError):
        return s


def to_bool(val: Any) -> Optional[bool]:
    s = clean_str(val)
    if s is None:
        return None
    return s.lower() in {"1", "true", "t", "yes", "y"}


def to_int(val: Any) -> Optional[int]:
    s = clean_str(val)
    if s is None:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def to_float(val: Any) -> Optional[float]:
    s = clean_str(val)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def to_date(val: Any):
    s = clean_str(val)
    if s is None:
        return None
    parsed = pd.to_datetime(s, errors="coerce", utc=False)
    if pd.isna(parsed):
        return None
    return parsed.date()


def to_timestamp(val: Any):
    s = clean_str(val)
    if s is None:
        return None
    parsed = pd.to_datetime(s, errors="coerce", utc=False)
    if pd.isna(parsed):
        return None
    ts = parsed.to_pydatetime()
    return ts.replace(tzinfo=None) if ts.tzinfo else ts


def sha256_text(val: Any) -> Optional[str]:
    s = clean_str(val)
    if s is None:
        return None
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def prefer_existing_or_plain(existing: Any, plain: Any = None) -> Optional[str]:
    """Use an already-hashed/canonical value when present; otherwise keep plain text.

    App-side hashing can be applied later. Never invent a new hash here.
    """
    existing_s = clean_str(existing)
    if existing_s is not None:
        return existing_s
    return clean_str(plain)


def username_from_user_id(user_id: str) -> str:
    return user_id.lower()


def demo_password_hash(user_id: str) -> str:
    """Generate a deterministic demo password hash; never store raw dataset auth hashes."""
    salt = hashlib.sha256(f"propguard-demo-{user_id}".encode()).hexdigest()[:32]
    digest = hashlib.pbkdf2_hmac("sha256", b"PropGuardDemo2024!", salt.encode(), 10_000)
    return f"pbkdf2_sha256$10000${salt}${digest.hex()}"


def split_csv_ids(val: Any) -> list[str]:
    """Split comma/semicolon-separated ID lists from query logs."""
    s = clean_str(val)
    if s is None:
        return []
    parts = re.split(r"[,;|]+", s)
    return [p.strip() for p in parts if p.strip()]


def risk_level_from_score(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"
