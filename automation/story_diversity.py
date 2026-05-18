"""
Diversity-aware story selection — avoids echo-chamber clustering.

- Topic clusters: similar titles (Hantavirus ×8, Trump/China ×5) collapse to one pick
- Category quotas: spread picks across primary desks per run / per day
- Saturation: penalize topics already published recently on WordPress
- Stratified feeds: boost under-used RSS desk hints before pure trend rank
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

from taxonomy import load_categories, suggest_primary_from_story

log = logging.getLogger(__name__)

STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of is are was were be been being
    that this with from as by it its into over after before not no yes
    says said will can about up out new just more most other than when
    how what who which their they them his her she he we you your our
    has have had could would should may might also amid while during
    """.split()
)

# Tokens too generic to define a "story cluster"
GENERIC_TOKENS = frozenset(
    """
    news report reports latest update breaking global world international
    officials government minister president leader country countries
    people public health officials experts analysts say says told
    """.split()
)


@dataclass
class DiversityConfig:
    enabled: bool = True
    max_per_cluster_per_run: int = 1
    max_per_primary_per_run: int = 2
    min_distinct_primaries_per_run: int = 3
    cluster_overlap_threshold: float = 0.38
    recent_hours: int = 72
    trending_score_cap: float = 8.0
    saturation_penalty: float = 12.0
    primary_daily_cap: int = 3


def load_diversity_config(config: dict) -> DiversityConfig:
    raw = config.get("pipeline", {}).get("diversity", {})
    return DiversityConfig(
        enabled=raw.get("enabled", True),
        max_per_cluster_per_run=int(raw.get("max_per_cluster_per_run", 1)),
        max_per_primary_per_run=int(raw.get("max_per_primary_per_run", 2)),
        min_distinct_primaries_per_run=int(raw.get("min_distinct_primaries_per_run", 3)),
        cluster_overlap_threshold=float(raw.get("cluster_overlap_threshold", 0.38)),
        recent_hours=int(raw.get("recent_hours", 72)),
        trending_score_cap=float(raw.get("trending_score_cap", 8.0)),
        saturation_penalty=float(raw.get("saturation_penalty", 12.0)),
        primary_daily_cap=int(raw.get("primary_daily_cap", 3)),
    )


def topic_tokens(title: str, summary: str = "") -> set[str]:
    """Significant tokens for clustering (lowercase)."""
    text = f"{title} {summary}".lower()
    words = re.findall(r"[a-z][a-z0-9'-]{2,}", text)
    out: set[str] = set()
    for w in words:
        if w in STOPWORDS or w in GENERIC_TOKENS:
            continue
        if len(w) < 3:
            continue
        out.add(w)
    # Named entities / phrases: keep hyphenated and longer tokens
    for m in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", f"{title} {summary}"):
        phrase = m.lower().replace(" ", "_")
        if phrase not in STOPWORDS:
            out.add(phrase)
    return out


def cluster_key(title: str, summary: str = "") -> frozenset[str]:
    return frozenset(topic_tokens(title, summary))


def cluster_overlap(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def clusters_match(
    a: frozenset[str],
    b: frozenset[str],
    threshold: float,
) -> bool:
    if cluster_overlap(a, b) >= threshold:
        return True
    # Same distinctive rare token — avoid blocking all "trump/china" headlines.
    shared = a & b
    if not shared:
        return False
    for tok in shared:
        if len(tok) >= 9:
            return True
    return False


def fetch_recent_wp_clusters(hours: int) -> tuple[list[frozenset[str]], Counter[str]]:
    """
    Recent published post title clusters + primary slug counts (last N hours).
    Returns empty on API failure.
    """
    base = os.environ.get("WP_URL", "").rstrip("/")
    user = os.environ.get("WP_USER", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    if not base or not user or not password:
        return [], Counter()

    after = datetime.now(timezone.utc) - timedelta(hours=hours)
    after_iso = after.strftime("%Y-%m-%dT%H:%M:%S")

    clusters: list[frozenset[str]] = []
    primary_counts: Counter[str] = Counter()

    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={
                "per_page": 100,
                "status": "publish",
                "orderby": "date",
                "order": "desc",
                "after": after_iso,
                "_fields": "title,categories",
            },
            auth=(user, password),
            timeout=20,
        )
        resp.raise_for_status()
        posts = resp.json()
    except Exception:
        log.exception("Could not fetch recent WP posts for diversity")
        return [], Counter()

    slug_by_id = _wp_category_slug_map(base, (user, password))

    for post in posts:
        title = (post.get("title") or {}).get("rendered", "")
        if title:
            clusters.append(cluster_key(re.sub(r"<[^>]+>", "", title)))
        for cat_id in post.get("categories") or []:
            slug = slug_by_id.get(cat_id, "")
            if slug:
                primary_counts[slug] += 1

    return clusters, primary_counts


def _wp_category_slug_map(base: str, auth: tuple[str, str]) -> dict[int, str]:
    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/categories",
            params={"per_page": 100},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        return {c["id"]: c.get("slug", "") for c in resp.json()}
    except Exception:
        return {}


def adjusted_score(
    story: dict,
    div: DiversityConfig,
    recent_clusters: list[frozenset[str]],
    recent_primary_counts: Counter[str],
) -> float:
    score = float(story.get("trend_score", 0))
    score = min(score, div.trending_score_cap)

    ck = cluster_key(story.get("title", ""), story.get("summary", ""))
    for rc in recent_clusters:
        if clusters_match(ck, rc, div.cluster_overlap_threshold):
            score -= div.saturation_penalty
            break

    primary = suggest_primary_from_story(
        story.get("title", ""),
        story.get("summary", ""),
        story.get("category"),
    )
    story["_suggested_primary"] = primary
    recent_primary_counts.get(primary, 0)
    if recent_primary_counts.get(primary, 0) >= div.primary_daily_cap:
        score -= div.saturation_penalty * 0.75

    # Slight boost for non–current-affairs feed hints
    if story.get("category") not in ("world", "current-affairs", ""):
        score += 2.0

    return score


def select_diverse_stories(
    candidates: list[dict],
    max_new: int,
    config: dict,
    *,
    skip_if_seen,
) -> list[dict]:
    """
    Pick up to max_new stories with topic + category diversity.
    skip_if_seen(title, url) -> True when story was already processed.
    """
    div = load_diversity_config(config)
    if not div.enabled or max_new <= 0:
        out = []
        for s in candidates:
            if skip_if_seen(s.get("title", ""), s.get("url", "")):
                continue
            out.append(s)
            if len(out) >= max_new:
                break
        return out

    recent_clusters, recent_primary_counts = fetch_recent_wp_clusters(div.recent_hours)

    scored: list[tuple[float, dict]] = []
    for story in candidates:
        if skip_if_seen(story.get("title", ""), story.get("url", "")):
            continue
        adj = adjusted_score(story, div, recent_clusters, recent_primary_counts)
        scored.append((adj, story))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected: list[dict] = []
    run_clusters: list[frozenset[str]] = []
    run_primary_counts: Counter[str] = Counter()

    def can_add(story: dict, primary: str, ck: frozenset[str]) -> bool:
        if run_primary_counts[primary] >= div.max_per_primary_per_run:
            return False
        # Only hard-block duplicate topics within this run — not against all recent posts.
        for rc in run_clusters:
            if clusters_match(ck, rc, div.cluster_overlap_threshold):
                return False
        return True

    # Pass 1: ensure min distinct primaries — pick best per under-used primary
    primaries_needed = min(div.min_distinct_primaries_per_run, max_new)
    by_primary: dict[str, list[tuple[float, dict]]] = {}
    for adj, story in scored:
        primary = story.get("_suggested_primary") or suggest_primary_from_story(
            story.get("title", ""),
            story.get("summary", ""),
            story.get("category"),
        )
        by_primary.setdefault(primary, []).append((adj, story))

    used_primaries: set[str] = set()
    for primary in sorted(
        by_primary.keys(),
        key=lambda p: (run_primary_counts[p], recent_primary_counts.get(p, 0)),
    ):
        if len(used_primaries) >= primaries_needed:
            break
        if primary == "current-affairs" and len(used_primaries) < primaries_needed - 1:
            continue  # defer catch-all desk until we have specifics
        for adj, story in by_primary[primary]:
            ck = cluster_key(story.get("title", ""), story.get("summary", ""))
            if can_add(story, primary, ck):
                selected.append(story)
                run_clusters.append(ck)
                run_primary_counts[primary] += 1
                used_primaries.add(primary)
                break

    # Pass 2: fill remaining slots by adjusted score
    selected_urls = {s.get("url", "").lower() for s in selected}
    for adj, story in scored:
        if len(selected) >= max_new:
            break
        if story.get("url", "").lower() in selected_urls:
            continue
        primary = story.get("_suggested_primary") or suggest_primary_from_story(
            story.get("title", ""),
            story.get("summary", ""),
            story.get("category"),
        )
        ck = cluster_key(story.get("title", ""), story.get("summary", ""))
        if not can_add(story, primary, ck):
            continue
        selected.append(story)
        selected_urls.add(story.get("url", "").lower())
        run_clusters.append(ck)
        run_primary_counts[primary] += 1

    if len(selected) < max_new:
        log.warning(
            "Diversity picked %d / %d — %d candidates after dedup, WP saturation window %dh",
            len(selected),
            max_new,
            len(scored),
            div.recent_hours,
        )

    if selected:
        log.info(
            "Diversity pick: %d stories, primaries=%s",
            len(selected),
            dict(run_primary_counts),
        )
    return selected[:max_new]
