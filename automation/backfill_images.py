#!/usr/bin/env python3
"""
Backfill images on existing WordPress posts with subject-aware selection.

Editorial rule (person stories): hero must be that person (source OG / Wikipedia),
never a random Pexels face.

Usage:
  cd automation && python3 backfill_images.py --ids 11852,11990,11628
  python3 backfill_images.py --person-stories --limit 20
  python3 backfill_images.py --recent 40 --skip-seo
"""

from __future__ import annotations

import argparse
import html
import logging
import os
import re
import sys
from pathlib import Path

import requests

log = logging.getLogger("backfill")


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


def _extract_source_url(content: str, fallback: str) -> str:
    for pat in (
        r'class="source-attribution"[\s\S]*?href="(https?://[^"]+)"',
        r'href="(https?://[^"]+)"[^>]*>[^<]*(?:original|Source|report)',
    ):
        m = re.search(pat, content or "", re.I)
        if m:
            return html.unescape(m.group(1).replace("&#038;", "&"))
    return fallback


def _resolve_tags(base: str, auth: tuple[str, str], tag_ids: list[int]) -> list[str]:
    names: list[str] = []
    for tid in tag_ids[:12]:
        try:
            r = requests.get(
                f"{base}/wp-json/wp/v2/tags/{tid}",
                auth=auth,
                params={"_fields": "name"},
                timeout=15,
            )
            if r.ok:
                names.append(r.json().get("name") or "")
        except Exception:
            continue
    return [n for n in names if n]


def _resolve_desk(base: str, auth: tuple[str, str], cat_ids: list[int]) -> str:
    for cid in cat_ids[:3]:
        try:
            r = requests.get(
                f"{base}/wp-json/wp/v2/categories/{cid}",
                auth=auth,
                params={"_fields": "slug"},
                timeout=15,
            )
            if r.ok:
                slug = (r.json().get("slug") or "").strip()
                if slug and slug != "uncategorized":
                    return slug
        except Exception:
            continue
    return ""


def _strip_inline_figures(content_html: str) -> str:
    html_out = re.sub(
        r'<figure class="wp-block-image[^"]*">[\s\S]*?</figure>',
        "",
        content_html or "",
    )
    from seo import strip_existing_waqya_blocks

    return strip_existing_waqya_blocks(html_out)


def backfill_post(
    post: dict,
    base_url: str,
    auth: tuple[str, str],
    *,
    skip_seo: bool = False,
    dry_run: bool = False,
) -> bool:
    from image_fetcher import detect_person_subjects, fetch_article_images
    from publisher import _build_article_html, upload_media
    from seo import optimize_published_post

    post_id = post["id"]
    title = html.unescape(post["title"]["rendered"])
    raw = post.get("content", {}).get("rendered", "")
    excerpt = re.sub(r"<[^>]+>", "", post.get("excerpt", {}).get("rendered", ""))[:200]
    tags = _resolve_tags(base_url, auth, post.get("tags") or [])
    desk = _resolve_desk(base_url, auth, post.get("categories") or [])
    source_url = _extract_source_url(raw, base_url)
    subjects = detect_person_subjects(title, tags)

    log.info(
        "Backfill #%d — %s | desk=%s subjects=%s source=%s",
        post_id,
        title[:70],
        desk or "-",
        subjects or "-",
        source_url[:80],
    )

    images = fetch_article_images(
        title,
        title,
        source_url,
        tags,
        desk=desk,
        allow_reuse=True,
    )
    if not images.featured:
        log.warning("No images for post #%d — %s", post_id, title)
        return False

    if dry_run:
        credit = re.sub(r"<[^>]+>", "", images.featured.credit or "")
        log.info(
            "DRY RUN #%d featured alt=%r credit=%r bytes=%d inlines=%d",
            post_id,
            images.featured.alt_text[:80],
            credit[:80],
            len(images.featured.data),
            len(images.inline),
        )
        return True

    if images.featured:
        upload_media(images.featured, title)
    for i, img in enumerate(images.inline):
        upload_media(img, f"{title} — {i + 2}")

    paras = re.findall(r"<p[^>]*>([\s\S]*?)</p>", _strip_inline_figures(raw))
    paras = [re.sub(r"<[^>]+>", "", p).strip() for p in paras if p.strip()]
    paras = [
        p
        for p in paras
        if "Source:" not in p
        and "waqya-related" not in p
        and "The Waqya read" not in p
    ]
    body_text = "\n\n".join(paras) if paras else excerpt

    class FakeArticle:
        pass

    fa = FakeArticle()
    fa.body = body_text if len(body_text) > 200 else (excerpt or title)
    fa.source_url = source_url
    fa.source_name = "Source"
    fa.headline = title
    fa.waqya_read = ""
    fa.category = desk

    content = _build_article_html(fa, images)

    update: dict = {"content": content}
    if images.featured and images.featured.wp_media_id:
        update["featured_media"] = images.featured.wp_media_id

    resp = requests.post(
        f"{base_url}/wp-json/wp/v2/posts/{post_id}",
        json=update,
        auth=auth,
        timeout=90,
    )
    resp.raise_for_status()
    post_url = resp.json().get("link", f"{base_url}/?p={post_id}")
    featured_url = images.featured.wp_url if images.featured else None

    if not skip_seo:
        optimize_published_post(
            post_id=post_id,
            headline=title,
            meta_description=excerpt or title,
            tags=tags,
            content_html=content,
            post_url=post_url,
            featured_image_url=featured_url,
            category_ids=post.get("categories", []),
        )

    credit = re.sub(r"<[^>]+>", "", images.featured.credit or "")
    log.info("Updated #%d — featured: %s", post_id, credit[:100])
    return True


def _fetch_posts(base: str, auth: tuple[str, str], args: argparse.Namespace) -> list[dict]:
    posts: list[dict] = []
    if args.ids:
        for pid in args.ids.split(","):
            r = requests.get(
                f"{base}/wp-json/wp/v2/posts/{pid.strip()}",
                auth=auth,
                timeout=20,
            )
            r.raise_for_status()
            posts.append(r.json())
        return posts

    page = 1
    scan_target = max(args.recent or 0, args.limit or 0, 50)
    if args.person_stories:
        scan_target = max(scan_target, args.recent or 100)
    per_page = min(50, scan_target)
    while len(posts) < scan_target:
        r = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            auth=auth,
            params={
                "status": "publish",
                "per_page": per_page,
                "page": page,
                "orderby": "date",
                "order": "desc",
                "_fields": "id,title,content,excerpt,categories,tags,link,date",
            },
            timeout=30,
        )
        if r.status_code == 400:
            break
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
        if page > 20:
            break

    if args.person_stories:
        from image_fetcher import detect_person_subjects

        filtered = []
        for p in posts:
            title = html.unescape(p["title"]["rendered"])
            if detect_person_subjects(title):
                filtered.append(p)
        log.info("Person-story filter: %d / %d scanned", len(filtered), len(posts))
        posts = filtered

    if args.limit:
        posts = posts[: args.limit]

    return posts


def main() -> int:
    _load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Subject-aware image backfill")
    parser.add_argument("--ids", default="", help="Comma-separated post IDs")
    parser.add_argument("--recent", type=int, default=0, help="N most recent publish posts")
    parser.add_argument("--limit", type=int, default=0, help="Max posts to process")
    parser.add_argument(
        "--person-stories",
        action="store_true",
        help="Only death/tributes/named-person headlines",
    )
    parser.add_argument("--skip-seo", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.ids and not args.recent and not args.person_stories and not args.limit:
        args.person_stories = True
        args.recent = 80
        args.limit = 25
        log.info("Defaulting to --person-stories --recent 80 --limit 25")

    base_url, auth = _auth()
    posts = _fetch_posts(base_url, auth, args)
    if not posts:
        log.error("No posts matched")
        return 1

    ok = 0
    for post in posts:
        try:
            if backfill_post(
                post,
                base_url,
                auth,
                skip_seo=args.skip_seo,
                dry_run=args.dry_run,
            ):
                ok += 1
        except Exception:
            log.exception("Failed post #%s", post.get("id"))

    log.info("Backfill complete: %d / %d posts updated", ok, len(posts))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
