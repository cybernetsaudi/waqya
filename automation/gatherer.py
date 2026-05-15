"""
News gatherer — pulls stories from RSS feeds and NewsAPI,
normalises them into a common format, and filters out duplicates.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Optional

import feedparser
import requests
import yaml

from dedup import is_seen, mark_seen

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


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── RSS ──────────────────────────────────────────────────────────────

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


# ── NewsAPI ──────────────────────────────────────────────────────────

def gather_newsapi(config: dict) -> list[Story]:
    api_cfg = config.get("newsapi", {})
    if not api_cfg.get("enabled"):
        return []

    api_key = os.environ.get("NEWSAPI_KEY", "")
    if not api_key:
        log.warning("NEWSAPI_KEY not set — skipping NewsAPI")
        return []

    params = {
        "apiKey": api_key,
        "domains": api_cfg.get("domains", ""),
        "language": api_cfg.get("language", "en"),
        "sortBy": api_cfg.get("sort_by", "publishedAt"),
        "pageSize": api_cfg.get("page_size", 20),
    }

    stories: list[Story] = []
    try:
        resp = requests.get(
            "https://newsapi.org/v2/everything", params=params, timeout=15
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
        log.exception("NewsAPI fetch failed")

    log.info("NewsAPI → %d items", len(stories))
    return stories


# ── Public API ───────────────────────────────────────────────────────

def gather(max_new: int | None = None) -> list[dict]:
    """
    Fetch from all sources, deduplicate, and return a list of new story dicts
    (at most *max_new*).
    """
    config = load_config()
    if max_new is None:
        max_new = config.get("pipeline", {}).get("max_articles_per_run", 5)

    raw = gather_rss(config) + gather_newsapi(config)
    log.info("Total raw stories: %d", len(raw))

    new_stories: list[dict] = []
    for story in raw:
        if is_seen(story.title, story.url):
            continue
        mark_seen(story.title, story.url, story.source)
        new_stories.append(asdict(story))
        if len(new_stories) >= max_new:
            break

    log.info("New stories after dedup: %d", len(new_stories))
    return new_stories


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    stories = gather()
    for s in stories:
        print(f"  [{s['category']}] {s['title']}")
        print(f"         {s['url']}\n")
