#!/usr/bin/env python3
"""Backfill Yoast SEO fields, HTML structure, slugs, and image alt text."""

from __future__ import annotations

import argparse
import logging
import os
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


def _inline_media_ids(html: str) -> list[int]:
    import re

    ids: list[int] = []
    for m in re.finditer(r'wp-image-(\d+)', html):
        ids.append(int(m.group(1)))
    return ids


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
        try:
            requests.post(
                f"{base}/wp-json/wp/v2/pages/{pid}",
                json={"meta": meta},
                auth=auth,
                timeout=30,
            ).raise_for_status()
        except Exception:
            log.exception("Page SEO failed: /%s/ (#%s)", slug, pid)
            continue
        log.info("Page SEO: /%s/", slug)
        updated += 1
    return updated


def optimize_one_post(
    base: str,
    auth: tuple[str, str],
    post: dict,
    *,
    used_focus: set[str],
    dry_run: bool = False,
) -> bool:
    from content_seo import optimize_post_html
    from html_utils import wp_plain_text
    from seo import strip_existing_waqya_blocks
    from yoast_seo import (
        build_image_alt,
        build_meta_description,
        build_post_slug,
        build_seo_title,
        suggest_focus_keyword,
    )

    pid = post["id"]
    title = wp_plain_text((post.get("title") or {}).get("raw", ""))
    excerpt = wp_plain_text((post.get("excerpt") or {}).get("raw", ""))
    content = post.get("content", {}).get("raw") or ""
    slug = post.get("slug", "")
    meta = post.get("meta") or {}

    primary = meta.get("_waqya_primary_category", "") or ""
    tags: list[str] = []
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

    from yoast_seo import is_strong_focus

    existing_focus = (meta.get("_yoast_wpseo_focuskw") or "").strip()
    if existing_focus and is_strong_focus(existing_focus, title):
        focus = existing_focus
        used_focus.add(existing_focus.lower())
    else:
        focus = suggest_focus_keyword(
            headline=title,
            summary=excerpt,
            primary_key=primary,
            tags=tags,
            used_focus=used_focus,
        )

    seo_title = build_seo_title(focus, title)
    metadesc = build_meta_description(focus, meta.get("_yoast_wpseo_metadesc", "") or excerpt, title)
    new_slug = build_post_slug(focus, title)

    stripped = strip_existing_waqya_blocks(content)
    optimized = optimize_post_html(stripped, focus, title)

    payload: dict = {
        "content": optimized,
        "meta": {
            "_yoast_wpseo_title": seo_title,
            "_yoast_wpseo_metadesc": metadesc,
            "_yoast_wpseo_focuskw": focus[:60],
        },
    }
    if new_slug and new_slug != slug:
        payload["slug"] = new_slug

    if dry_run:
        log.info("[dry-run] #%d %s | focus=%s", pid, seo_title[:50], focus)
        return True

    requests.post(
        f"{base}/wp-json/wp/v2/posts/{pid}",
        json=payload,
        auth=auth,
        timeout=120,
    ).raise_for_status()

    featured = post.get("featured_media")
    if featured:
        _patch_media_alt(base, auth, int(featured), build_image_alt(focus, title, "featured"))
    for mid in _inline_media_ids(optimized):
        _patch_media_alt(base, auth, mid, build_image_alt(focus, title, "inline"))

    log.info("Post #%d SEO: %s | focus=%s", pid, seo_title[:45], focus)
    return True


def backfill_posts(
    base: str,
    auth: tuple[str, str],
    *,
    limit: int = 500,
    post_id: int | None = None,
    dry_run: bool = False,
) -> int:
    from yoast_seo import fetch_used_focus_keywords

    used_focus = fetch_used_focus_keywords(base, auth, pages=12)
    updated = 0

    if post_id:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts/{post_id}",
            params={"context": "edit"},
            auth=auth,
            timeout=60,
        )
        resp.raise_for_status()
        if optimize_one_post(base, auth, resp.json(), used_focus=used_focus, dry_run=dry_run):
            return 1
        return 0

    page = 1
    while updated < limit:
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
            try:
                optimize_one_post(base, auth, post, used_focus=used_focus, dry_run=dry_run)
                updated += 1
            except Exception:
                log.exception("Failed post #%s", post.get("id"))

        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
        page += 1

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill Yoast SEO on Waqya posts")
    parser.add_argument("--limit", type=int, default=500, help="Max posts to process")
    parser.add_argument("--post-id", type=int, default=0, help="Single post ID only")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pages-only", action="store_true", help="Trust/static pages only")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_env()
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])

    n_pages = backfill_pages(base, auth) if not args.post_id else 0
    n_posts = 0
    if not args.pages_only:
        n_posts = backfill_posts(
            base,
            auth,
            limit=args.limit,
            post_id=args.post_id or None,
            dry_run=args.dry_run,
        )
    log.info("Backfill complete: %d pages, %d posts", n_pages, n_posts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
