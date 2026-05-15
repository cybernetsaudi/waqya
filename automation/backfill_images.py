#!/usr/bin/env python3
"""
Backfill images + SEO on existing WordPress posts (drafts and published).

Usage:
  cd automation && python backfill_images.py
  python backfill_images.py --status publish
  python backfill_images.py --ids 5,6
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys

import requests
from dotenv import load_dotenv

log = logging.getLogger("backfill")


def _auth():
    base = os.environ["WP_URL"].rstrip("/")
    return base, (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])


def _strip_images(html: str) -> str:
    html = re.sub(
        r'<figure class="wp-block-image[^"]*">[\s\S]*?</figure>',
        "",
        html,
    )
    from seo import strip_existing_waqya_blocks

    return strip_existing_waqya_blocks(html)


def _extract_tags(post: dict) -> list[str]:
    return []  # filled via tag endpoint if needed


def backfill_post(post: dict, base_url: str, auth: tuple[str, str]) -> bool:
    from image_fetcher import fetch_article_images
    from publisher import _build_article_html, upload_media
    from seo import optimize_published_post

    post_id = post["id"]
    title = post["title"]["rendered"]
    raw = post.get("content", {}).get("rendered", "")
    excerpt = re.sub(r"<[^>]+>", "", post.get("excerpt", {}).get("rendered", ""))[:200]

    # Guess image query from title
    image_query = title
    tags: list[str] = []

    # Try to find source link in content
    source_url = base_url
    m = re.search(r'href="(https?://[^"]+)"[^>]*>.*original', raw, re.I)
    if m:
        source_url = m.group(1)

    images = fetch_article_images(title, image_query, source_url, tags)
    if not images.featured:
        log.warning("No images for post #%d — %s", post_id, title)
        return False

    if images.featured:
        upload_media(base_url, auth, images.featured, title)
    for i, img in enumerate(images.inline):
        upload_media(base_url, auth, img, f"{title} — {i + 2}")

    paras = re.findall(r"<p[^>]*>([\s\S]*?)</p>", raw)
    paras = [re.sub(r"<[^>]+>", "", p).strip() for p in paras if p.strip()]
    paras = [p for p in paras if "Source:" not in p and "waqya-related" not in p]
    body_text = "\n\n".join(paras) if paras else excerpt

    class FakeArticle:
        pass

    fa = FakeArticle()
    fa.body = body_text if len(body_text) > 200 else excerpt
    fa.source_url = source_url
    fa.source_name = "Source"
    fa.headline = title

    content = _build_article_html(fa, images)

    meta_desc = excerpt or title
    update = {"content": content}
    if images.featured and images.featured.wp_media_id:
        update["featured_media"] = images.featured.wp_media_id

    resp = requests.post(
        f"{base_url}/wp-json/wp/v2/posts/{post_id}",
        json=update,
        auth=auth,
        timeout=60,
    )
    resp.raise_for_status()
    post_url = resp.json().get("link", f"{base_url}/?p={post_id}")
    featured_url = images.featured.wp_url if images.featured else None

    optimize_published_post(
        post_id=post_id,
        headline=title,
        meta_description=meta_desc,
        tags=tags,
        content_html=content,
        post_url=post_url,
        featured_image_url=featured_url,
        category_ids=post.get("categories", []),
    )
    log.info("Updated post #%d with images", post_id)
    return True


def main():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--status", default="draft,publish", help="Comma-separated statuses")
    parser.add_argument("--ids", default="", help="Comma-separated post IDs")
    args = parser.parse_args()

    base_url, auth = _auth()

    if args.ids:
        posts = []
        for pid in args.ids.split(","):
            r = requests.get(
                f"{base_url}/wp-json/wp/v2/posts/{pid.strip()}",
                auth=auth,
                timeout=15,
            )
            r.raise_for_status()
            posts.append(r.json())
    else:
        statuses = args.status.split(",")
        posts = []
        for status in statuses:
            r = requests.get(
                f"{base_url}/wp-json/wp/v2/posts",
                params={"status": status.strip(), "per_page": 50},
                auth=auth,
                timeout=15,
            )
            r.raise_for_status()
            posts.extend(r.json())

    ok = 0
    for post in posts:
        try:
            if backfill_post(post, base_url, auth):
                ok += 1
        except Exception:
            log.exception("Failed post #%s", post.get("id"))
    log.info("Backfill complete: %d / %d posts updated", ok, len(posts))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
