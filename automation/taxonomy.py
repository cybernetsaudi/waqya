"""
IPTC Media Topics taxonomy helpers (international news classification standard).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

TAXONOMY_PATH = Path(__file__).parent / "iptc_taxonomy.yaml"


def load_taxonomy() -> dict:
    with open(TAXONOMY_PATH) as f:
        return yaml.safe_load(f)


def topic_keys() -> list[str]:
    return list(load_taxonomy().get("topics", {}).keys())


def topic_catalog_for_prompt() -> str:
    """Compact list for LLM classification prompts."""
    tax = load_taxonomy()
    lines = []
    for key, t in tax.get("topics", {}).items():
        lines.append(f"- {key}: {t['label']} ({t['iptc_code']})")
    return "\n".join(lines)


def resolve_topic(
    iptc_topic: str,
    feed_category: str | None = None,
) -> dict:
    """
    Return topic record: key, iptc_code, label, wp_category.
    Falls back to feed map then default.
    """
    tax = load_taxonomy()
    topics = tax.get("topics", {})
    key = (iptc_topic or "").strip().lower().replace(" ", "_").replace("-", "_")

    if key not in topics:
        # fuzzy: match prefix
        for k in topics:
            if key.startswith(k[:8]) or k.startswith(key[:8]):
                key = k
                break

    if key not in topics and feed_category:
        mapped = tax.get("feed_category_map", {}).get(feed_category.strip().lower())
        if mapped and mapped in topics:
            key = mapped

    if key not in topics:
        key = tax.get("default_topic", "society")

    t = topics[key]
    return {
        "topic_key": key,
        "iptc_code": t["iptc_code"],
        "iptc_label": t["label"],
        "wp_category": t["wp_category"],
        "description": t.get("description", ""),
    }


def normalize_tags(raw_tags: list[str], regions: list[str] | None = None, max_tags: int = 12) -> list[str]:
    """Dedupe and clean tags for WordPress (dc:subject / keyword tags)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(tag: str) -> None:
        tag = re.sub(r"\s+", " ", tag.strip())
        if len(tag) < 2 or len(tag) > 48:
            return
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            out.append(tag)

    for t in raw_tags:
        for part in re.split(r"[,;|]", t):
            add(part)

    for r in regions or []:
        add(r)

    return out[:max_tags]
