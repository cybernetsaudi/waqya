"""
Auto-post published Waqya articles to free social networks.

Free stack (no paid APIs):
  - Bluesky (AT Protocol) — primary
  - Mastodon — any instance (mastodon.social, etc.)
  - Telegram channel — public channel via existing bot

X/Twitter is unsupported in the default config (paid write API).

Posts only live (status=publish) articles. Skips drafts. Idempotent via seen.db.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
from pathlib import Path

import requests

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

    budget = max_len - len(url) - 2
    if budget < 40:
        return f"{title[: max(20, max_len - len(url) - 3)]}…\n{url}" if url else title[:max_len]

    head = title
    if len(head) > budget:
        head = head[: budget - 1].rstrip() + "…"
        return f"{head}\n{url}"

    remaining = budget - len(head)
    if excerpt and remaining > 40:
        dek = excerpt[: remaining - 3].rstrip()
        if len(excerpt) > remaining - 3:
            dek = dek.rsplit(" ", 1)[0] + "…"
        if dek and dek.lower() not in head.lower():
            return f"{head}\n{dek}\n{url}"

    return f"{head}\n{url}"


def _social_on(config: dict) -> bool:
    return bool(config.get("social", {}).get("enabled", True))


def _bluesky_enabled(config: dict) -> bool:
    if not _social_on(config):
        return False
    if not config.get("social", {}).get("bluesky", {}).get("enabled", True):
        return False
    return bool(os.environ.get("BLUESKY_HANDLE") and os.environ.get("BLUESKY_APP_PASSWORD"))


def _mastodon_enabled(config: dict) -> bool:
    if not _social_on(config):
        return False
    if not config.get("social", {}).get("mastodon", {}).get("enabled", False):
        return False
    return bool(os.environ.get("MASTODON_BASE_URL") and os.environ.get("MASTODON_ACCESS_TOKEN"))


def _telegram_channel_enabled(config: dict) -> bool:
    if not _social_on(config):
        return False
    if not config.get("social", {}).get("telegram_channel", {}).get("enabled", False):
        return False
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = (
        os.environ.get("TELEGRAM_CHANNEL_ID")
        or config.get("social", {}).get("telegram_channel", {}).get("chat_id")
        or ""
    ).strip()
    return bool(token and chat)


def post_to_bluesky(text: str, config: dict) -> str:
    from atproto import Client

    handle = os.environ["BLUESKY_HANDLE"].lstrip("@")
    password = os.environ["BLUESKY_APP_PASSWORD"]
    client = Client()
    client.login(handle, password)

    max_len = int(config.get("social", {}).get("bluesky", {}).get("max_length", 300))
    body = text if len(text) <= max_len else text[: max_len - 1] + "…"
    resp = client.send_post(body)
    uri = getattr(resp, "uri", None) or str(resp)
    log.info("Bluesky posted: %s", uri)
    return uri


def post_to_mastodon(text: str, config: dict) -> str:
    """Post a status to Mastodon (free). Returns status URL or id."""
    base = os.environ["MASTODON_BASE_URL"].rstrip("/")
    token = os.environ["MASTODON_ACCESS_TOKEN"]
    max_len = int(config.get("social", {}).get("mastodon", {}).get("max_length", 500))
    body = text if len(text) <= max_len else text[: max_len - 1] + "…"

    resp = requests.post(
        f"{base}/api/v1/statuses",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": body, "visibility": "public"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    uri = data.get("url") or str(data.get("id", ""))
    log.info("Mastodon posted: %s", uri)
    return uri


def post_to_telegram_channel(text: str, config: dict) -> str:
    """Post to a public Telegram channel (free). Bot must be channel admin."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = (
        os.environ.get("TELEGRAM_CHANNEL_ID")
        or config.get("social", {}).get("telegram_channel", {}).get("chat_id")
        or ""
    ).strip()
    max_len = int(config.get("social", {}).get("telegram_channel", {}).get("max_length", 1000))
    body = text if len(text) <= max_len else text[: max_len - 1] + "…"

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat,
            "text": body,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram channel post failed: {data}")
    msg_id = str(data.get("result", {}).get("message_id", ""))
    log.info("Telegram channel posted: %s", msg_id)
    return msg_id


def _try_network(
    *,
    post_id: int,
    network: str,
    enabled: bool,
    post_fn,
    text: str,
    config: dict,
    counts: dict,
) -> bool:
    if not enabled:
        return False
    if already_posted(post_id, network):
        log.info("%s skip (already posted) #%d", network, post_id)
        return False
    try:
        remote = post_fn(text, config)
        mark_posted(post_id, network, remote)
        counts[network] = counts.get(network, 0) + 1
        return True
    except Exception:
        log.exception("%s post failed for #%d", network, post_id)
        counts["errors"] = counts.get("errors", 0) + 1
        return False


def distribute_publish_results(results: list, config: dict | None = None) -> dict:
    """
    Post each live PublishResult to configured free networks.
    Returns counts per network + skipped/errors.
    """
    if config is None:
        import yaml

        with open(Path(__file__).parent / "config.yaml") as f:
            config = yaml.safe_load(f)

    social = config.get("social", {})
    if not social.get("enabled", True):
        log.info("Social distribution disabled in config")
        return {"bluesky": 0, "mastodon": 0, "telegram": 0, "skipped": 0, "errors": 0}

    max_per_run = int(social.get("max_posts_per_run", 5))
    counts = {"bluesky": 0, "mastodon": 0, "telegram": 0, "skipped": 0, "errors": 0}
    posted_this_run = 0

    live = [r for r in results if getattr(r, "status", "") == "publish" and getattr(r, "post_url", "")]
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

        # Longer compose for Mastodon/Telegram; Bluesky truncates inside its poster
        text_short = _compose_text(title, url, max_len=300)
        text_long = _compose_text(title, url, max_len=480)

        did_any = False
        did_any |= _try_network(
            post_id=post_id,
            network="bluesky",
            enabled=_bluesky_enabled(config),
            post_fn=lambda t, c: post_to_bluesky(text_short, c),
            text=text_short,
            config=config,
            counts=counts,
        )
        did_any |= _try_network(
            post_id=post_id,
            network="mastodon",
            enabled=_mastodon_enabled(config),
            post_fn=lambda t, c: post_to_mastodon(text_long, c),
            text=text_long,
            config=config,
            counts=counts,
        )
        did_any |= _try_network(
            post_id=post_id,
            network="telegram",
            enabled=_telegram_channel_enabled(config),
            post_fn=lambda t, c: post_to_telegram_channel(text_long, c),
            text=text_long,
            config=config,
            counts=counts,
        )

        if did_any:
            posted_this_run += 1
        else:
            counts["skipped"] += 1

    log.info(
        "Social distribution: bluesky=%d mastodon=%d telegram=%d skipped=%d errors=%d",
        counts["bluesky"],
        counts["mastodon"],
        counts["telegram"],
        counts["skipped"],
        counts["errors"],
    )
    return counts
