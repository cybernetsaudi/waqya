"""
Append developing-story updates when the same source URL appears in feeds again.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

from datetime_utils import gmt_now_iso
from url_utils import normalize_story_url, url_fingerprint

log = logging.getLogger(__name__)


def _wp_auth() -> tuple[str, tuple[str, str]]:
    base = os.environ["WP_URL"].rstrip("/")
    return base, (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])


def fetch_developing_posts(*, window_hours: int = 48) -> dict[str, dict[str, Any]]:
    """
    Map normalized source URL → {post_id, title, update_log, modified}.
  """
    base, auth = _wp_auth()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    out: dict[str, dict[str, Any]] = {}

    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={
                "per_page": 50,
                "status": "publish",
                "orderby": "modified",
                "order": "desc",
                "_fields": "id,title,modified,meta",
            },
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        posts = resp.json()
    except Exception:
        log.exception("Could not fetch developing posts from WordPress")
        return out

    for post in posts:
        meta = post.get("meta") or {}
        if not isinstance(meta, dict):
            continue
        if meta.get("_waqya_developing") != "1":
            continue

        modified = post.get("modified", "")
        try:
            mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
            if mod_dt.tzinfo is None:
                mod_dt = mod_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            mod_dt = datetime.now(timezone.utc)

        pub_cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        if mod_dt < pub_cutoff:
            continue

        src = (meta.get("_waqya_source_url") or "").strip()
        norm = normalize_story_url(src)
        if not norm:
            continue

        title = ""
        if isinstance(post.get("title"), dict):
            title = post["title"].get("rendered", "")
        elif isinstance(post.get("title"), str):
            title = post["title"]

        out[norm] = {
            "post_id": int(post["id"]),
            "title": title,
            "update_log": meta.get("_waqya_update_log") or "[]",
            "modified": mod_dt,
        }
        fp = url_fingerprint(src)
        if fp:
            out[f"fp:{fp}"] = out[norm]

    if out:
        log.info("Developing posts on site: %d source URL(s)", len([k for k in out if not k.startswith("fp:")]))
    return out


def _last_log_note(update_log_json: str) -> str:
    try:
        entries = json.loads(update_log_json or "[]")
    except json.JSONDecodeError:
        return ""
    if not entries:
        return ""
    last = entries[-1]
    if isinstance(last, dict):
        return str(last.get("note", "")).strip()
    return ""


def _build_update_note(story: dict) -> str:
    title = (story.get("title") or "").strip()
    summary = (story.get("summary") or "").strip()
    if summary and len(summary) > 40:
        return summary[:480]
    if title:
        return f"Update: {title[:460]}"
    return "Story updated from source feed"


def append_update_log(existing_json: str, note: str) -> str:
    try:
        entries = json.loads(existing_json or "[]")
        if not isinstance(entries, list):
            entries = []
    except json.JSONDecodeError:
        entries = []

    entries.append({"at": gmt_now_iso(), "note": note[:500]})
    return json.dumps(entries, ensure_ascii=False)


def update_developing_post(post_id: int, note: str, update_log_json: str) -> bool:
    base, auth = _wp_auth()
    new_log = append_update_log(update_log_json, note)

    try:
        resp = requests.post(
            f"{base}/wp-json/wp/v2/posts/{post_id}",
            json={"meta": {"_waqya_update_log": new_log}},
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        log.info("Developing update #%d: %s", post_id, note[:80])
        return True
    except Exception:
        log.exception("Failed to update developing post #%d", post_id)
        return False


def apply_developing_updates(candidates: list[dict], config: dict) -> int:
    """
    Scan ranked feed items; append update-log entries for matching developing posts.
    Returns number of posts updated.
    """
    dev_cfg = config.get("developing", {})
    if dev_cfg.get("enabled", True) is False:
        return 0

    window_hours = int(dev_cfg.get("update_window_hours", 48))
    developing = fetch_developing_posts(window_hours=window_hours)
    if not developing:
        return 0

    updated = 0
    seen_posts: set[int] = set()

    for story in candidates:
        url = (story.get("url") or "").strip()
        norm = normalize_story_url(url)
        fp = url_fingerprint(url)
        match = developing.get(norm) or (developing.get(f"fp:{fp}") if fp else None)
        if not match:
            continue

        post_id = int(match["post_id"])
        if post_id in seen_posts:
            continue

        note = _build_update_note(story)
        if note == _last_log_note(match.get("update_log", "[]")):
            continue

        if update_developing_post(post_id, note, match.get("update_log", "[]")):
            updated += 1
            seen_posts.add(post_id)
            match["update_log"] = append_update_log(match.get("update_log", "[]"), note)

    if updated:
        log.info("Applied %d developing story update(s)", updated)
    return updated
