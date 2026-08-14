"""Parsing helpers for messy cleaned CSV / staging text columns."""

from __future__ import annotations

import hashlib
import math
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
        # Prefer integer form when the value is numeric
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
    parsed = pd.to_datetime(s, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def to_time(val: Any):
    s = clean_str(val)
    if s is None:
        return None
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            continue
    return None


def to_timestamp(val: Any):
    s = clean_str(val)
    if s is None:
        return None
    parsed = pd.to_datetime(s, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def sha256_text(val: Any) -> Optional[str]:
    s = clean_str(val)
    if s is None:
        return None
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def username_from_user_id(user_id: str) -> str:
    return user_id.lower()
