#!/usr/bin/env python3
"""
Rule-based recategorize of Uncategorized posts (no LLM required).

Fixes the mass Uncategorized problem caused by WP category search failing on
names that contain "&" (e.g. Technology & AI).

Usage:
  cd automation && python3 recategorize_uncategorized.py --limit 100
  python3 recategorize_uncategorized.py --limit 500 --dry-run
"""

from __future__ import annotations

import argparse
import html
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests

log = logging.getLogger("recat_uncat")


def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def _auth():
    base = os.environ["WP_URL"].rstrip("/")
    return base, (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])


def _strip(raw: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw or ""))
    return re.sub(r"\s+", " ", text).strip()


def _slug_map(base: str, auth: tuple[str, str]) -> dict[str, int]:
    out: dict[str, int] = {}
    page = 1
    while page <= 20:
        r = requests.get(
            f"{base}/wp-json/wp/v2/categories",
            auth=auth,
            params={"per_page": 100, "page": page, "_fields": "id,slug"},
            timeout=30,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for c in batch:
            out[c["slug"]] = int(c["id"])
        page += 1
        if len(batch) < 100:
            break
    return out


def main() -> int:
    _load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--sleep", type=float, default=0.2)
    args = parser.parse_args()

    sys.path.insert(0, str(Path(__file__).parent))
    from taxonomy import resolve_primary, suggest_primary_from_story

    base, auth = _auth()
    slugs = _slug_map(base, auth)
    uncat_id = slugs.get("uncategorized", 1)
    log.info("Loaded %d categories; uncategorized id=%s", len(slugs), uncat_id)

    posts: list[dict] = []
    page = 1
    while len(posts) < args.limit and page <= 40:
        r = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            auth=auth,
            params={
                "categories": uncat_id,
                "per_page": min(50, args.limit - len(posts)),
                "page": page,
                "orderby": "date",
                "order": "desc",
                "status": "publish",
                "_fields": "id,title,excerpt,content,categories,date",
            },
            timeout=40,
        )
        if r.status_code != 200:
            log.error("Fetch failed: %s %s", r.status_code, r.text[:200])
            break
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        page += 1
        if len(batch) < 50:
            break

    log.info("Recategorizing %d uncategorized posts…", len(posts))
    ok = skipped = failed = 0
    for post in posts:
        title = _strip(post["title"]["rendered"])
        excerpt = _strip(post.get("excerpt", {}).get("rendered", ""))
        body = _strip(post.get("content", {}).get("rendered", ""))[:1500]
        summary = excerpt or body
        key = suggest_primary_from_story(title, summary)
        primary = resolve_primary(key, title=title, summary=summary)
        slug = primary["slug"]
        cat_id = slugs.get(slug)
        if not cat_id or cat_id == uncat_id:
            log.warning("Skip #%d — no desk for %s (%s)", post["id"], slug, title[:50])
            skipped += 1
            continue
        if args.dry_run:
            log.info("DRY #%d → %s | %s", post["id"], primary["label"], title[:55])
            ok += 1
            continue
        try:
            resp = requests.post(
                f"{base}/wp-json/wp/v2/posts/{post['id']}",
                auth=auth,
                json={
                    "categories": [cat_id],
                    "meta": {
                        "_waqya_primary_category": primary["primary_key"],
                        "_waqya_iptc_topic": primary["primary_key"],
                        "_waqya_iptc_code": primary["iptc_code"],
                        "_waqya_iptc_label": primary["label"],
                    },
                },
                timeout=40,
            )
            resp.raise_for_status()
            ok += 1
            log.info("#%d → %s | %s", post["id"], primary["label"], title[:55])
        except Exception:
            log.exception("Failed #%d", post["id"])
            failed += 1
        time.sleep(args.sleep)

    log.info("Done: ok=%d skipped=%d failed=%d", ok, skipped, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
