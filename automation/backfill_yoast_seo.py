#!/usr/bin/env python3
"""Backfill Yoast SEO fields, slugs, and image alt text on posts and pages."""

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


def _patch_media_alt(base: str, auth: tuple[str, str], media_id: int, alt: str) -> None:
    try:
        requests.post(
            f"{base}/wp-json/wp/v2/media/{media_id}",
            json={"alt_text": alt},
            auth=auth,
            timeout=20,
        ).raise_for_status()
    except Exception:
        log.debug("Media alt update failed for #%d", media_id)


def backfill_pages(base: str, auth: tuple[str, str]) -> int:
    from yoast_seo import PAGE_SEO

    updated = 0
    for slug, seo in PAGE_SEO.items():
        r = requests.get(
            f"{base}/wp-json/wp/v2/pages",
            params={"slug": slug, "context": "edit"},
            auth=auth,
            timeout=20,
        )
        r.raise_for_status()
        pages = r.json()
        if not pages:
            continue
        page = pages[0]
        pid = page["id"]
        meta = {
            "_yoast_wpseo_title": seo["seo_title"],
            "_yoast_wpseo_metadesc": seo["metadesc"][:155],
            "_yoast_wpseo_focuskw": seo["focuskw"],
        }
        requests.post(
            f"{base}/wp-json/wp/v2/pages/{pid}",
            json={"meta": meta},
            auth=auth,
            timeout=30,
        ).raise_for_status()
        log.info("Page SEO: /%s/", slug)
        updated += 1
    return updated


def backfill_posts(
    base: str,
    auth: tuple[str, str],
    limit: int = 200,
    *,
    refresh_related: bool = False,
) -> int:
    from html_utils import wp_plain_text
    from seo import optimize_published_post, strip_existing_waqya_blocks
    from yoast_seo import (
        build_image_alt,
        build_meta_description,
        build_post_slug,
        build_seo_title,
        suggest_focus_keyword,
    )

    updated = 0
    page = 1
    while updated < limit and page <= 15:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={"status": "publish", "per_page": 50, "page": page, "context": "edit"},
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
            if updated >= limit:
                break
            pid = post["id"]
            title = wp_plain_text((post.get("title") or {}).get("raw", ""))
            excerpt = wp_plain_text((post.get("excerpt") or {}).get("raw", ""))
            content = post.get("content", {}).get("raw") or ""
            slug = post.get("slug", "")
            meta = post.get("meta") or {}

            primary = meta.get("_waqya_primary_category", "") or ""
            tags = []
            tag_ids = post.get("tags") or []
            if tag_ids:
                tr = requests.get(
                    f"{base}/wp-json/wp/v2/tags",
                    params={"include": ",".join(str(t) for t in tag_ids[:15])},
                    auth=auth,
                    timeout=15,
                )
                if tr.ok:
                    tags = [t["name"] for t in tr.json()]

            focus = suggest_focus_keyword(
                headline=title,
                summary=excerpt,
                primary_key=primary,
                tags=tags,
            )
            seo_title = build_seo_title(focus, title)
            metadesc = build_meta_description(
                focus,
                meta.get("_yoast_wpseo_metadesc", "") or excerpt,
                title,
            )
            new_slug = build_post_slug(focus, title)

            payload: dict = {
                "meta": {
                    "_yoast_wpseo_title": seo_title,
                    "_yoast_wpseo_metadesc": metadesc,
                    "_yoast_wpseo_focuskw": focus,
                }
            }
            if new_slug and new_slug != slug:
                payload["slug"] = new_slug

            requests.post(
                f"{base}/wp-json/wp/v2/posts/{pid}",
                json=payload,
                auth=auth,
                timeout=90,
            ).raise_for_status()

            featured = post.get("featured_media")
            if featured:
                alt = build_image_alt(focus, title, "featured")
                _patch_media_alt(base, auth, int(featured), alt)

            if (refresh_related and "waqya-related" in content) or False:
                stripped = strip_existing_waqya_blocks(content)
                optimize_published_post(
                    post_id=pid,
                    headline=title,
                    meta_description=metadesc,
                    tags=tags,
                    content_html=stripped,
                    post_url=post.get("link", ""),
                    category_ids=post.get("categories", []),
                    focus_keyword=focus,
                    seo_title=seo_title,
                )
            log.info("Post #%d SEO: %s | focus=%s", pid, seo_title[:45], focus)
            updated += 1

        page += 1

    return updated


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_env()
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    n_pages = backfill_pages(base, auth)
    n_posts = backfill_posts(base, auth)
    log.info("Backfill complete: %d pages, %d posts", n_pages, n_posts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
