"""
Telegram notifier — sends a summary of newly created drafts
to the site owner so they can review and approve/reject.
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


def notify_new_drafts(results: list[PublishResult], wp_admin_url: str) -> bool:
    """
    Send a Telegram message listing all new drafts awaiting review.
    Includes direct edit links so the owner can approve from their phone.
    """
    if not results:
        log.info("No new drafts to notify about")
        return True

    lines = [
        f"<b>📰 Waqya — {len(results)} new draft{'s' if len(results) != 1 else ''} ready for review</b>",
        "",
    ]

    for i, r in enumerate(results, 1):
        lines.append(f"{i}. <a href=\"{r.edit_url}\">{r.title}</a>")

    lines.append("")
    lines.append(f"<a href=\"{wp_admin_url}/wp-admin/edit.php?post_status=draft\">→ Open all drafts</a>")

    return send_message("\n".join(lines))


def notify_error(error_msg: str) -> bool:
    """Alert the owner about a pipeline failure."""
    text = f"<b>⚠️ Waqya Pipeline Error</b>\n\n<code>{error_msg}</code>"
    return send_message(text)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

    send_message("<b>Waqya Bot Test</b>\n\nIf you see this, notifications are working!")
