"""
Syndicate live Waqya articles to LinkedIn (company page link shares).

Medium cross-posting is optional when MEDIUM_INTEGRATION_TOKEN is set.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def _syndication_cfg(config: dict) -> dict:
    return config.get("syndication", {}) or {}


def _linkedin_enabled(config: dict) -> bool:
    syn = _syndication_cfg(config)
    if not syn.get("enabled", True):
        return False
    if not syn.get("linkedin", {}).get("enabled", True):
        return False
    return bool(
        os.environ.get("LINKEDIN_ACCESS_TOKEN")
        or os.environ.get("LINKEDIN_REFRESH_TOKEN")
    )


def _min_quality(config: dict) -> int:
    syn = _syndication_cfg(config)
    if "min_quality_score" in syn:
        return int(syn["min_quality_score"])
    return int(config.get("pipeline", {}).get("require_min_quality_score", 78))


def _compose_linkedin_commentary(title: str, excerpt: str, article_url: str) -> str:
    title = re.sub(r"\s+", " ", (title or "").strip())
    excerpt = re.sub(r"\s+", " ", (excerpt or "").strip())
    if len(excerpt) > 220:
        excerpt = excerpt[:217].rsplit(" ", 1)[0] + "…"
    lines = [title]
    if excerpt:
        lines.append("")
        lines.append(excerpt)
    lines.append("")
    lines.append(f"Read the full analysis on Waqya → {article_url}")
    return "\n".join(lines)


def _fetch_post_meta(post_id: int) -> tuple[str, str]:
    """Return (excerpt, featured_image_url) from WordPress REST."""
    base = os.environ.get("WP_URL", "https://waqya.com").rstrip("/")
    auth = (os.environ.get("WP_USER", ""), os.environ.get("WP_APP_PASSWORD", ""))
    if not auth[0] or not auth[1]:
        return "", ""
    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts/{post_id}",
            params={"_fields": "excerpt,featured_media"},
            auth=auth,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        excerpt = re.sub(r"<[^>]+>", "", data.get("excerpt", {}).get("rendered", "") or "").strip()
        fm = int(data.get("featured_media") or 0)
        image_url = ""
        if fm:
            m = requests.get(
                f"{base}/wp-json/wp/v2/media/{fm}",
                params={"_fields": "source_url"},
                auth=auth,
                timeout=15,
            )
            if m.ok:
                image_url = m.json().get("source_url", "") or ""
        return excerpt, image_url
    except Exception:
        log.exception("WP meta fetch failed for #%d", post_id)
        return "", ""


def post_to_linkedin(
    *,
    title: str,
    article_url: str,
    excerpt: str = "",
    thumbnail_url: str = "",
    config: dict,
) -> str:
    from linkedin_client import post_article_link

    commentary = _compose_linkedin_commentary(title, excerpt, article_url)
    description = excerpt[:400] if excerpt else title[:400]
    return post_article_link(
        title=title,
        article_url=article_url,
        commentary=commentary,
        description=description,
        thumbnail_url=thumbnail_url,
    )


def distribute_syndication_results(results: list, config: dict | None = None) -> dict:
    """Post top live articles to LinkedIn company page."""
    if config is None:
        import yaml

        with open(Path(__file__).parent / "config.yaml") as f:
            config = yaml.safe_load(f)

    syn = _syndication_cfg(config)
    if not syn.get("enabled", True):
        return {"linkedin": 0, "skipped": 0, "errors": 0}

    from social_poster import already_posted, mark_posted

    max_per_run = int(syn.get("max_posts_per_run", 3))
    min_score = _min_quality(config)
    counts = {"linkedin": 0, "skipped": 0, "errors": 0}

    if not _linkedin_enabled(config):
        log.info("LinkedIn syndication disabled (no tokens)")
        return counts

    live = [
        r
        for r in results
        if getattr(r, "status", "") == "publish"
        and getattr(r, "post_url", "")
        and int(getattr(r, "quality_score", 0) or 0) >= min_score
    ]
    live.sort(key=lambda r: getattr(r, "quality_score", 0) or 0, reverse=True)

    posted = 0
    for result in live:
        if posted >= max_per_run:
            counts["skipped"] += 1
            continue

        post_id = int(getattr(result, "post_id", 0) or 0)
        title = getattr(result, "title", "") or ""
        url = getattr(result, "post_url", "") or ""
        if not post_id or not url:
            counts["skipped"] += 1
            continue

        if already_posted(post_id, "linkedin"):
            log.info("LinkedIn skip (already posted) #%d", post_id)
            counts["skipped"] += 1
            continue

        excerpt = getattr(result, "excerpt", "") or ""
        thumbnail = getattr(result, "featured_image_url", "") or ""
        if not excerpt or not thumbnail:
            fetched_excerpt, fetched_thumb = _fetch_post_meta(post_id)
            excerpt = excerpt or fetched_excerpt
            thumbnail = thumbnail or fetched_thumb

        try:
            remote = post_to_linkedin(
                title=title,
                article_url=url,
                excerpt=excerpt,
                thumbnail_url=thumbnail,
                config=config,
            )
            mark_posted(post_id, "linkedin", remote)
            counts["linkedin"] += 1
            posted += 1
        except Exception:
            log.exception("LinkedIn syndication failed for #%d", post_id)
            counts["errors"] += 1

    log.info(
        "Syndication: linkedin=%d skipped=%d errors=%d",
        counts["linkedin"],
        counts["skipped"],
        counts["errors"],
    )
    return counts
