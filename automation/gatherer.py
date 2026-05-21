"""
News gatherer — pulls stories from RSS, NewsAPI, and trending-topic search.
Ranks by trending relevance, then deduplicates.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from typing import Optional

import feedparser
import requests
import yaml

from dedup import count_seen as _dedup_count, is_seen, mark_seen
from sources import merge_extra_sources
from story_diversity import load_diversity_config, select_diverse_stories
from taxonomy import suggest_primary_from_story
from trending import (
    fetch_newsapi_for_query,
    fetch_trending_keywords,
    score_story_text,
)

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "waqya_categories.yaml")


@dataclass
class Story:
    title: str
    url: str
    source: str
    summary: str
    category: str
    published: Optional[str] = None
    trend_score: float = 0.0
    trend_matched: str = ""


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    if cfg.get("taxonomy", {}).get("source") == "waqya_categories.yaml":
        import os as _os

        cat_path = CATEGORIES_PATH
        if _os.path.isfile(cat_path):
            with open(cat_path) as cf:
                cat = yaml.safe_load(cf)
            cfg["rss_feeds"] = cat.get("rss_feeds", cfg.get("rss_feeds", []))
            cfg["feed_category_map"] = cat.get("feed_category_map", {})
            if cat.get("trending"):
                base_t = cfg.get("trending", {})
                cfg["trending"] = {**base_t, **cat["trending"]}
    return merge_extra_sources(cfg)


def _fetch_rss(feed_url: str, feed_name: str, category: str) -> list[Story]:
    stories: list[Story] = []
    try:
        parsed = feedparser.parse(feed_url)
        limit = 20
        for entry in parsed.entries[:limit]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", entry.get("description", "")).strip()
            published = entry.get("published", entry.get("updated", ""))
            if not title or not link:
                continue
            stories.append(
                Story(
                    title=title,
                    url=link,
                    source=feed_name,
                    summary=summary[:500],
                    category=category,
                    published=published,
                )
            )
    except Exception:
        log.exception("RSS fetch failed for %s", feed_name)
    return stories


def gather_rss(config: dict) -> list[Story]:
    all_stories: list[Story] = []
    for feed in config.get("rss_feeds", []):
        stories = _fetch_rss(feed["url"], feed["name"], feed.get("category", "world"))
        all_stories.extend(stories)
        log.info("RSS  %-30s → %d items", feed["name"], len(stories))
    return all_stories


def gather_google_news(config: dict) -> list[Story]:
    """Google News topic RSS — free, strong on regional breaking news."""
    gcfg = config.get("google_news", {})
    if not gcfg.get("enabled", True):
        return []

    all_stories: list[Story] = []
    for feed in gcfg.get("feeds", []):
        stories = _fetch_rss(
            feed["url"],
            feed.get("name", "Google News"),
            feed.get("category", "world"),
        )
        for s in stories:
            s.trend_score += 3.0
        all_stories.extend(stories)
        log.info("GoogleNews %-30s → %d items", feed.get("name", "?"), len(stories))
    return all_stories


def gather_newsapi_country_headlines(config: dict) -> list[Story]:
    """Top headlines by country (Middle East, South Asia, etc.)."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    api_cfg = config.get("newsapi", {})
    if not api_key or not api_cfg.get("enabled"):
        return []

    country_map = api_cfg.get("regional_countries") or {}
    stories: list[Story] = []

    for country, meta in country_map.items():
        if isinstance(meta, str):
            feed_cat, page_size = meta, 8
        else:
            feed_cat = meta.get("category", "world")
            page_size = int(meta.get("page_size", 8))
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": api_key,
                    "country": country,
                    "pageSize": page_size,
                    "language": "en",
                },
                timeout=12,
            )
            resp.raise_for_status()
            for article in resp.json().get("articles", []):
                title = (article.get("title") or "").strip()
                url = (article.get("url") or "").strip()
                if not title or not url or title == "[Removed]":
                    continue
                stories.append(
                    Story(
                        title=title,
                        url=url,
                        source=f"NewsAPI:{country}",
                        summary=(article.get("description") or "")[:500],
                        category=feed_cat,
                        published=article.get("publishedAt", ""),
                        trend_score=6.0,
                    )
                )
        except Exception:
            log.exception("NewsAPI country headlines failed: %s", country)

    log.info("NewsAPI regional countries → %d items", len(stories))
    return stories


def gather_newsapi_topic_queries(config: dict) -> list[Story]:
    """Targeted /everything searches (region, space, tech)."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    api_cfg = config.get("newsapi", {})
    if not api_key or not api_cfg.get("enabled"):
        return []

    stories: list[Story] = []
    for item in api_cfg.get("topic_queries", []):
        query = item.get("query", "")
        feed_cat = item.get("category", "world")
        page_size = int(item.get("page_size", 8))
        if not query:
            continue
        for raw in fetch_newsapi_for_query(api_key, query, page_size=page_size):
            stories.append(
                Story(
                    title=raw["title"],
                    url=raw["url"],
                    source=f"NewsAPI:q",
                    summary=raw["summary"],
                    category=feed_cat,
                    published=raw.get("published"),
                    trend_score=7.0,
                    trend_matched=query[:40],
                )
            )
    log.info("NewsAPI topic queries → %d items", len(stories))
    return stories


def gather_newsapi(config: dict) -> list[Story]:
    api_cfg = config.get("newsapi", {})
    if not api_cfg.get("enabled"):
        return []

    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        log.warning("NEWSAPI_KEY not set — skipping NewsAPI")
        return []

    stories: list[Story] = []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "apiKey": api_key,
                "domains": api_cfg.get("domains", ""),
                "language": api_cfg.get("language", "en"),
                "sortBy": api_cfg.get("sort_by", "publishedAt"),
                "pageSize": api_cfg.get("page_size", 20),
            },
            timeout=15,
        )
        resp.raise_for_status()
        for article in resp.json().get("articles", []):
            title = (article.get("title") or "").strip()
            url = (article.get("url") or "").strip()
            if not title or not url or title == "[Removed]":
                continue
            stories.append(
                Story(
                    title=title,
                    url=url,
                    source=article.get("source", {}).get("name", "NewsAPI"),
                    summary=(article.get("description") or "")[:500],
                    category="world",
                    published=article.get("publishedAt", ""),
                )
            )
    except Exception:
        log.exception("NewsAPI everything failed")

    log.info("NewsAPI everything → %d items", len(stories))
    return stories


def gather_newsapi_top_headlines(config: dict) -> list[Story]:
    """Top headlines endpoint (free tier) — high-engagement stories."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    api_cfg = config.get("newsapi", {})
    if not api_key:
        return []

    stories: list[Story] = []
    categories = api_cfg.get(
        "top_headline_categories",
        ["general", "business", "technology"],
    )
    for cat in categories:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/top-headlines",
                params={
                    "apiKey": api_key,
                    "language": "en",
                    "pageSize": int(api_cfg.get("top_headlines_page_size", 12)),
                    "category": cat,
                },
                timeout=12,
            )
            resp.raise_for_status()
            feed_cat = {"technology": "tech", "business": "business", "science": "science"}.get(
                cat, "world"
            )
            for article in resp.json().get("articles", []):
                title = (article.get("title") or "").strip()
                url = (article.get("url") or "").strip()
                if not title or not url or title == "[Removed]":
                    continue
                stories.append(
                    Story(
                        title=title,
                        url=url,
                        source=f"Top:{cat}",
                        summary=(article.get("description") or "")[:500],
                        category=feed_cat,
                        published=article.get("publishedAt", ""),
                        trend_score=5.0,
                    )
                )
        except Exception:
            log.exception("Top headlines failed: %s", cat)

    log.info("NewsAPI top-headlines → %d items", len(stories))
    return stories


def gather_trending_queries(config: dict, trending: list[tuple[str, float]]) -> list[Story]:
    """Fetch extra stories for top trending keyword phrases."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    cfg = config.get("trending", {})
    n_queries = int(cfg.get("search_top_queries", 3))
    if not api_key or n_queries <= 0:
        return []

    stories: list[Story] = []
    # Use multi-word phrases from trending list
    phrases = [kw for kw, _ in trending if " " in kw][:n_queries]
    if not phrases:
        phrases = [kw for kw, _ in trending[:n_queries]]

    for phrase in phrases:
        for raw in fetch_newsapi_for_query(api_key, phrase, page_size=5):
            stories.append(
                Story(
                    title=raw["title"],
                    url=raw["url"],
                    source=raw["source"],
                    summary=raw["summary"],
                    category=raw.get("category", "world"),
                    published=raw.get("published"),
                    trend_score=10.0,
                    trend_matched=phrase,
                )
            )
    log.info("Trending query stories → %d items", len(stories))
    return stories


def _rank_stories(
    stories: list[Story],
    trending: list[tuple[str, float]],
    config: dict,
) -> list[Story]:
    div = load_diversity_config(config)
    for s in stories:
        text = f"{s.title} {s.summary}"
        s.trend_score += score_story_text(text, trending)
        s.trend_score = min(s.trend_score, div.trending_score_cap)
    return sorted(stories, key=lambda x: x.trend_score, reverse=True)


def _apply_crisis_filter(candidates: list[dict], config: dict) -> list[dict]:
    """When crisis mode is on, only gather stories for priority desks."""
    crisis = config.get("crisis_mode", {})
    if not crisis.get("enabled"):
        return candidates
    desks = set(crisis.get("desks", []))
    if not desks:
        return candidates
    filtered = [c for c in candidates if c.get("suggested_primary") in desks]
    log.info(
        "Crisis mode: %d → %d stories (desks: %s)",
        len(candidates),
        len(filtered),
        ", ".join(sorted(desks)),
    )
    return filtered if filtered else candidates


def _dedupe_stories(stories: list[Story]) -> list[Story]:
    seen_urls: set[str] = set()
    out: list[Story] = []
    for s in stories:
        key = s.url.strip().lower()
        if key in seen_urls:
            continue
        seen_urls.add(key)
        out.append(s)
    return out


def gather(max_new: int | None = None) -> list[dict]:
    config = load_config()
    if max_new is None:
        max_new = config.get("pipeline", {}).get("max_articles_per_run", 5)

    log.info("Loading trending topics…")
    trending = fetch_trending_keywords(config)

    raw = (
        gather_google_news(config)
        + gather_rss(config)
        + gather_newsapi_top_headlines(config)
        + gather_newsapi_country_headlines(config)
        + gather_newsapi_topic_queries(config)
        + gather_trending_queries(config, trending)
        + gather_newsapi(config)
    )
    raw = _dedupe_stories(raw)
    log.info("Total unique stories: %d", len(raw))

    ranked = _rank_stories(raw, trending, config)
    if ranked[:3]:
        log.info(
            "Top trend matches: %s",
            [(s.title[:40], round(s.trend_score, 1)) for s in ranked[:3]],
        )

    candidates = [asdict(s) for s in ranked]
    for c in candidates:
        c["suggested_primary"] = suggest_primary_from_story(
            c.get("title", ""),
            c.get("summary", ""),
            c.get("category"),
        )

    candidates = _apply_crisis_filter(candidates, config)

    def _skip_if_seen(title: str, url: str) -> bool:
        return is_seen(title, url)

    eligible_count = sum(
        1 for c in candidates if not _skip_if_seen(c.get("title", ""), c.get("url", ""))
    )
    log.info(
        "Candidates: %d total, %d pass dedup (seen.db entries: %s)",
        len(candidates),
        eligible_count,
        _dedup_count(),
    )

    picked = select_diverse_stories(
        candidates,
        max_new,
        config,
        skip_if_seen=_skip_if_seen,
    )

    new_stories: list[dict] = []
    for story in picked:
        mark_seen(story["title"], story["url"], story["source"])
        new_stories.append(story)

    log.info("New stories after diversity selection: %d", len(new_stories))
    return new_stories


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    for s in gather():
        print(f"  [{s['category']}] score={s.get('trend_score', 0)} {s['title'][:60]}")
