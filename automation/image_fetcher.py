"""
Image fetcher — hero + inline images for each article.

Providers: pexels (free), og_image, openai (DALL-E).
Requires PEXELS_API_KEY in .env (not .env.example).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import requests
import yaml

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
USER_AGENT = "WaqyaBot/1.0 (+https://waqya.com)"


@dataclass
class FetchedImage:
    data: bytes
    filename: str
    mime_type: str
    alt_text: str
    credit: str
    wp_media_id: Optional[int] = None
    wp_url: Optional[str] = None


@dataclass
class ArticleImages:
    featured: Optional[FetchedImage] = None
    inline: list[FetchedImage] = field(default_factory=list)


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _download(url: str, timeout: int = 25) -> Optional[bytes]:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        if len(resp.content) < 1024:
            return None
        return resp.content
    except Exception:
        log.exception("Image download failed: %s", url)
        return None


def _pexels_key() -> str:
    return os.environ.get("PEXELS_API_KEY", "").strip()


def _expand_queries(base: str, tags: list[str], count: int) -> list[str]:
    """Build distinct search queries for multiple images."""
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = q.strip()[:80]
        key = q.lower()
        if q and key not in seen:
            seen.add(key)
            queries.append(q)

    add(base)
    for tag in tags:
        add(tag)
        add(f"{tag} news")
    add(f"{base} editorial")
    add(f"{base} headline")

    while len(queries) < count:
        add(f"{base} {len(queries)}")
    return queries[:count]


def _photo_to_image(photo: dict, idx: int, query: str) -> Optional[FetchedImage]:
    src = photo.get("src", {}).get("large") or photo.get("src", {}).get("medium")
    if not src:
        return None
    data = _download(src)
    if not data:
        return None
    photographer = photo.get("photographer", "Pexels")
    link = photo.get("url", "https://www.pexels.com")
    credit = f'Photo: <a href="{link}">{photographer}</a> / Pexels'
    return FetchedImage(
        data=data,
        filename=f"image-{idx}.jpg",
        mime_type="image/jpeg",
        alt_text=query[:120],
        credit=credit,
    )


def _pexels_search(query: str, per_page: int = 4, page: int = 1) -> list[FetchedImage]:
    api_key = _pexels_key()
    if not api_key:
        log.warning("PEXELS_API_KEY not set")
        return []

    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            params={
                "query": query,
                "per_page": per_page,
                "page": page,
                "orientation": "landscape",
            },
            headers={"Authorization": api_key},
            timeout=20,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        out: list[FetchedImage] = []
        for i, photo in enumerate(photos):
            img = _photo_to_image(photo, i + 1, query)
            if img:
                out.append(img)
        return out
    except Exception:
        log.exception("Pexels search failed: %s", query)
        return []


def _from_og_image(page_url: str) -> Optional[FetchedImage]:
    try:
        resp = requests.get(page_url, timeout=15, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        html = resp.text[:500_000]
    except Exception:
        return None

    for pat in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ):
        m = re.search(pat, html, re.I)
        if m:
            image_url = urljoin(page_url, m.group(1).strip())
            data = _download(image_url)
            if data:
                return FetchedImage(
                    data=data,
                    filename="featured.jpg",
                    mime_type="image/jpeg",
                    alt_text="Story image",
                    credit=f'Source: <a href="{page_url}">original</a>',
                )
    return None


def fetch_article_images(
    headline: str,
    image_query: str,
    source_url: str,
    tags: list[str] | None = None,
) -> ArticleImages:
    """Fetch 1 featured + N inline images."""
    config = _load_config()
    img_cfg = config.get("images", {})
    if not img_cfg.get("enabled", True):
        return ArticleImages()

    inline_count = int(img_cfg.get("inline_count", 3))
    total_needed = 1 + inline_count
    base = (image_query or headline).strip()
    tag_list = tags or []
    queries = _expand_queries(base, tag_list, total_needed)

    collected: list[FetchedImage] = []
    for i, q in enumerate(queries):
        if len(collected) >= total_needed:
            break
        batch = _pexels_search(q, per_page=2, page=1 + (i % 3))
        for img in batch:
            if len(collected) >= total_needed:
                break
            # Avoid duplicate bytes
            if any(existing.data == img.data for existing in collected):
                continue
            collected.append(img)

    if len(collected) < total_needed:
        og = _from_og_image(source_url)
        if og and not any(existing.data == og.data for existing in collected):
            collected.append(og)

    result = ArticleImages()
    if collected:
        result.featured = collected[0]
        result.inline = collected[1 : 1 + inline_count]
        log.info(
            "Images for '%s': 1 featured + %d inline",
            headline[:50],
            len(result.inline),
        )
    else:
        log.warning("No images found for: %s", headline)
    return result


# Backwards compatibility
def fetch_featured_image(
    headline: str,
    image_query: str,
    source_url: str,
    tags: list[str] | None = None,
) -> Optional[FetchedImage]:
    images = fetch_article_images(headline, image_query, source_url, tags)
    return images.featured
