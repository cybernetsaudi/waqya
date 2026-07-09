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
from story_diversity import load_diversity_config, select_diverse_fallback, select_diverse_stories
from taxonomy import suggest_primary_from_story
from trending import (
    fetch_newsapi_for_query,
    fetch_trending_keywords,
    score_story_text,
)

log = logging.getLogger(__name__)

# Last gather() diagnostics for Telegram / debugging.
GATHER_STATS: dict = {}


def _rotate_items(items: list, per_run: int, bucket: int) -> list:
    """Pick a sliding window of items so each run uses a different subset."""
    if not items or per_run <= 0:
        return []
    n = len(items)
    take = min(per_run, n)
    start = bucket % n
    return [items[(start + i) % n] for i in range(take)]

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
    story_format: str = ""
    interview_tone: str = ""


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
        fmt = feed.get("format", "")
        for s in stories:
            s.trend_score += 3.0
            if fmt:
                s.story_format = fmt
        all_stories.extend(stories)
        log.info("GoogleNews %-30s → %d items", feed.get("name", "?"), len(stories))
    return all_stories


def gather_newsapi_country_headlines(config: dict) -> list[Story]:
    """Top headlines by country (Middle East, South Asia, etc.)."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    api_cfg = config.get("newsapi", {})
    if not api_key or not api_cfg.get("enabled"):
        return []

    from datetime import datetime, timezone

    from newsapi_budget import get

    country_map = api_cfg.get("regional_countries") or {}
    per_run = int(api_cfg.get("country_headlines_per_run", 2))
    hour_bucket = datetime.now(timezone.utc).hour
    stories: list[Story] = []

    for country, meta in _rotate_items(list(country_map.items()), per_run, hour_bucket):
        if isinstance(meta, str):
            feed_cat, page_size = meta, 8
        else:
            feed_cat = meta.get("category", "world")
            page_size = int(meta.get("page_size", 8))
        resp = get(
            config,
            "https://newsapi.org/v2/top-headlines",
            params={
                "apiKey": api_key,
                "country": country,
                "pageSize": page_size,
                "language": "en",
            },
            label=f"country:{country}",
        )
        if resp is None:
            continue
        try:
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
            log.exception("NewsAPI country headlines parse failed: %s", country)

    log.info("NewsAPI regional countries → %d items", len(stories))
    return stories


def gather_newsapi_topic_queries(config: dict) -> list[Story]:
    """Targeted /everything searches (region, space, tech + focus-mode desks)."""
    api_key = os.environ.get("NEWSAPI_KEY", "")
    api_cfg = config.get("newsapi", {})
    if not api_key or not api_cfg.get("enabled"):
        return []

    from datetime import datetime, timezone

    from focus_mode import focus_active, focus_cfg, focus_topic_queries

    queries = list(api_cfg.get("topic_queries", []))
    per_run = int(api_cfg.get("topic_queries_per_run", 3))
    if focus_active(config):
        focus_queries = focus_topic_queries(config)
        if focus_queries:
            queries = focus_queries + queries
            per_run = max(per_run, int(focus_cfg(config).get("topic_queries_per_run", per_run)))
    hour_bucket = datetime.now(timezone.utc).hour // 4

    stories: list[Story] = []
    for item in _rotate_items(queries, per_run, hour_bucket):
        query = item.get("query", "")
        feed_cat = item.get("category", "world")
        page_size = int(item.get("page_size", 8))
        if not query:
            continue
        story_fmt = item.get("format", "")
        for raw in fetch_newsapi_for_query(api_key, query, page_size=page_size, config=config):
            stories.append(
                Story(
                    title=raw["title"],
                    url=raw["url"],
                    source="NewsAPI:q",
                    summary=raw["summary"],
                    category=feed_cat,
                    published=raw.get("published"),
                    trend_score=8.0 if story_fmt else 7.0,
                    trend_matched=query[:40],
                    story_format=story_fmt,
                )
            )
    log.info("NewsAPI topic queries → %d items", len(stories))
    return stories


def gather_on_the_record(config: dict) -> list[Story]:
    """Dedicated interview-review queries from on_the_record config."""
    otr = config.get("on_the_record", {})
    if not otr.get("enabled"):
        return []

    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        return []

    stories: list[Story] = []
    for item in otr.get("topic_queries", []):
        query = item.get("query", "")
        if not query:
            continue
        feed_cat = item.get("category", otr.get("default_desk", "united-states"))
        page_size = int(item.get("page_size", 6))
        for raw in fetch_newsapi_for_query(api_key, query, page_size=page_size, config=config):
            stories.append(
                Story(
                    title=raw["title"],
                    url=raw["url"],
                    source="OnTheRecord",
                    summary=raw["summary"],
                    category=feed_cat,
                    published=raw.get("published"),
                    trend_score=9.0,
                    trend_matched=query[:40],
                    story_format="on_the_record",
                )
            )
    log.info("On The Record queries → %d items", len(stories))
    return stories


def gather_newsapi(config: dict) -> list[Story]:
    api_cfg = config.get("newsapi", {})
    if not api_cfg.get("enabled") or not api_cfg.get("everything_enabled", False):
        return []

    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        log.warning("NEWSAPI_KEY not set — skipping NewsAPI")
        return []

    from newsapi_budget import get

    stories: list[Story] = []
    resp = get(
        config,
        "https://newsapi.org/v2/everything",
        params={
            "apiKey": api_key,
            "domains": api_cfg.get("domains", ""),
            "language": api_cfg.get("language", "en"),
            "sortBy": api_cfg.get("sort_by", "publishedAt"),
            "pageSize": api_cfg.get("page_size", 20),
        },
        timeout=15,
        label="everything:domains",
    )
    if resp is None:
        log.info("NewsAPI everything → 0 items")
        return stories
    try:
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
    if not api_key or not api_cfg.get("top_headlines_enabled", False):
        return []

    from newsapi_budget import get

    stories: list[Story] = []
    categories = api_cfg.get(
        "top_headline_categories",
        ["general", "business", "technology"],
    )
    for cat in categories:
        resp = get(
            config,
            "https://newsapi.org/v2/top-headlines",
            params={
                "apiKey": api_key,
                "language": "en",
                "pageSize": int(api_cfg.get("top_headlines_page_size", 12)),
                "category": cat,
            },
            label=f"top-headlines:{cat}",
        )
        if resp is None:
            continue
        try:
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
        for raw in fetch_newsapi_for_query(api_key, phrase, page_size=5, config=config):
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
    global GATHER_STATS
    config = load_config()
    if max_new is None:
        max_new = config.get("pipeline", {}).get("max_articles_per_run", 5)

    from newsapi_budget import begin_run, usage_summary

    begin_run(config)
    log.info(usage_summary(config))

    log.info("Loading trending topics…")
    trending = fetch_trending_keywords(config)

    raw = (
        gather_google_news(config)
        + gather_rss(config)
        + gather_newsapi_top_headlines(config)
        + gather_newsapi_country_headlines(config)
        + gather_on_the_record(config)
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

    from focus_mode import apply_focus_score_adjustments, focus_active

    if focus_active(config):
        candidates = apply_focus_score_adjustments(candidates, config)
        candidates.sort(key=lambda c: float(c.get("trend_score", 0)), reverse=True)

    candidates = _apply_crisis_filter(candidates, config)

    from developing_updates import apply_developing_updates

    apply_developing_updates(candidates, config)

    from interview_review import annotate_interview_stories

    annotate_interview_stories(candidates, config)

    def _skip_if_seen(title: str, url: str, summary: str = "") -> bool:
        return is_seen(title, url, summary)

    eligible_count = sum(
        1
        for c in candidates
        if not _skip_if_seen(c.get("title", ""), c.get("url", ""), c.get("summary", ""))
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

    if len(picked) < max_new and eligible_count > len(picked):
        extra = select_diverse_fallback(
            candidates,
            max_new - len(picked),
            skip_if_seen=_skip_if_seen,
            exclude_urls={s.get("url", "") for s in picked},
        )
        if extra:
            log.info("Diversity fallback added %d stories (saturation bypass)", len(extra))
            picked = picked + extra

    new_stories: list[dict] = []
    for story in picked:
        mark_seen(story["title"], story["url"], story["source"])
        new_stories.append(story)

    GATHER_STATS = {
        "candidates": len(candidates),
        "eligible": eligible_count,
        "picked": len(new_stories),
        "seen_db": _dedup_count(),
        "newsapi": usage_summary(config),
    }

    log.info("New stories after diversity selection: %d", len(new_stories))
    return new_stories


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    for s in gather():
        print(f"  [{s['category']}] score={s.get('trend_score', 0)} {s['title'][:60]}")
