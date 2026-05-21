"""
HTML entity helpers — WordPress REST often returns entities; avoid double-escaping.
"""

from __future__ import annotations

import re
from html import escape, unescape

_ENTITY_RE = re.compile(r"&#\d+;|&#x[0-9a-fA-F]+;|&amp;|&quot;|&apos;|&nbsp;|&rsquo;|&lsquo;|&rdquo;|&ldquo;")


def decode_entities(text: str, *, max_passes: int = 4) -> str:
    """Decode HTML entities until stable (handles double-encoding)."""
    if not text:
        return ""
    out = text
    for _ in range(max_passes):
        nxt = unescape(out)
        if nxt == out:
            break
        out = nxt
    return out


def wp_plain_text(raw: str) -> str:
    """Strip tags and decode entities for display or storage."""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", "", raw)
    return decode_entities(text).strip()


def has_html_entities(text: str) -> bool:
    return bool(_ENTITY_RE.search(text))


def safe_html_text(text: str) -> str:
    """Plain text safe to embed inside HTML elements."""
    return escape(wp_plain_text(text))
