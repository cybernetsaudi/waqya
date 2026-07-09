"""
Telegram notifier — publish/hold summaries, errors, and budget alerts.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import requests

from publisher import PublishResult

log = logging.getLogger(__name__)


def _get_credentials() -> tuple[Optional[str], Optional[str]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    return token, chat_id


def send_message(text: str) -> bool:
    """Send a plain-text message via the Telegram Bot API."""
    token, chat_id = _get_credentials()
    if not token or not chat_id:
        log.warning("Telegram credentials not set — skipping notification")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        log.info("Telegram notification sent")
        return True
    except Exception:
        log.exception("Telegram notification failed")
        return False


def notify_pipeline_results(
    results: list[PublishResult],
    wp_admin_url: str,
    social_summary: str = "",
) -> bool:
    """Notify about a pipeline run: live posts vs drafts held for review."""
    if not results:
        log.info("No posts to notify about")
        return True

    live = [r for r in results if r.status == "publish"]
    held = [r for r in results if r.status != "publish"]

    lines = [
        f"<b>📰 Waqya pipeline — {len(results)} article{'s' if len(results) != 1 else ''}</b>",
        f"✅ Live: {len(live)} · 📝 Held: {len(held)}",
        "",
    ]

    for i, r in enumerate(results, 1):
        icon = "✅" if r.status == "publish" else "📝"
        breaking = " 🔴" if r.is_breaking else ""
        score = f" · {r.quality_score}/100" if r.quality_score else ""
        link = r.post_url if r.status == "publish" and r.post_url else r.edit_url
        lines.append(f"{i}. {icon}{breaking} <a href=\"{link}\">{r.title}</a>{score}")
        if r.llm_body:
            lines.append(f"   <i>Body: {r.llm_body} · Headline: {r.llm_headline or 'n/a'}</i>")
        if r.held_reason:
            lines.append(f"   <i>{r.held_reason}</i>")
        elif r.quality_notes and r.status == "publish":
            lines.append(f"   <i>{r.quality_notes[:180]}</i>")

    if social_summary:
        lines.append("")
        lines.append(f"<i>Social: {social_summary}</i>")

    if held:
        lines.append("")
        lines.append(
            f'<a href="{wp_admin_url}/wp-admin/edit.php?post_status=draft">→ Review held drafts</a>'
        )
    if live:
        lines.append(f'<a href="{wp_admin_url}">→ View site</a>')

    return send_message("\n".join(lines))


def notify_new_drafts(results: list[PublishResult], wp_admin_url: str) -> bool:
    """Backward-compatible alias."""
    return notify_pipeline_results(results, wp_admin_url)


def notify_error(error_msg: str) -> bool:
    """Alert the owner about a pipeline failure."""
    text = f"<b>⚠️ Waqya Pipeline Error</b>\n\n<code>{error_msg}</code>"
    return send_message(text)


def notify_gather_empty(stats: dict) -> bool:
    """Alert when the pipeline ran but found no publishable stories."""
    if not stats:
        return False
    lines = [
        "<b>⚠️ Waqya pipeline — no new stories</b>",
        "",
        f"Candidates in feeds: {stats.get('candidates', '?')}",
        f"Passed dedup: {stats.get('eligible', '?')}",
        f"Picked to publish: {stats.get('picked', 0)}",
        f"seen.db entries: {stats.get('seen_db', '?')}",
        stats.get("newsapi", ""),
        "",
        "RSS/Google News still run; NewsAPI is budget-capped. "
        "Diversity fallback may still block if all URLs were already published.",
        "",
        "Check GitHub Actions logs or run: <code>python pipeline.py</code>",
    ]
    return send_message("\n".join(lines))


def notify_publish_failed(article_count: int) -> bool:
    """Alert when articles were generated but WordPress rejected every publish."""
    lines = [
        "<b>⚠️ Waqya pipeline — publish failed</b>",
        "",
        f"Generated {article_count} article{'s' if article_count != 1 else ''}, "
        "but nothing reached WordPress (403 after retries).",
        "",
        "Usually Hostinger WAF blocking GitHub Actions IPs — not a bad password.",
        "Check hPanel WAF / allow <code>/wp-json/*</code>. Secrets are OK if local runs work.",
        "",
        "Check Actions logs for <code>wp-json/wp/v2/posts</code> errors.",
    ]
    return send_message("\n".join(lines))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    send_message("<b>Waqya Bot Test</b>\n\nIf you see this, notifications are working!")
