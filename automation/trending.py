"""
Discover high-interest / trending news topics to prioritize story selection.

Sources (free):
  - NewsAPI top headlines (multiple categories)
  - Google Trends daily RSS
  - Reddit r/worldnews + r/news hot titles
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from typing import Optional
import feedparser
import requests

log = logging.getLogger(__name__)

STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of is are was were be been being
    that this with from as by it its into over after before not no yes
    says said will can about up out new just more most other than when
    how what who which their they them his her she he we you your our
    """.split()
)


def _keywords_from_text(text: str, weight: float = 1.0) -> Counter:
    words = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", text.lower())
    c: Counter = Counter()
    for w in words:
        if w not in STOPWORDS and len(w) > 2:
            c[w] += weight
    # bigrams from title-like text
    tokens = [w for w in words if w not in STOPWORDS][:12]
    for i in range(len(tokens) - 1):
        c[f"{tokens[i]} {tokens[i+1]}"] += weight * 1.5
    return c


def _merge(counter: Counter, other: Counter) -> None:
    counter.update(other)


def fetch_newsapi_top_headlines(api_key: str) -> Counter:
    """NewsAPI top-headlines (allowed on free tier)."""
    topics: Counter = Counter()
    if not api_key:
        return topics

    categories = ["general", "business", "technology", "science", "health"]
    for cat in categories:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": api_key,
                    "language": "en",
                    "pageSize": 15,
                    "category": cat,
                },
                timeout=12,
            )
            resp.raise_for_status()
            for art in resp.json().get("articles", []):
                title = art.get("title") or ""
                desc = art.get("description") or ""
                _merge(topics, _keywords_from_text(f"{title} {desc}", weight=2.0))
        except Exception:
            log.exception("NewsAPI top-headlines failed for %s", cat)
    return topics


def fetch_google_trends_rss(geo: str = "US", weight: float = 3.0) -> Counter:
    """Daily trending searches for a Google Trends geo code (US, GB, IN, PK, SA, …)."""
    topics: Counter = Counter()
    geo = (geo or "US").strip().upper()
    try:
        parsed = feedparser.parse(
            f"https://trends.google.com/trending/rss?geo={geo}"
        )
        for entry in parsed.entries[:20]:
            title = entry.get("title", "")
            _merge(topics, _keywords_from_text(title, weight=weight))
        log.debug("Google Trends %s → %d entries", geo, len(parsed.entries))
    except Exception:
        log.exception("Google Trends RSS failed for geo=%s", geo)
    return topics


def fetch_google_trends_multi(geos: list) -> Counter:
    """Merge trending topics from multiple regional Google Trends feeds."""
    combined: Counter = Counter()
    for item in geos:
        if isinstance(item, str):
            geo, weight = item, 3.0
        else:
            geo = item.get("geo", "US")
            weight = float(item.get("weight", 3.0))
        _merge(combined, fetch_google_trends_rss(geo, weight))
    return combined


def fetch_reddit_hot(subreddit: str, weight: float = 2.5) -> Counter:
    topics: Counter = Counter()
    try:
        resp = requests.get(
            f"https://www.reddit.com/r/{subreddit}/hot.json",
            params={"limit": 20},
            headers={"User-Agent": "WaqyaBot/1.0"},
            timeout=12,
        )
        resp.raise_for_status()
        for child in resp.json().get("data", {}).get("children", []):
            title = child.get("data", {}).get("title", "")
            _merge(topics, _keywords_from_text(title, weight=weight))
    except Exception:
        log.exception("Reddit fetch failed: r/%s", subreddit)
    return topics


def fetch_trending_keywords(config: dict | None = None) -> list[tuple[str, float]]:
    """
    Return ranked (keyword, score) tuples for biasing story selection.
    """
    cfg = (config or {}).get("trending", {})
    if cfg.get("enabled", True) is False:
        return []

    combined: Counter = Counter()
    api_key = os.environ.get("NEWSAPI_KEY", "")

    if cfg.get("newsapi_top_headlines", True):
        _merge(combined, fetch_newsapi_top_headlines(api_key))

    if cfg.get("google_trends", True):
        geos = cfg.get("google_trends_geos")
        if geos:
            _merge(combined, fetch_google_trends_multi(geos))
        else:
            _merge(combined, fetch_google_trends_rss())

    for sub in cfg.get("reddit_subreddits", ["worldnews", "news", "technology"]):
        _merge(combined, fetch_reddit_hot(sub))

    try:
        from taxonomy import get_scrape_keywords

        for _key, kws in get_scrape_keywords().items():
            for kw in kws:
                combined[kw.lower()] += 2.0
    except Exception:
        pass

    ranked = combined.most_common(int(cfg.get("max_keywords", 40)))
    log.info("Trending keywords loaded: %d (top: %s)", len(ranked), ranked[:5])
    return [(k, float(v)) for k, v in ranked]


def score_story_text(text: str, trending: list[tuple[str, float]]) -> float:
    """Higher = better match to current trending topics."""
    if not trending:
        return 0.0
    lower = text.lower()
    score = 0.0
    for kw, weight in trending:
        if kw in lower:
            score += weight
    return score


def fetch_newsapi_for_query(api_key: str, query: str, page_size: int = 10) -> list[dict]:
    """Pull articles matching a hot trending phrase."""
    if not api_key or not query:
        return []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "apiKey": api_key,
                "q": query[:100],
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": page_size,
            },
            timeout=12,
        )
        resp.raise_for_status()
        out = []
        for art in resp.json().get("articles", []):
            title = (art.get("title") or "").strip()
            url = (art.get("url") or "").strip()
            if not title or not url or title == "[Removed]":
                continue
            out.append(
                {
                    "title": title,
                    "url": url,
                    "source": art.get("source", {}).get("name", "NewsAPI"),
                    "summary": (art.get("description") or "")[:500],
                    "category": "world",
                    "published": art.get("publishedAt", ""),
                    "trend_matched": query,
                }
            )
        return out
    except Exception:
        log.exception("NewsAPI query failed: %s", query)
        return []
