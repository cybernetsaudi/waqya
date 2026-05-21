#!/usr/bin/env python3
"""
Fix HTML entity encoding site-wide on WordPress posts.

- Decodes titles and excerpts stored with literal &#8217; etc.
- Rebuilds waqya-related blocks with correct link text.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import requests

log = logging.getLogger(__name__)


def _load_env() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_env()

    from html_utils import has_html_entities, wp_plain_text
    from seo import optimize_published_post, strip_existing_waqya_blocks

    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])

    fixed_titles = 0
    fixed_excerpts = 0
    fixed_seo = 0
    page = 1

    while page <= 25:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={"status": "publish", "per_page": 100, "page": page, "context": "edit"},
            auth=auth,
            timeout=60,
        )
        if resp.status_code == 400:
            break
        resp.raise_for_status()
        posts = resp.json()
        if not posts:
            break

        for post in posts:
            pid = post["id"]
            title_field = post.get("title") or {}
            rendered_title = str(title_field.get("rendered", ""))
            raw_title = str(title_field.get("raw") or rendered_title)
            plain_title = wp_plain_text(raw_title)

            excerpt_field = post.get("excerpt") or {}
            rendered_excerpt = str(excerpt_field.get("rendered", ""))
            raw_excerpt = str(excerpt_field.get("raw") or rendered_excerpt)
            plain_excerpt = wp_plain_text(raw_excerpt)

            content = post.get("content", {}).get("raw") or post.get("content", {}).get("rendered", "")
            has_related = "waqya-related" in content

            payload: dict = {}
            if has_html_entities(raw_title) and plain_title:
                payload["title"] = plain_title
                fixed_titles += 1
            if has_html_entities(raw_excerpt) and plain_excerpt:
                payload["excerpt"] = plain_excerpt
                fixed_excerpts += 1

            if payload:
                try:
                    requests.post(
                        f"{base}/wp-json/wp/v2/posts/{pid}",
                        json=payload,
                        auth=auth,
                        timeout=30,
                    ).raise_for_status()
                    log.info("Updated #%d: %s", pid, list(payload.keys()))
                except Exception:
                    log.exception("Failed to update post #%d", pid)

            if has_related:
                related_html = re.search(r"waqya-related[\s\S]*?</div>", content)
                if related_html and (
                    "&amp;#" in related_html.group(0) or has_html_entities(related_html.group(0))
                ):
                    meta = post.get("meta", {}) or {}
                    stripped = strip_existing_waqya_blocks(content)
                    optimize_published_post(
                        post_id=pid,
                        headline=plain_title,
                        meta_description=meta.get("_yoast_wpseo_metadesc", "") or plain_excerpt[:155],
                        tags=[],
                        content_html=stripped,
                        post_url=post.get("link", ""),
                        category_ids=post.get("categories", []),
                    )
                    fixed_seo += 1

        page += 1

    log.info(
        "Done — titles: %d, excerpts: %d, related blocks rebuilt: %d",
        fixed_titles,
        fixed_excerpts,
        fixed_seo,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
