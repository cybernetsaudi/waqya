"""
Editorial quality gate — rule-based score before publish (no extra API cost).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from generator import Article

_TABLOID_CLICHES = (
    "shockwaves",
    "sparking outrage",
    "sparking international",
    "slams",
    "blasts",
    "perfect for fans",
    "game-changer",
    "game changer",
    "sent shockwaves",
    "raises eyebrows",
    "left wondering",
    "you won't believe",
)

_SEO_SLOP = (
    "frames the debate here",
    "is at the centre of this story",
    "is at the center of this story",
    "that tension around",
    "observers say",
    "will shape the debate for months",
    "who benefits if",
    "dominates the agenda",
)


@dataclass
class QualityResult:
    score: int
    notes: list[str] = field(default_factory=list)
    is_breaking: bool = False
    publish_recommended: bool = True


def _load_pipeline_cfg(config: dict) -> dict:
    return config.get("pipeline", {})


def _breaking_cfg(config: dict) -> dict:
    return config.get("breaking", {})


def _normalize_title(text: str) -> str:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _title_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, _normalize_title(a), _normalize_title(b)).ratio()


def _count_markdown_h2(body: str) -> int:
    return len(re.findall(r"^##\s+", body, re.M))


def _tabloid_hits(text: str) -> list[str]:
    lower = text.lower()
    return [phrase for phrase in _TABLOID_CLICHES if phrase in lower]


def _seo_slop_hits(text: str) -> list[str]:
    lower = text.lower()
    return [phrase for phrase in _SEO_SLOP if phrase in lower]


def score_article(article: Article, story: dict | None, config: dict) -> QualityResult:
    """Score 0–100. Higher = safer to auto-publish."""
    pipe = _load_pipeline_cfg(config)
    breaking_cfg = _breaking_cfg(config)
    notes: list[str] = []
    score = 50

    body = article.body or ""
    words = len(re.findall(r"\w+", body))
    title = article.headline or ""
    source_title = article.source_title or (story or {}).get("title", "")

    if words >= 600:
        score += 15
        notes.append(f"Length OK ({words} words)")
    elif words >= 500:
        score += 8
        notes.append(f"Acceptable length ({words} words)")
    elif words >= 400:
        score += 5
        notes.append(f"Short ({words} words)")
    else:
        score -= 25
        notes.append(f"Too short ({words} words)")

    if 400 <= words < 500:
        score -= 5
        notes.append("Below 500-word editorial target")

    if 40 <= len(title) <= 65:
        score += 10
    elif 40 <= len(title) <= 90:
        score += 5
        notes.append("Headline long (>65 chars)")
    else:
        score -= 8
        notes.append("Headline length suboptimal")

    if article.excerpt and len(article.excerpt) > 40:
        score += 5
    if article.meta_description and len(article.meta_description) > 50:
        score += 5

    if article.source_url and article.source_name:
        score += 10
        notes.append("Source attributed")
    else:
        score -= 15
        notes.append("Missing source metadata")

    if story and story.get("url"):
        score += 5

    if article.category and article.category != "current-affairs":
        score += 5
        notes.append(f"Desk: {article.category}")

    if article.waqya_read and article.waqya_read.count("|") >= 2:
        score += 8
        notes.append("Waqya Read present")

    h2_count = _count_markdown_h2(body)
    if h2_count >= 2:
        score += 5
    elif h2_count == 1:
        score -= 5
        notes.append("Only one subheading")
    else:
        score -= 12
        notes.append("Missing ## subheadings")

    if source_title:
        sim = _title_similarity(title, source_title)
        if sim >= 0.78:
            score -= 18
            notes.append(f"Headline too close to source ({sim:.0%})")
        elif sim >= 0.65:
            score -= 6
            notes.append(f"Headline resembles source ({sim:.0%})")

    tabloid = _tabloid_hits(title + " " + body[:800])
    if tabloid:
        score -= min(20, 8 * len(tabloid))
        notes.append(f"Tabloid phrasing: {', '.join(tabloid[:3])}")

    slop = _seo_slop_hits(body)
    if slop:
        score -= min(15, 5 * len(slop))
        notes.append("SEO boilerplate detected")

    if article.article_format == "on_the_record":
        score += 5
        notes.append("On The Record format")
        if "##" in body:
            score += 3

    ai_slop = ["as an ai", "as a language model", "i cannot", "openai"]
    lower = body.lower()
    if any(p in lower for p in ai_slop):
        score -= 30
        notes.append("AI disclaimer detected")

    trend = float((story or {}).get("trend_score", 0))
    is_breaking = False
    if breaking_cfg.get("enabled", True):
        desks = set(breaking_cfg.get("desks", ["war-conflict", "middle-east", "current-affairs"]))
        min_trend = float(breaking_cfg.get("min_trend_score", 7))
        if article.category in desks and trend >= min_trend:
            is_breaking = True
            score += 5
            notes.append("Breaking candidate")

    min_publish = int(pipe.get("require_min_quality_score", 78))
    draft_below = int(pipe.get("always_draft_below_score", 55))
    score = max(0, min(100, score))
    publish_recommended = score >= min_publish and score >= draft_below

    return QualityResult(
        score=score,
        notes=notes,
        is_breaking=is_breaking,
        publish_recommended=publish_recommended,
    )


def resolve_post_status(quality: QualityResult, config: dict) -> str:
    """Return WordPress status: publish or draft."""
    pipe = _load_pipeline_cfg(config)
    draft_below = int(pipe.get("always_draft_below_score", 55))

    if quality.score < draft_below:
        return "draft"

    if not pipe.get("auto_publish", True):
        return "draft"

    mode = pipe.get("publish_mode", "quality_gated")
    if mode == "draft":
        return "draft"
    if mode == "quality_gated" and not quality.publish_recommended:
        return "draft"
    if mode == "auto":
        return "publish"

    return "publish" if quality.publish_recommended else "draft"
