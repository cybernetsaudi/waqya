"""
Automated SEO — runs after each post is saved.

- Yoast meta fields (title, description, focus keyword)
- JSON-LD Article schema in content
- Related internal links (helps crawl depth)
- Ping Google & Bing sitemaps
- IndexNow URL submission (fast indexing when configured)
"""

from __future__ import annotations

import json
import logging
import os
import re
from html import escape
from typing import Optional

import requests
import yaml

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _site_url() -> str:
    return os.environ.get("WP_URL", "https://waqya.com").rstrip("/")


def _focus_keyword(headline: str, tags: list[str]) -> str:
    if tags:
        return tags[0][:60]
    return " ".join(headline.split()[:4])[:60]


def build_json_ld(
    headline: str,
    description: str,
    url: str,
    date_published: str,
    image_url: Optional[str] = None,
) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": headline,
        "description": description,
        "url": url,
        "datePublished": date_published,
        "author": {"@type": "Organization", "name": "Waqya"},
        "publisher": {
            "@type": "Organization",
            "name": "Waqya",
            "logo": {
                "@type": "ImageObject",
                "url": f"{_site_url()}/wp-content/uploads/logo.png",
            },
        },
    }
    if image_url:
        data["image"] = [image_url]
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def fetch_related_posts(
    base_url: str,
    auth: tuple[str, str],
    category_ids: list[int],
    exclude_id: int,
    limit: int = 3,
) -> list[dict]:
    params: dict = {
        "per_page": limit + 5,
        "status": "publish,draft",
        "_fields": "id,title,link",
    }
    if category_ids:
        params["categories"] = category_ids[0]
    try:
        resp = requests.get(
            f"{base_url}/wp-json/wp/v2/posts",
            params=params,
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        return [p for p in resp.json() if p["id"] != exclude_id][:limit]
    except Exception:
        log.exception("Failed to fetch related posts")
        return []




def build_related_html(related: list[dict]) -> str:
    if not related:
        return ""
    items = "".join(
        f'<li><a href="{escape(p["link"])}">'
        f'{escape(p["title"]["rendered"] if isinstance(p["title"], dict) else p["title"])}'
        f"</a></li>"
        for p in related
    )
    return f'<div class="waqya-related"><h3>Related on Waqya</h3><ul>{items}</ul></div>'


def ping_sitemap(sitemap_url: str) -> None:
    endpoints = [
        f"https://www.google.com/ping?sitemap={sitemap_url}",
        f"https://www.bing.com/ping?sitemap={sitemap_url}",
    ]
    for url in endpoints:
        try:
            resp = requests.get(url, timeout=5)
            log.info("Sitemap ping %s → %s", url.split("?")[0], resp.status_code)
        except Exception:
            log.debug("Sitemap ping skipped: %s", url.split("?")[0])


def submit_indexnow(urls: list[str]) -> None:
    key = os.environ.get("INDEXNOW_KEY", "").strip()
    host = _site_url().replace("https://", "").replace("http://", "")
    if not key or not urls:
        return
    payload = {
        "host": host,
        "key": key,
        "keyLocation": f"{_site_url()}/{key}.txt",
        "urlList": urls,
    }
    try:
        resp = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=15)
        log.info("IndexNow submit → %s", resp.status_code)
    except Exception:
        log.exception("IndexNow submission failed")


def strip_existing_waqya_blocks(html: str) -> str:
    html = re.sub(
        r'<script type="application/ld\+json">.*?</script>',
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(r'<div class="waqya-related">[\s\S]*?</div>', "", html)
    return html.strip()


def optimize_published_post(
    post_id: int,
    headline: str,
    meta_description: str,
    tags: list[str],
    content_html: str,
    post_url: str,
    featured_image_url: Optional[str] = None,
    category_ids: Optional[list[int]] = None,
) -> None:
    config = _load_config()
    if not config.get("seo", {}).get("enabled", True):
        return

    base_url = _site_url()
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    focus = _focus_keyword(headline, tags)
    seo_cfg = config.get("seo", {})

    content_html = strip_existing_waqya_blocks(content_html)
    extra_html = ""

    if seo_cfg.get("add_related_links", True):
        related = fetch_related_posts(base_url, auth, category_ids or [], post_id, limit=3)
        extra_html += build_related_html(related)

    if seo_cfg.get("add_schema", True):
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        extra_html = build_json_ld(headline, meta_description, post_url, now, featured_image_url) + extra_html

    new_content = content_html + ("\n\n" + extra_html if extra_html else "")

    meta = {
        "_yoast_wpseo_title": headline[:60],
        "_yoast_wpseo_metadesc": meta_description[:155],
        "_yoast_wpseo_focuskw": focus,
    }

    try:
        requests.post(
            f"{base_url}/wp-json/wp/v2/posts/{post_id}",
            json={"content": new_content, "meta": meta},
            auth=auth,
            timeout=30,
        )
        log.info("SEO meta applied to post #%d (focus: %s)", post_id, focus)
    except Exception:
        log.exception("SEO update failed for post #%d", post_id)

    if seo_cfg.get("ping_sitemaps", True):
        ping_sitemap(f"{base_url}/wp-sitemap.xml")

    if seo_cfg.get("indexnow", True):
        submit_indexnow([post_url])
