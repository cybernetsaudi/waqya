"""Normalize story URLs for deduplication."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_STRIP_QUERY_PREFIXES = ("utm_", "fbclid", "gclid", "mc_cid", "mc_eid")


def normalize_story_url(url: str) -> str:
    """Canonical URL for dedup (scheme + host + path, no tracking query)."""
    url = (url or "").strip()
    if not url:
        return ""
    try:
        parsed = urlparse(url.lower())
    except Exception:
        return url.lower().rstrip("/")

    query = parse_qs(parsed.query, keep_blank_values=False)
    filtered = []
    for key, vals in sorted(query.items()):
        if any(key.startswith(p) for p in _STRIP_QUERY_PREFIXES):
            continue
        filtered.append((key, vals[0] if vals else ""))
    new_query = urlencode(filtered) if filtered else ""

    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme or "https", parsed.netloc, path, "", new_query, ""))


def url_fingerprint(url: str) -> str:
    norm = normalize_story_url(url)
    if not norm:
        return ""
    return hashlib.sha256(norm.encode()).hexdigest()[:20]
