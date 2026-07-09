"""
Auto-post published Waqya articles to social networks.

Primary: Bluesky (AT Protocol) — free, no paid API, fully automatable.
Optional: X/Twitter — when X_API_* secrets are set (paid developer access).

Posts only live (status=publish) articles. Skips drafts. Idempotent via seen.db.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from pathlib import Path

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "seen.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS social_posts (
            post_id INTEGER NOT NULL,
            network TEXT NOT NULL,
            posted_at TEXT NOT NULL DEFAULT (datetime('now')),
            remote_uri TEXT,
            PRIMARY KEY (post_id, network)
        )
        """
    )
    conn.commit()
    return conn


def already_posted(post_id: int, network: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM social_posts WHERE post_id = ? AND network = ?",
            (post_id, network),
        ).fetchone()
    return row is not None


def mark_posted(post_id: int, network: str, remote_uri: str = "") -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO social_posts (post_id, network, remote_uri) VALUES (?, ?, ?)",
            (post_id, network, remote_uri),
        )
        conn.commit()


def _compose_text(title: str, url: str, excerpt: str = "", *, max_len: int = 280) -> str:
    title = re.sub(r"\s+", " ", (title or "").strip())
    excerpt = re.sub(r"\s+", " ", (excerpt or "").strip())
    url = (url or "").strip()

    # Reserve space for URL + newlines
    budget = max_len - len(url) - 2
    if budget < 40:
        return f"{title[: max(20, max_len - len(url) - 3)]}…\n{url}" if url else title[:max_len]

    head = title
    if len(head) > budget:
        head = head[: budget - 1].rstrip() + "…"
        return f"{head}\n{url}"

    remaining = budget - len(head)
    if excerpt and remaining > 40:
        # Optional short dek
        dek = excerpt[: remaining - 3].rstrip()
        if len(excerpt) > remaining - 3:
            dek = dek.rsplit(" ", 1)[0] + "…"
        if dek and dek.lower() not in head.lower():
            return f"{head}\n{dek}\n{url}"

    return f"{head}\n{url}"


def _bluesky_enabled(config: dict) -> bool:
    social = config.get("social", {})
    if not social.get("enabled", True):
        return False
    if not social.get("bluesky", {}).get("enabled", True):
        return False
    return bool(os.environ.get("BLUESKY_HANDLE") and os.environ.get("BLUESKY_APP_PASSWORD"))


def _x_enabled(config: dict) -> bool:
    social = config.get("social", {})
    if not social.get("enabled", True):
        return False
    if not social.get("x", {}).get("enabled", False):
        return False
    keys = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET")
    return all(os.environ.get(k) for k in keys)


def post_to_bluesky(text: str, config: dict) -> str:
    """Create a Bluesky post. Returns at:// URI."""
    from atproto import Client

    handle = os.environ["BLUESKY_HANDLE"].lstrip("@")
    password = os.environ["BLUESKY_APP_PASSWORD"]
    client = Client()
    client.login(handle, password)

    # Prefer facets/link card via text; simple post is enough for v1
    max_len = int(config.get("social", {}).get("bluesky", {}).get("max_length", 300))
    body = text if len(text) <= max_len else text[: max_len - 1] + "…"
    resp = client.send_post(body)
    uri = getattr(resp, "uri", None) or str(resp)
    log.info("Bluesky posted: %s", uri)
    return uri


def post_to_x(text: str, config: dict) -> str:
    """Create an X (Twitter) post via API v2. Returns tweet id."""
    import tweepy

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    max_len = int(config.get("social", {}).get("x", {}).get("max_length", 280))
    body = text if len(text) <= max_len else text[: max_len - 1] + "…"
    resp = client.create_tweet(text=body)
    tweet_id = str(resp.data["id"])
    log.info("X posted: %s", tweet_id)
    return tweet_id


def distribute_publish_results(results: list, config: dict | None = None) -> dict:
    """
    Post each live PublishResult to configured networks.
    Returns counts: {bluesky: n, x: n, skipped: n, errors: n}
    """
    if config is None:
        import yaml

        with open(Path(__file__).parent / "config.yaml") as f:
            config = yaml.safe_load(f)

    social = config.get("social", {})
    if not social.get("enabled", True):
        log.info("Social distribution disabled in config")
        return {"bluesky": 0, "x": 0, "skipped": 0, "errors": 0}

    max_per_run = int(social.get("max_posts_per_run", 5))
    counts = {"bluesky": 0, "x": 0, "skipped": 0, "errors": 0}
    posted_this_run = 0

    live = [r for r in results if getattr(r, "status", "") == "publish" and getattr(r, "post_url", "")]
    # Prefer higher quality scores first
    live.sort(key=lambda r: getattr(r, "quality_score", 0) or 0, reverse=True)

    for result in live:
        if posted_this_run >= max_per_run:
            counts["skipped"] += 1
            continue

        post_id = int(getattr(result, "post_id", 0) or 0)
        title = getattr(result, "title", "") or ""
        url = getattr(result, "post_url", "") or ""
        if not post_id or not url:
            counts["skipped"] += 1
            continue

        text = _compose_text(title, url)
        did_any = False

        if _bluesky_enabled(config):
            if already_posted(post_id, "bluesky"):
                log.info("Bluesky skip (already posted) #%d", post_id)
            else:
                try:
                    uri = post_to_bluesky(text, config)
                    mark_posted(post_id, "bluesky", uri)
                    counts["bluesky"] += 1
                    did_any = True
                except Exception:
                    log.exception("Bluesky post failed for #%d", post_id)
                    counts["errors"] += 1

        if _x_enabled(config):
            if already_posted(post_id, "x"):
                log.info("X skip (already posted) #%d", post_id)
            else:
                try:
                    tid = post_to_x(text, config)
                    mark_posted(post_id, "x", tid)
                    counts["x"] += 1
                    did_any = True
                except Exception:
                    log.exception("X post failed for #%d", post_id)
                    counts["errors"] += 1

        if did_any:
            posted_this_run += 1
        else:
            counts["skipped"] += 1

    log.info(
        "Social distribution: bluesky=%d x=%d skipped=%d errors=%d",
        counts["bluesky"],
        counts["x"],
        counts["skipped"],
        counts["errors"],
    )
    return counts
