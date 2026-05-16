#!/usr/bin/env python3
"""
Create all IPTC Media Topic categories in WordPress (one-time or after taxonomy updates).

Usage:
  cd automation && python sync_categories.py
"""

from __future__ import annotations

import logging
import os
import re
import sys

import requests
from dotenv import load_dotenv

from taxonomy import load_taxonomy

log = logging.getLogger("sync_categories")


def _slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:50] or "category"


def sync_all() -> int:
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    tax = load_taxonomy()
    created = 0

    # Fetch existing categories
    existing: dict[str, dict] = {}
    page = 1
    while True:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/categories",
            params={"per_page": 100, "page": page},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for cat in batch:
            existing[cat["name"].lower()] = cat
        page += 1
        if len(batch) < 100:
            break

    log.info("Found %d existing WordPress categories", len(existing))

    for key, topic in tax.get("topics", {}).items():
        name = topic["wp_category"]
        slug = _slugify(key.replace("_", "-"))
        desc = (
            f"IPTC {topic['iptc_code']} — {topic['label']}. "
            f"{topic.get('description', '')}"
        )

        if name.lower() in existing:
            cat_id = existing[name.lower()]["id"]
            # Update description so admins see IPTC standard in WP
            requests.post(
                f"{base}/wp-json/wp/v2/categories/{cat_id}",
                json={"description": desc, "slug": slug},
                auth=auth,
                timeout=15,
            )
            log.info("  ✓ exists: %s (id=%d)", name, cat_id)
            continue

        resp = requests.post(
            f"{base}/wp-json/wp/v2/categories",
            json={"name": name, "slug": slug, "description": desc},
            auth=auth,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            cat_id = resp.json()["id"]
            log.info("  + created: %s (id=%d, slug=%s)", name, cat_id, slug)
            created += 1
        elif resp.status_code == 400:
            data = resp.json()
            if data.get("code") == "term_exists":
                tid = data.get("data", {}).get("term_id") or (
                    data.get("additional_data", [None])[0]
                )
                if tid:
                    existing[name.lower()] = {"id": tid, "name": name}
                    log.info("  ✓ exists: %s (id=%d)", name, tid)
            else:
                log.error("  ! failed: %s — %s", name, resp.text[:200])
        else:
            log.error("  ! failed: %s — %s", name, resp.text[:200])

    return created


def main() -> int:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not os.environ.get("WP_URL"):
        log.error("WP_URL not set in .env")
        return 1

    log.info("Syncing IPTC categories to %s …\n", os.environ["WP_URL"])
    n = sync_all()
    log.info("\nDone. %d new categories created.", n)
    log.info("View in WP Admin → Posts → Categories")
    return 0


if __name__ == "__main__":
    sys.exit(main())
