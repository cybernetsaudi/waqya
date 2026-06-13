"""
Weekly desk breakdown from published WordPress posts (for Telegram ops summary).
"""

from __future__ import annotations

import logging
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests

log = logging.getLogger(__name__)


def _wp_auth() -> tuple[str, tuple[str, str]]:
    base = os.environ["WP_URL"].rstrip("/")
    return base, (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])


def fetch_desk_counts(*, days: int = 7) -> dict[str, int]:
    base, auth = _wp_auth()
    after = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S")

    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={
                "per_page": 100,
                "status": "publish",
                "after": after,
                "orderby": "date",
                "order": "desc",
                "_fields": "id,meta,categories",
            },
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        posts = resp.json()
    except Exception:
        log.exception("Desk report: could not fetch posts")
        return {}

    slug_by_id = _category_slug_map(base, auth)
    counts: Counter[str] = Counter()
    breaking = 0
    otr = 0

    for post in posts:
        meta = post.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}
        if meta.get("_waqya_is_breaking") == "1":
            breaking += 1
        if meta.get("_waqya_format") == "on_the_record":
            otr += 1

        desk = (meta.get("_waqya_primary_category") or "").strip()
        if not desk:
            for cat_id in post.get("categories") or []:
                slug = slug_by_id.get(cat_id, "")
                if slug:
                    desk = slug
                    break
        if not desk:
            desk = "uncategorized"
        counts[desk] += 1

    counts["_breaking"] = breaking
    counts["_on_the_record"] = otr
    counts["_total"] = len(posts)
    return dict(counts)


def _category_slug_map(base: str, auth: tuple[str, str]) -> dict[int, str]:
    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/categories",
            params={"per_page": 100},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        return {c["id"]: c.get("slug", "") for c in resp.json()}
    except Exception:
        return {}


def format_desk_report_lines(*, days: int = 7) -> list[str]:
    counts = fetch_desk_counts(days=days)
    if not counts or counts.get("_total", 0) == 0:
        return [f"No published posts in the last {days} days."]

    total = int(counts.pop("_total", 0))
    breaking = int(counts.pop("_breaking", 0))
    otr = int(counts.pop("_on_the_record", 0))

    lines = [
        f"<b>Last {days} days on site</b>",
        f"Published: {total} · Breaking: {breaking} · On The Record: {otr}",
        "",
    ]

    for desk, n in sorted(counts.items(), key=lambda x: (-x[1], x[0])):
        label = desk.replace("-", " ").title()
        lines.append(f"· {label}: {n}")

    return lines
