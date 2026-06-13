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

# Too vague for Yoast “previously used” / relevance — always re-derive from headline
GENERIC_FOCUS_KEYWORDS = frozenset(
    {
        "ai",
        "eu",
        "uk",
        "us",
        "war",
        "news",
        "world news",
        "politics",
        "business",
        "technology",
        "science",
        "health",
        "sport",
        "religion",
    }
)


def _slugify(text: str) -> str:
    text = wp_plain_text(text).lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text.strip())
    return re.sub(r"-+", "-", text).strip("-")[:180]


def _phrase_from_headline(headline: str) -> str:
    """Extract a specific 2–3 word keyphrase from the headline when possible."""
    h = wp_plain_text(headline)
    low = h.lower()

    if "pope" in low and re.search(r"\bai\b|artificial intelligence|disarmament", low):
        return "AI disarmament"
    if re.search(r"\bdisarmament\s+of\s+ai\b", low):
        return "AI disarmament"

    m = re.search(
        r"\b(disarmament|regulation|ban|crackdown|sanctions|tariffs?)\s+of\s+([a-z][a-z0-9-]{1,20})\b",
        low,
    )
    if m:
        noun = m.group(2)
        if noun == "ai":
            return "AI disarmament"
        return f"{m.group(1)} of {noun}"[:35]

    m = re.search(
        r"\b([a-z][a-z0-9-]{2,20}(?:\s+[a-z][a-z0-9-]{2,20})?)\s+"
        r"(?:war|conflict|crisis|summit|election|vote|strike|attack)\b",
        low,
    )
    if m:
        return m.group(1)[:35]

    if re.search(r"\bartificial intelligence\b", low):
        return "artificial intelligence"
    if re.search(r"\bai\b", low):
        return "artificial intelligence"
    if "trump" in low:
        return "Donald Trump" if "donald" in low else "Trump"
    if "iran" in low:
        return "Iran"
    if "gaza" in low or "israel" in low:
        return "Gaza" if "gaza" in low else "Israel"

    # Two capitalized words from headline
    caps = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", h)
    for c in caps:
        if c.lower() not in ("the", "waqya", "breaking") and len(c) <= 30:
            return c

    return ""


def suggest_focus_keyword(
    *,
    headline: str = "",
    summary: str = "",
    primary_key: str = "",
    topic_tags: list[str] | None = None,
    tags: list[str] | None = None,
    subjects: list[str] | None = None,
    parsed_focus: str = "",
    used_focus: set[str] | None = None,
) -> str:
    """Pick a short Yoast keyphrase (1–3 words) aligned with the story."""
    if parsed_focus:
        focus = wp_plain_text(parsed_focus).strip()
        if 2 <= len(focus) <= 40:
            return _dedupe_focus(focus, headline, used_focus)

    phrase = _phrase_from_headline(headline)
    if phrase:
        return _dedupe_focus(phrase, headline, used_focus)

    for source in (topic_tags or [], tags or [], subjects or []):
        for item in source:
            phrase = wp_plain_text(str(item)).strip()
            if not phrase or len(phrase) > 35:
                continue
            words = phrase.split()
            if 1 <= len(words) <= 3 and phrase.lower() not in STOPWORDS:
                return _dedupe_focus(phrase.lower(), headline, used_focus)

    if primary_key and primary_key in DESK_FOCUS:
        return _dedupe_focus(DESK_FOCUS[primary_key], headline, used_focus)

    text = f"{headline} {summary}".lower()
    for key, cat_kw in DESK_FOCUS.items():
        if key.replace("-", " ") in text or cat_kw.lower() in text:
            return _dedupe_focus(cat_kw, headline, used_focus)

    words = [w for w in re.findall(r"[a-z]{4,}", text) if w not in STOPWORDS]
    if len(words) >= 2:
        a, b = words[0], words[1]
        # Avoid nonsense like "Brexit brexits" from near-duplicate tokens.
        if a[:5] == b[:5]:
            return _dedupe_focus(a, headline, used_focus)
        return _dedupe_focus(f"{a} {b}", headline, used_focus)
    if words:
        return _dedupe_focus(words[0], headline, used_focus)
    return "world news"


def is_strong_focus(focus: str, headline: str = "") -> bool:
    """Whether an existing focus keyphrase is worth keeping on backfill."""
    focus = wp_plain_text(focus).strip()
    if len(focus) < 4 or len(focus) > 40:
        return False
    low = focus.lower()
    if low in GENERIC_FOCUS_KEYWORDS:
        return False
    if len(focus.split()) > 4:
        return False
    if low.endswith((" before", " after", " too late", " news")):
        return False
    if re.search(r"\b(your|delay|stunning|disappointments|toaster)\b", low):
        return False
    if headline:
        h = wp_plain_text(headline).lower()
        tokens = [t for t in re.findall(r"[a-z0-9]+", low) if len(t) > 2]
        if tokens and not all(t in h for t in tokens):
            return False
    return True


def _dedupe_focus(focus: str, headline: str, used: set[str] | None) -> str:
    """Avoid reusing the same focus keyphrase on another post (Yoast duplicate check)."""
    if not used:
        return focus
    key = focus.lower().strip()
    if key not in used:
        used.add(key)
        return focus
    focus_tokens = set(key.replace("-", " ").split())
    headline_words = [
        w
        for w in re.findall(r"[a-z]{4,}", wp_plain_text(headline).lower())
        if w not in STOPWORDS and w not in focus_tokens
    ]
    for word in headline_words[:8]:
        variant = f"{focus} {word.title()}"[:40].strip()
        vk = variant.lower()
        if vk not in used and vk != key:
            used.add(vk)
            return variant
    variant = f"{focus} analysis"[:40]
    used.add(variant.lower())
    return variant


def fetch_used_focus_keywords(base: str, auth: tuple[str, str], pages: int = 8) -> set[str]:
    import requests

    used: set[str] = set()
    for page in range(1, pages + 1):
        try:
            resp = requests.get(
                f"{base.rstrip('/')}/wp-json/wp/v2/posts",
                params={
                    "status": "publish",
                    "per_page": 100,
                    "page": page,
                    "context": "edit",
                    "_fields": "meta",
                },
                auth=auth,
                timeout=45,
            )
            if resp.status_code == 400:
                break
            resp.raise_for_status()
            batch = resp.json()
        except Exception:
            break
        if not batch:
            break
        for post in batch:
            meta = post.get("meta") or {}
            kw = (meta.get("_yoast_wpseo_focuskw") or "").strip().lower()
            if kw:
                used.add(kw)
        if page >= int(resp.headers.get("X-WP-TotalPages", 1)):
            break
    return used


def build_seo_title(focus: str, headline: str, max_len: int = 55) -> str:
    """SEO title: keyphrase first, within Yoast pixel-friendly length."""
    focus = wp_plain_text(focus).strip()
    headline = wp_plain_text(headline).strip()
    if not headline:
        return focus[:max_len]

    lower_h = headline.lower()
    lower_f = focus.lower()
    focus_tokens = [t for t in re.findall(r"[a-z0-9]+", lower_f) if len(t) > 2]

    if lower_h.startswith(lower_f):
        title = headline
    elif lower_f in lower_h:
        title = headline
    elif focus_tokens and all(t in lower_h for t in focus_tokens):
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
    low = text.lower()
    f_low = focus.lower()
    if f_low not in low and not (f_low == "ai" and " ai" in f" {low}"):
        lead = focus[0].upper() + focus[1:] if focus else ""
        text = f"{lead}: {text}" if lead else text

    text = re.sub(r"\s+", " ", text).strip()
    suffix = "Analysis and context from Waqya commentary."
    parts = [
        p.strip()
        for p in re.split(
            r"\s*Analysis and context from Waqya commentary\.?\s*",
            text,
            flags=re.I,
        )
        if p.strip()
    ]
    text = parts[0] if parts else text
    if len(text) < min_len:
        text = f"{text} {suffix}".strip()
    elif suffix.lower() not in text.lower():
        text = f"{text} {suffix}".strip()

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
            "How Waqya writes and publishes commentary: sourcing, quality gates, "
            "independence, and corrections. Read our editorial standards."
        ),
        "focuskw": "editorial policy",
    },
    "corrections": {
        "seo_title": "Corrections | Waqya",
        "metadesc": (
            "Report a factual error on Waqya. We correct mistakes promptly with "
            "timestamps and transparent updates to affected articles."
        ),
        "focuskw": "corrections",
    },
    "about": {
        "seo_title": "About Waqya | News Commentary",
        "metadesc": (
            "Waqya (واقعة) is independent world-news commentary — 33+ desks, "
            "quality-gated publishing, and analysis built for readers who want context."
        ),
        "focuskw": "about Waqya",
    },
    "contact": {
        "seo_title": "Contact Waqya",
        "metadesc": (
            "Contact Waqya for corrections, press, and partnerships. Corrections are "
            "prioritised within 24 hours. Press and feedback welcome."
        ),
        "focuskw": "contact",
    },
    "privacy-policy": {
        "seo_title": "Privacy Policy | Waqya",
        "metadesc": (
            "How Waqya uses cookies, analytics, and email data. GDPR and CCPA-friendly "
            "practices — your choices for tracking and the weekly digest."
        ),
        "focuskw": "privacy policy",
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
