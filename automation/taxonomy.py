"""
Waqya taxonomy — IPTC-aligned editorial categories (v2).

Loads automation/waqya_categories.yaml (source of truth).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import yaml

CATEGORIES_PATH = Path(__file__).parent / "waqya_categories.yaml"
LEGACY_IPTC_PATH = Path(__file__).parent / "iptc_taxonomy.yaml"


def load_categories() -> dict:
    with open(CATEGORIES_PATH) as f:
        return yaml.safe_load(f)


def primary_keys() -> list[str]:
    return list(load_categories().get("primary_categories", {}).keys())


def primary_catalog_for_prompt() -> str:
    lines = []
    for key, cat in load_categories().get("primary_categories", {}).items():
        group = cat.get("menu_group", "")
        lines.append(f"- {key}: {cat['label']} [{group}]")
    return "\n".join(lines)


def region_tags_list() -> list[str]:
    return list(load_categories().get("region_tags", []))


def topic_tags_list() -> list[str]:
    return list(load_categories().get("topic_tags", []))


def resolve_primary(
    primary_key: str,
    feed_category: str | None = None,
) -> dict:
    """Return primary category record for WordPress + meta."""
    data = load_categories()
    primaries = data.get("primary_categories", {})
    key = (primary_key or "").strip().lower().replace(" ", "_").replace("-", "_")

    if key not in primaries:
        for k in primaries:
            if key.startswith(k[:10]) or k.startswith(key[:10]):
                key = k
                break

    if key not in primaries and feed_category:
        mapped = data.get("feed_category_map", {}).get(feed_category.strip().lower())
        if mapped and mapped in primaries:
            key = mapped

    if key not in primaries:
        key = data.get("default_primary", "current-affairs")

    cat = primaries[key]
    return {
        "primary_key": key,
        "label": cat["label"],
        "slug": cat["slug"],
        "wp_category": cat["label"],
        "iptc_code": cat.get("iptc_reference", ""),
        "menu_group": cat.get("menu_group", ""),
        "description": cat.get("description", ""),
    }


# Backwards compatibility for older imports
def load_taxonomy() -> dict:
    return load_categories()


def topic_catalog_for_prompt() -> str:
    return primary_catalog_for_prompt()


def topic_keys() -> list[str]:
    return primary_keys()


def resolve_topic(iptc_topic: str, feed_category: str | None = None) -> dict:
    """Map old iptc_topic key or primary key to unified record."""
    r = resolve_primary(iptc_topic, feed_category)
    return {
        "topic_key": r["primary_key"],
        "iptc_code": r["iptc_code"],
        "iptc_label": r["label"],
        "wp_category": r["wp_category"],
        "description": r.get("description", ""),
    }


def normalize_tags(
    raw_tags: list[str],
    regions: list[str] | None = None,
    topic_tags: list[str] | None = None,
    max_tags: int = 15,
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []

    def add(tag: str) -> None:
        tag = re.sub(r"\s+", " ", tag.strip())
        if len(tag) < 2 or len(tag) > 48:
            return
        k = tag.lower()
        if k not in seen:
            seen.add(k)
            out.append(tag)

    for t in raw_tags:
        for part in re.split(r"[,;|]", t):
            add(part)
    for r in regions or []:
        add(r)
    for t in topic_tags or []:
        add(t)

    return out[:max_tags]


def get_scrape_keywords() -> dict[str, list[str]]:
    """primary_key -> keywords for trending boost."""
    out = {}
    for key, cat in load_categories().get("primary_categories", {}).items():
        kws = cat.get("scrape_keywords", [])
        if kws:
            out[key] = kws
    return out
