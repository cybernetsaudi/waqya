#!/usr/bin/env python3
"""
Remove duplicate Pexels photos across posts (and within a post).

Keeps the oldest post's images; refetches unique images for newer duplicates.
Also supports deleting duplicate story clusters (e.g. James Webb).

Usage:
  python fix_duplicate_images.py --dry-run
  python fix_duplicate_images.py --fix-images
  python fix_duplicate_images.py --delete-webb-duplicates
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

log = logging.getLogger(__name__)


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

_PEXELS_ID_RE = re.compile(r"pexels\.com/photo/[^/\"]+-(\d+)", re.I)
_WP_IMAGE_RE = re.compile(r"wp-image-(\d+)", re.I)

WEBB_DELETE_IDS = [206, 566, 572, 620, 884, 908, 1290, 1350]
WEBB_KEEP = {1984, 1356}


def _auth():
    base = os.environ["WP_URL"].rstrip("/")
    return base, (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])


def fetch_all_posts(base: str, auth: tuple[str, str]) -> list[dict]:
    posts: list[dict] = []
    page = 1
    while page <= 15:
        r = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={
                "per_page": 100,
                "page": page,
                "status": "publish",
                "_fields": "id,title,date,featured_media,content,excerpt,categories",
            },
            auth=auth,
            timeout=60,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            break
        page += 1
    return posts


def fetch_media_pexels_map(base: str, auth: tuple[str, str]) -> dict[int, str]:
    out: dict[int, str] = {}
    page = 1
    while page <= 20:
        r = requests.get(
            f"{base}/wp-json/wp/v2/media",
            params={"per_page": 100, "page": page, "_fields": "id,caption"},
            auth=auth,
            timeout=60,
        )
        if r.status_code != 200:
            break
        batch = r.json()
        if not batch:
            break
        for m in batch:
            cap = (m.get("caption") or {}).get("rendered", "")
            mm = _PEXELS_ID_RE.search(cap)
            if mm:
                out[m["id"]] = mm.group(1)
        if page >= int(r.headers.get("X-WP-TotalPages", 1)):
            break
        page += 1
    return out


def post_pexels_ids(post: dict, media_map: dict[int, str]) -> list[str]:
    ids: list[str] = []
    fm = post.get("featured_media") or 0
    if fm and fm in media_map:
        ids.append(media_map[fm])
    html = (post.get("content") or {}).get("rendered", "")
    for mid in _WP_IMAGE_RE.findall(html):
        if int(mid) in media_map:
            ids.append(media_map[int(mid)])
    return ids


def delete_posts(base: str, auth: tuple[str, str], ids: list[int], *, dry_run: bool) -> int:
    n = 0
    for pid in ids:
        if dry_run:
            log.info("[dry-run] Would delete post #%d", pid)
            n += 1
            continue
        r = requests.delete(
            f"{base}/wp-json/wp/v2/posts/{pid}",
            params={"force": True},
            auth=auth,
            timeout=30,
        )
        if r.status_code in (200, 410):
            log.info("Deleted post #%d", pid)
            n += 1
        else:
            log.error("Delete failed #%d: %s", pid, r.text[:200])
    return n


def plan_image_fixes(posts: list[dict], media_map: dict[int, str]) -> set[int]:
    """Posts that need new images (duplicate pexels vs older post or within-post dup)."""
    pexels_keep_post: dict[str, int] = {}
    for post in sorted(posts, key=lambda p: p.get("date", "")):
        pid = post["id"]
        for px in set(post_pexels_ids(post, media_map)):
            if px not in pexels_keep_post:
                pexels_keep_post[px] = pid

    need_fix: set[int] = set()
    for post in posts:
        pid = post["id"]
        px_list = post_pexels_ids(post, media_map)
        if len(px_list) != len(set(px_list)):
            need_fix.add(pid)
            continue
        for px in set(px_list):
            if pexels_keep_post.get(px) != pid:
                need_fix.add(pid)
    return need_fix


def fix_post_images(
    post: dict,
    base: str,
    auth: tuple[str, str],
    reserved_pexels: set[str],
    *,
    dry_run: bool,
) -> bool:
    from backfill_images import backfill_post

    if dry_run:
        log.info("[dry-run] Would refetch images for #%d", post["id"])
        return True

    # Temporarily clear images.db entries for this post's pexels so we can replace?
    # Use exclude_pexels=reserved_pexels only — stronger.
    import html as html_mod

    post_id = post["id"]
    title = html_mod.unescape(post["title"]["rendered"])

    from image_fetcher import fetch_article_images
    from publisher import _build_article_html, upload_media

    raw = post.get("content", {}).get("rendered", "")
    excerpt = re.sub(r"<[^>]+>", "", post.get("excerpt", {}).get("rendered", ""))[:200]
    source_url = base
    m = re.search(r'href="(https?://[^"]+)"[^>]*>.*original', raw, re.I)
    if m:
        source_url = m.group(1)

    exclude = set(reserved_pexels)
    images = fetch_article_images(title, title, source_url, [], exclude_pexels=exclude)
    if not images.featured:
        log.warning("No unique images for #%d", post_id)
        return False

    if images.featured:
        upload_media(base_url=base, auth=auth, image=images.featured, title=title)
    for i, img in enumerate(images.inline):
        upload_media(base_url=base, auth=auth, image=img, title=f"{title} — {i + 2}")

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
    fa.waqya_read = ""

    content = _build_article_html(fa, images)
    update = {"content": content}
    if images.featured and images.featured.wp_media_id:
        update["featured_media"] = images.featured.wp_media_id

    requests.post(
        f"{base}/wp-json/wp/v2/posts/{post_id}",
        json=update,
        auth=auth,
        timeout=90,
    ).raise_for_status()

    for img in [images.featured, *(images.inline or [])]:
        if img and img.pexels_id is not None:
            reserved_pexels.add(str(img.pexels_id))
    log.info("Fixed images on post #%d", post_id)
    return True


def main() -> int:
    _load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delete-webb-duplicates", action="store_true")
    parser.add_argument("--fix-images", action="store_true")
    parser.add_argument("--delay", type=float, default=3.0, help="Seconds between image fixes")
    args = parser.parse_args()

    if not args.delete_webb_duplicates and not args.fix_images:
        parser.error("Specify --delete-webb-duplicates and/or --fix-images (or --dry-run)")

    base, auth = _auth()
    posts = fetch_all_posts(base, auth)
    media_map = fetch_media_pexels_map(base, auth)

    if args.delete_webb_duplicates:
        delete_posts(base, auth, WEBB_DELETE_IDS, dry_run=args.dry_run)
        posts = [p for p in posts if p["id"] not in WEBB_DELETE_IDS]

    if args.fix_images:
        need = plan_image_fixes(posts, media_map)
        log.info("Posts needing unique images: %d / %d", len(need), len(posts))
        reserved: set[str] = set()
        # Reserve pexels from posts we are NOT fixing (keepers)
        for post in sorted(posts, key=lambda p: p.get("date", "")):
            if post["id"] not in need:
                for px in set(post_pexels_ids(post, media_map)):
                    reserved.add(px)

        fixed = 0
        for post in sorted(posts, key=lambda p: p.get("date", "")):
            if post["id"] not in need:
                continue
            try:
                if fix_post_images(post, base, auth, reserved, dry_run=args.dry_run):
                    fixed += 1
                if not args.dry_run:
                    time.sleep(args.delay)
            except Exception:
                log.exception("Failed post #%s", post.get("id"))

        if not args.dry_run:
            from image_dedup import sync_used_from_wordpress

            n = sync_used_from_wordpress()
            log.info("Synced %d Pexels ids to images.db", n)

        log.info("Image fix complete: %d posts", fixed)

    return 0


if __name__ == "__main__":
    sys.exit(main())
