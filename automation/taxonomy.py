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


def _keyword_in_text(keyword: str, text: str) -> bool:
    """Match whole words/phrases only (avoids 'war' in 'hantavirus')."""
    k = keyword.lower().strip()
    if not k:
        return False
    if " " in k:
        return k in text
    return re.search(rf"\b{re.escape(k)}\b", text) is not None


def suggest_primary_from_story(
    title: str,
    summary: str = "",
    feed_category: str | None = None,
) -> str:
    """
    Rule-based primary desk from keywords + feed hint.
    Prefer specific desks over current-affairs.
    """
    data = load_categories()
    primaries = data.get("primary_categories", {})
    text = f"{title} {summary}".lower()

    scores: dict[str, float] = {}
    for key, cat in primaries.items():
        if key == "current-affairs":
            continue
        score = 0.0
        for kw in cat.get("scrape_keywords", []):
            if _keyword_in_text(kw, text):
                score += 2.0 if " " in kw else 1.0
        label = cat.get("label", "").lower()
        if label and _keyword_in_text(label, text):
            score += 1.5
        if score > 0:
            scores[key] = score

    if feed_category:
        fc = feed_category.strip().lower()
        if fc in primaries and fc != "current-affairs":
            scores[fc] = scores.get(fc, 0) + 2.0
        mapped = data.get("feed_category_map", {}).get(fc)
        if mapped and mapped in primaries and mapped != "current-affairs":
            scores[mapped] = scores.get(mapped, 0) + 1.5

    if scores:
        return max(scores, key=scores.get)

    # Obvious cross-cutting signals when keywords miss
    signals: list[tuple[str, tuple[str, ...]]] = [
        ("crime-justice", (
            "murder",
            "stabbing",
            "manslaughter",
            "knife crime",
            "man charged",
            "woman charged",
            "police arrest",
            "found guilty",
            "sentenced to",
            "shooting",
            "homicide",
        )),
        ("war-conflict", ("war ", " airstrike", "missile", "ceasefire", "military", "invasion")),
        ("immigration-migration", ("immigrant", "migration", "asylum", "deportation", "border")),
        ("markets-finance", ("stock", "dow ", "nasdaq", "shares", "earnings", "ipo")),
        ("technology-ai", ("nvidia", "openai", "artificial intelligence", "semiconductor", "startup")),
        ("health-medicine", ("virus", "disease", "outbreak", "hospital", "vaccine", "cdc")),
        ("elections", ("election", "ballot", "by-election", "campaign", "poll")),
        ("diplomacy", ("diplomat", "summit", "sanctions", "treaty", "strait of")),
        ("sport", ("football", "cricket", "championship", "premier league", "olympic")),
        ("entertainment-arts", ("gaming", "nintendo", "playstation", "xbox", "console", "film")),
    ]
    for key, phrases in signals:
        if any(p in text for p in phrases):
            return key

    if feed_category:
        mapped = data.get("feed_category_map", {}).get(feed_category.strip().lower())
        if mapped and mapped in primaries:
            return mapped

    return data.get("default_primary", "current-affairs")


def resolve_primary(
    primary_key: str,
    feed_category: str | None = None,
    title: str | None = None,
    summary: str | None = None,
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

    if key not in primaries and (title or summary):
        key = suggest_primary_from_story(title or "", summary or "", feed_category)

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
    skip_labels = {
        c.get("label", "").lower()
        for c in load_categories().get("primary_categories", {}).values()
    }

    def add(tag: str) -> None:
        tag = re.sub(r"\s+", " ", tag.strip())
        if len(tag) < 2 or len(tag) > 48:
            return
        if tag.lower() in skip_labels:
            return  # category names are not WordPress tags
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
