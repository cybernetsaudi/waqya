"""
Yoast-oriented SEO helpers — focus keyphrase, titles, meta, slugs, image alt.
"""

from __future__ import annotations

import re
from html_utils import wp_plain_text

# Default 1–2 word focus keyphrase per desk (Yoast-friendly)
DESK_FOCUS: dict[str, str] = {
    "current-affairs": "world news",
    "war-conflict": "war",
    "politics-government": "politics",
    "diplomacy": "diplomacy",
    "elections": "elections",
    "immigration-migration": "immigration",
    "human-rights": "human rights",
    "crime-justice": "crime",
    "media-disinformation": "disinformation",
    "middle-east": "Middle East",
    "south-asia": "South Asia",
    "east-asia": "East Asia",
    "europe": "Europe",
    "united-kingdom": "United Kingdom",
    "united-states": "United States",
    "americas": "Latin America",
    "africa": "Africa",
    "russia-central-asia": "Russia",
    "indo-pacific": "Indo-Pacific",
    "religion-faith": "religion",
    "business-economy": "business",
    "markets-finance": "markets",
    "technology-ai": "technology",
    "science": "science",
    "health-medicine": "health",
    "climate-environment": "climate",
    "energy-resources": "energy",
    "society-culture": "society",
    "labour-work": "labour",
    "sport": "sport",
    "entertainment-arts": "entertainment",
    "education": "education",
    "disasters-emergencies": "disaster",
}

STOPWORDS = frozenset(
    "a an the and or but in on at to for of is are was were be been being "
    "that this with from by as it its".split()
)


def _slugify(text: str) -> str:
    text = wp_plain_text(text).lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return re.sub(r"-+", "-", text).strip("-")[:180]


def suggest_focus_keyword(
    *,
    headline: str = "",
    summary: str = "",
    primary_key: str = "",
    topic_tags: list[str] | None = None,
    tags: list[str] | None = None,
    subjects: list[str] | None = None,
    parsed_focus: str = "",
) -> str:
    """Pick a short Yoast keyphrase (1–3 words) aligned with the story."""
    if parsed_focus:
        focus = wp_plain_text(parsed_focus).strip()
        if 2 <= len(focus) <= 40:
            return focus

    for source in (topic_tags or [], tags or [], subjects or []):
        for item in source:
            phrase = wp_plain_text(str(item)).strip()
            if not phrase or len(phrase) > 35:
                continue
            words = phrase.split()
            if 1 <= len(words) <= 3 and phrase.lower() not in STOPWORDS:
                return phrase.lower()

    if primary_key and primary_key in DESK_FOCUS:
        return DESK_FOCUS[primary_key]

    text = f"{headline} {summary}".lower()
    for key, cat_kw in DESK_FOCUS.items():
        if key.replace("-", " ") in text or cat_kw.lower() in text:
            return cat_kw

    # Two meaningful words from headline
    words = [w for w in re.findall(r"[a-z]{4,}", text) if w not in STOPWORDS]
    if len(words) >= 2:
        return f"{words[0]} {words[1]}"
    if words:
        return words[0]
    return "news"


def build_seo_title(focus: str, headline: str, max_len: int = 55) -> str:
    """SEO title: keyphrase first, within Yoast pixel-friendly length."""
    focus = wp_plain_text(focus).strip()
    headline = wp_plain_text(headline).strip()
    if not headline:
        return focus[:max_len]

    lower_h = headline.lower()
    lower_f = focus.lower()
    if lower_h.startswith(lower_f):
        title = headline
    elif lower_f in lower_h:
        title = headline
    else:
        title = f"{focus}: {headline}"

    if len(title) <= max_len:
        return title

    trimmed = title[: max_len + 1].rsplit(" ", 1)[0].rstrip(".,;:-")
    return trimmed + "…" if trimmed else title[:max_len]


def build_meta_description(
    focus: str,
    meta: str,
    headline: str,
    *,
    min_len: int = 135,
    max_len: int = 155,
) -> str:
    """Meta description with keyphrase near the start, 135–155 chars."""
    focus = wp_plain_text(focus).strip()
    text = wp_plain_text(meta) or wp_plain_text(headline)
    if focus.lower() not in text.lower():
        lead = focus[0].upper() + focus[1:] if focus else ""
        text = f"{lead}: {text}" if lead else text

    text = re.sub(r"\s+", " ", text).strip()
    if len(text) < min_len:
        text = f"{text} Analysis and context from Waqya commentary.".strip()

    if len(text) <= max_len:
        return text

    cut = text[: max_len + 1].rsplit(" ", 1)[0].rstrip(".,;:")
    return cut + "…" if cut else text[:max_len]


def build_post_slug(focus: str, headline: str) -> str:
    """Slug includes keyphrase tokens when missing from headline slug."""
    focus_slug = _slugify(focus)
    headline_slug = _slugify(headline)
    if not headline_slug:
        return focus_slug
    focus_tokens = [t for t in focus_slug.split("-") if len(t) > 2]
    if focus_tokens and not any(t in headline_slug for t in focus_tokens):
        return f"{focus_slug}-{headline_slug}"[:200]
    return headline_slug[:200]


def build_image_alt(focus: str, headline: str, role: str = "photo") -> str:
    """Alt text with ≥ half of keyphrase words for Yoast image check."""
    focus = wp_plain_text(focus)
    headline = wp_plain_text(headline)[:70]
    alt = f"{focus} — {headline} ({role})"
    return alt[:125]


PAGE_SEO: dict[str, dict[str, str]] = {
    "editorial-policy": {
        "seo_title": "Editorial Policy | Waqya",
        "metadesc": (
            "How Waqya publishes news commentary: sourcing rules, automation standards, "
            "and when we hold stories for review before publishing."
        ),
        "focuskw": "editorial policy",
    },
    "corrections": {
        "seo_title": "Corrections | Waqya",
        "metadesc": (
            "Report a factual error on Waqya. We correct mistakes promptly and note "
            "material updates at the top of affected articles."
        ),
        "focuskw": "corrections",
    },
    "about": {
        "seo_title": "About Waqya | News Commentary",
        "metadesc": (
            "Waqya (واقعة) is an English commentary desk on world news — Middle East, "
            "tech, conflict, and markets with clear analysis."
        ),
        "focuskw": "about Waqya",
    },
    "contact": {
        "seo_title": "Contact Waqya",
        "metadesc": (
            "Contact Waqya for corrections, press inquiries, and partnerships. "
            "We respond to factual reports and editorial questions."
        ),
        "focuskw": "contact",
    },
}


def count_keyphrase(text: str, focus: str) -> int:
    text = wp_plain_text(text).lower()
    focus = focus.lower().strip()
    if not focus:
        return 0
    if " " in focus:
        return len(re.findall(re.escape(focus), text))
    return len(re.findall(rf"\b{re.escape(focus)}\b", text))
