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

from dedup import is_seen, mark_seen
from trending import (
    fetch_newsapi_for_query,
    fetch_trending_keywords,
    score_story_text,
)

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


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
        return yaml.safe_load(f)


def _fetch_rss(feed_url: str, feed_name: str, category: str) -> list[Story]:
    stories: list[Story] = []
    try:
        parsed = feedparser.parse(feed_url)
        for entry in parsed.entries[:15]:
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
    if not api_key:
        return []

    stories: list[Story] = []
    categories = config.get("newsapi", {}).get(
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
                    "pageSize": 10,
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


def _rank_stories(stories: list[Story], trending: list[tuple[str, float]]) -> list[Story]:
    for s in stories:
        text = f"{s.title} {s.summary}"
        s.trend_score += score_story_text(text, trending)
    return sorted(stories, key=lambda x: x.trend_score, reverse=True)


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
        gather_newsapi_top_headlines(config)
        + gather_trending_queries(config, trending)
        + gather_rss(config)
        + gather_newsapi(config)
    )
    raw = _dedupe_stories(raw)
    log.info("Total unique stories: %d", len(raw))

    ranked = _rank_stories(raw, trending)
    if ranked[:3]:
        log.info(
            "Top trend matches: %s",
            [(s.title[:40], round(s.trend_score, 1)) for s in ranked[:3]],
        )

    new_stories: list[dict] = []
    for story in ranked:
        if is_seen(story.title, story.url):
            continue
        mark_seen(story.title, story.url, story.source)
        new_stories.append(asdict(story))
        if len(new_stories) >= max_new:
            break

    log.info("New stories after dedup (trend-ranked): %d", len(new_stories))
    return new_stories


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    for s in gather():
        print(f"  [{s['category']}] score={s.get('trend_score', 0)} {s['title'][:60]}")
