"""
Auto-post published Waqya articles to free social networks + promote Telegram.

Free stack (no paid APIs):
  - Bluesky (AT Protocol) — primary
  - Mastodon — optional
  - Telegram channel — public channel via bot

Also auto-promotes t.me/waqya_news (join CTAs) — Telegram cannot force-add subscribers.
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


def _promote_cfg(config: dict) -> dict:
    return config.get("social", {}).get("promote", {}) or {}


def telegram_invite_url(config: dict) -> str:
    url = (_promote_cfg(config).get("telegram_url") or "").strip()
    if url:
        return url
    chat = (
        os.environ.get("TELEGRAM_CHANNEL_ID")
        or config.get("social", {}).get("telegram_channel", {}).get("chat_id")
        or "@waqya_news"
    ).strip()
    if chat.startswith("@"):
        return f"https://t.me/{chat.lstrip('@')}"
    if chat.startswith("https://"):
        return chat
    return "https://t.me/waqya_news"


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


def _with_bluesky_promo(text: str, config: dict, *, index: int) -> str:
    every = int(_promote_cfg(config).get("bluesky_promo_every_n", 0) or 0)
    if every <= 0 or (index % every) != 0:
        return text
    invite = telegram_invite_url(config)
    promo = f"\nTelegram: {invite}"
    max_len = int(config.get("social", {}).get("bluesky", {}).get("max_length", 300))
    if len(text) + len(promo) <= max_len:
        return text + promo
    # Trim head to fit promo
    room = max_len - len(promo) - 1
    if room < 40:
        return text
    return text[:room].rstrip() + "…" + promo


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


def _telegram_chat_id(config: dict) -> str:
    return (
        os.environ.get("TELEGRAM_CHANNEL_ID")
        or config.get("social", {}).get("telegram_channel", {}).get("chat_id")
        or ""
    ).strip()


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


def post_to_telegram_channel(
    text: str,
    config: dict,
    *,
    article_url: str = "",
) -> str:
    """Post to public Telegram channel with optional Read on Waqya button."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat = _telegram_chat_id(config)
    max_len = int(config.get("social", {}).get("telegram_channel", {}).get("max_length", 1000))
    body = text if len(text) <= max_len else text[: max_len - 1] + "…"

    payload: dict = {
        "chat_id": chat,
        "text": body,
        "disable_web_page_preview": False,
    }
    if article_url:
        payload["reply_markup"] = {
            "inline_keyboard": [
                [
                    {"text": "Read on Waqya", "url": article_url},
                    {"text": "Join channel", "url": telegram_invite_url(config)},
                ]
            ]
        }

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram channel post failed: {data}")
    msg_id = str(data.get("result", {}).get("message_id", ""))
    log.info("Telegram channel posted: %s", msg_id)
    return msg_id


def post_telegram_join_promo(config: dict) -> str:
    """Standalone join CTA in the channel (encourages shares / pinned content)."""
    invite = telegram_invite_url(config)
    text = (
        "Follow Waqya for breaking commentary as it publishes.\n"
        f"Join the channel → {invite}\n"
        "Share with someone who needs the incident explained."
    )
    return post_to_telegram_channel(text, config, article_url="https://waqya.com/")


def _try_network(
    *,
    post_id: int,
    network: str,
    enabled: bool,
    post_fn,
    counts: dict,
) -> bool:
    if not enabled:
        return False
    if already_posted(post_id, network):
        log.info("%s skip (already posted) #%d", network, post_id)
        return False
    try:
        remote = post_fn()
        mark_posted(post_id, network, remote)
        counts[network] = counts.get(network, 0) + 1
        return True
    except Exception:
        log.exception("%s post failed for #%d", network, post_id)
        counts["errors"] = counts.get("errors", 0) + 1
        return False


def distribute_publish_results(results: list, config: dict | None = None) -> dict:
    """Post each live PublishResult to free networks and promote Telegram."""
    if config is None:
        import yaml

        with open(Path(__file__).parent / "config.yaml") as f:
            config = yaml.safe_load(f)

    social = config.get("social", {})
    if not social.get("enabled", True):
        log.info("Social distribution disabled in config")
        return {
            "bluesky": 0,
            "mastodon": 0,
            "telegram": 0,
            "promos": 0,
            "skipped": 0,
            "errors": 0,
        }

    max_per_run = int(social.get("max_posts_per_run", 5))
    counts = {
        "bluesky": 0,
        "mastodon": 0,
        "telegram": 0,
        "promos": 0,
        "skipped": 0,
        "errors": 0,
    }
    posted_this_run = 0
    article_index = 0

    live = [r for r in results if getattr(r, "status", "") == "publish" and getattr(r, "post_url", "")]
    live.sort(key=lambda r: getattr(r, "quality_score", 0) or 0, reverse=True)

    join_every = int(_promote_cfg(config).get("telegram_join_every_n", 0) or 0)

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

        article_index += 1
        text_short = _compose_text(title, url, max_len=300)
        text_short = _with_bluesky_promo(text_short, config, index=article_index)
        text_long = _compose_text(title, url, max_len=480)

        # Bind loop locals for lambdas (avoid late-binding bugs).
        bsky_text, masto_text, tg_text, tg_url = text_short, text_long, text_long, url

        did_any = False
        did_any |= _try_network(
            post_id=post_id,
            network="bluesky",
            enabled=_bluesky_enabled(config),
            post_fn=lambda t=bsky_text: post_to_bluesky(t, config),
            counts=counts,
        )
        did_any |= _try_network(
            post_id=post_id,
            network="mastodon",
            enabled=_mastodon_enabled(config),
            post_fn=lambda t=masto_text: post_to_mastodon(t, config),
            counts=counts,
        )
        did_any |= _try_network(
            post_id=post_id,
            network="telegram",
            enabled=_telegram_channel_enabled(config),
            post_fn=lambda t=tg_text, u=tg_url: post_to_telegram_channel(
                t, config, article_url=u
            ),
            counts=counts,
        )

        if (
            did_any
            and join_every > 0
            and article_index % join_every == 0
            and _telegram_channel_enabled(config)
        ):
            promo_key = post_id * 1000 + 1  # synthetic id so join promo is once per article slot
            if not already_posted(promo_key, "telegram_promo"):
                try:
                    remote = post_telegram_join_promo(config)
                    mark_posted(promo_key, "telegram_promo", remote)
                    counts["promos"] += 1
                except Exception:
                    log.exception("Telegram join promo failed")
                    counts["errors"] += 1

        if did_any:
            posted_this_run += 1
        else:
            counts["skipped"] += 1

    log.info(
        "Social distribution: bluesky=%d mastodon=%d telegram=%d promos=%d skipped=%d errors=%d",
        counts["bluesky"],
        counts["mastodon"],
        counts["telegram"],
        counts["promos"],
        counts["skipped"],
        counts["errors"],
    )
    return counts
