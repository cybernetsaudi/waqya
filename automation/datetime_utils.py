"""
Parse source publish times for WordPress date_gmt fields.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional


def parse_source_datetime(value: str | None) -> Optional[datetime]:
    """Return UTC datetime from RSS/NewsAPI date strings."""
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    try:
        if re.match(r"^\d{10}$", raw):
            return datetime.fromtimestamp(int(raw), tz=timezone.utc)
        if re.match(r"^\d{13}$", raw):
            return datetime.fromtimestamp(int(raw) / 1000, tz=timezone.utc)
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, IndexError):
        return None


def gmt_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def source_date_gmt(value: str | None) -> Optional[str]:
    """WordPress REST date_gmt: YYYY-MM-DDTHH:MM:SS (no offset)."""
    dt = parse_source_datetime(value)
    if not dt:
        return None
    return dt.strftime("%Y-%m-%dT%H:%M:%S")
