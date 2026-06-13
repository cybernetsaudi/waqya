"""
Image fetcher — hero + inline images for each article.

Providers: pexels (free), og_image, openai (DALL-E).
Requires PEXELS_API_KEY in .env (not .env.example).
"""

from __future__ import annotations

import html
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import requests
import yaml

from image_dedup import (
    ImageBatchContext,
    fingerprint,
    is_image_used,
    is_source_url_used,
    mark_image_used,
)

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
    pexels_id: Optional[int] = None
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


def _clean_query(text: str) -> str:
    """Short, safe search string for stock photo APIs."""
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"[^\w\s-]", " ", text)
    words = [w for w in text.split() if w][:6]
    return " ".join(words) if words else "news"


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

    n = 0
    while len(queries) < count and n < 12:
        n += 1
        add(f"{base[:30]} news {n}")
    return queries[:count]


def _photo_to_image(
    photo: dict,
    idx: int,
    query: str,
    *,
    exclude_pexels: set[str] | None = None,
) -> Optional[FetchedImage]:
    pexels_id = photo.get("id")
    if pexels_id is not None:
        pid = str(pexels_id)
        if exclude_pexels and pid in exclude_pexels:
            return None
        if is_image_used(pexels_id=pexels_id):
            return None

    src = photo.get("src", {}).get("large") or photo.get("src", {}).get("medium")
    if not src:
        return None
    data = _download(src)
    if not data:
        return None
    if is_image_used(data, pexels_id=pexels_id):
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
        pexels_id=int(pexels_id) if pexels_id is not None else None,
    )


def _pexels_search(
    query: str,
    per_page: int = 4,
    start_page: int = 1,
    max_pages: int = 5,
    *,
    exclude_pexels: set[str] | None = None,
) -> list[FetchedImage]:
    api_key = _pexels_key()
    if not api_key:
        log.warning("PEXELS_API_KEY not set")
        return []

    out: list[FetchedImage] = []
    try:
        for page in range(start_page, start_page + max_pages):
            if len(out) >= per_page:
                break
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={
                    "query": query,
                    "per_page": min(15, per_page * 2),
                    "page": page,
                    "orientation": "landscape",
                },
                headers={"Authorization": api_key},
                timeout=20,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                break
            for i, photo in enumerate(photos):
                if len(out) >= per_page:
                    break
                img = _photo_to_image(photo, len(out) + 1, query, exclude_pexels=exclude_pexels)
                if img:
                    out.append(img)
        return out
    except Exception:
        log.exception("Pexels search failed: %s", query)
        return out


def _from_og_image(page_url: str) -> Optional[FetchedImage]:
    try:
        resp = requests.get(page_url, timeout=15, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        page_html = resp.text[:500_000]
    except Exception:
        return None

    for pat in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ):
        m = re.search(pat, page_html, re.I)
        if m:
            image_url = urljoin(page_url, m.group(1).strip())
            data = _download(image_url)
            if data and not is_image_used(data) and not is_source_url_used(image_url):
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
    *,
    exclude_pexels: set[str] | None = None,
    batch_ctx: ImageBatchContext | None = None,
) -> ArticleImages:
    """Fetch 1 featured + N inline images."""
    config = _load_config()
    img_cfg = config.get("images", {})
    if not img_cfg.get("enabled", True):
        return ArticleImages()

    inline_count = int(img_cfg.get("inline_count", 3))
    total_needed = 1 + inline_count
    base = _clean_query(image_query or headline)
    tag_list = [_clean_query(t) for t in (tags or [])]
    queries = _expand_queries(base, tag_list, total_needed)

    collected: list[FetchedImage] = []
    merged_exclude: set[str] = set(exclude_pexels or set())
    if batch_ctx:
        merged_exclude |= batch_ctx.exclude_pexels

    def _add(img: FetchedImage) -> bool:
        fp = fingerprint(img.data)
        if batch_ctx and batch_ctx.is_session_duplicate(img.data):
            return False
        if fp in {fingerprint(x.data) for x in collected}:
            return False
        collected.append(img)
        if batch_ctx:
            batch_ctx.reserve(img)
        return True

    batch = _pexels_search(
        base,
        per_page=total_needed,
        start_page=1,
        max_pages=8,
        exclude_pexels=merged_exclude,
    )
    for img in batch:
        if len(collected) >= total_needed:
            break
        _add(img)

    for i, q in enumerate(queries):
        if len(collected) >= total_needed:
            break
        batch = _pexels_search(
            q,
            per_page=2,
            start_page=1 + (i % 5),
            max_pages=6,
            exclude_pexels=merged_exclude,
        )
        for img in batch:
            if len(collected) >= total_needed:
                break
            _add(img)

    if len(collected) < total_needed:
        og = _from_og_image(source_url)
        if og:
            _add(og)

    result = ArticleImages()
    if collected:
        result.featured = collected[0]
        result.inline = collected[1 : 1 + inline_count]
        for img in collected:
            mark_image_used(
                img.data,
                img.pexels_id,
                context=headline[:120],
            )
            if img.pexels_id is not None:
                merged_exclude.add(str(img.pexels_id))
        log.info(
            "Images for '%s': 1 featured + %d inline (pool: %d used total)",
            headline[:50],
            len(result.inline),
            _used_count(),
        )
    else:
        log.warning("No images found for: %s", headline)
    return result


def _used_count() -> int:
    try:
        from image_dedup import count_used
        return count_used()
    except Exception:
        return 0


# Backwards compatibility
def fetch_featured_image(
    headline: str,
    image_query: str,
    source_url: str,
    tags: list[str] | None = None,
) -> Optional[FetchedImage]:
    images = fetch_article_images(headline, image_query, source_url, tags)
    return images.featured
