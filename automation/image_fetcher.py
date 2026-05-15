"""
Featured image fetcher — attaches a hero image to each article.

Providers (config.yaml → images.provider):
  - pexels   — free stock photos (PEXELS_API_KEY, recommended)
  - og_image — scrape og:image from the source article URL
  - openai   — DALL-E 3 generated image (~$0.04 each)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
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
    credit: str  # HTML snippet for caption / media description


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _download(url: str, timeout: int = 20) -> Optional[bytes]:
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        if len(resp.content) < 1024:
            return None
        return resp.content
    except Exception:
        log.exception("Image download failed: %s", url)
        return None


def _guess_filename(url: str, content_type: str) -> tuple[str, str]:
    ext = ".jpg"
    mime = "image/jpeg"
    if "png" in (content_type or "") or url.lower().endswith(".png"):
        ext, mime = ".png", "image/png"
    elif "webp" in (content_type or "") or url.lower().endswith(".webp"):
        ext, mime = ".webp", "image/webp"
    return f"featured{ext}", mime


def _from_pexels(query: str) -> Optional[FetchedImage]:
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        log.warning("PEXELS_API_KEY not set — skipping Pexels")
        return None

    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            headers={"Authorization": api_key},
            timeout=15,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            return None
        photo = photos[0]
        src = photo.get("src", {}).get("large") or photo.get("src", {}).get("medium")
        if not src:
            return None
        data = _download(src)
        if not data:
            return None
        photographer = photo.get("photographer", "Pexels")
        pexels_link = photo.get("url", "https://www.pexels.com")
        credit = f'Photo: <a href="{pexels_link}">{photographer}</a> / Pexels'
        return FetchedImage(
            data=data,
            filename="featured.jpg",
            mime_type="image/jpeg",
            alt_text=query[:120],
            credit=credit,
        )
    except Exception:
        log.exception("Pexels search failed for query: %s", query)
        return None


def _from_og_image(page_url: str) -> Optional[FetchedImage]:
    try:
        resp = requests.get(
            page_url,
            timeout=15,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        html = resp.text[:500_000]
    except Exception:
        log.exception("Failed to fetch page for og:image: %s", page_url)
        return None

    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    image_url = None
    for pat in patterns:
        m = re.search(pat, html, re.I)
        if m:
            image_url = m.group(1).strip()
            break
    if not image_url:
        return None

    image_url = urljoin(page_url, image_url)
    data = _download(image_url)
    if not data:
        return None
    filename, mime = _guess_filename(image_url, "")
    return FetchedImage(
        data=data,
        filename=filename,
        mime_type=mime,
        alt_text="Story image",
        credit=f'Source image via <a href="{page_url}">original article</a>',
    )


def _from_openai(query: str, headline: str) -> Optional[FetchedImage]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        prompt = (
            f"Editorial news photo for article: {headline}. "
            f"Visual theme: {query}. Photorealistic, dramatic lighting, "
            "no text overlays, no logos, no watermarks."
        )
        result = client.images.generate(
            model="dall-e-3",
            prompt=prompt[:900],
            size="1792x1024",
            quality="standard",
            n=1,
        )
        url = result.data[0].url
        if not url:
            return None
        data = _download(url)
        if not data:
            return None
        return FetchedImage(
            data=data,
            filename="featured.png",
            mime_type="image/png",
            alt_text=headline[:120],
            credit="Image generated with AI",
        )
    except Exception:
        log.exception("DALL-E image generation failed")
        return None


def fetch_featured_image(
    headline: str,
    image_query: str,
    source_url: str,
    tags: list[str] | None = None,
) -> Optional[FetchedImage]:
    """Try configured providers in order until an image is found."""
    config = _load_config()
    img_cfg = config.get("images", {})
    if not img_cfg.get("enabled", True):
        return None

    query = (image_query or headline).strip()
    if tags and not image_query:
        query = f"{headline} {' '.join(tags[:2])}"

    provider = img_cfg.get("provider", "pexels")
    fallbacks = img_cfg.get("fallbacks", ["og_image"])

    chain = [provider] + [f for f in fallbacks if f != provider]

    for name in chain:
        log.info("Trying image provider: %s", name)
        img: Optional[FetchedImage] = None
        if name == "pexels":
            img = _from_pexels(query)
        elif name == "og_image":
            img = _from_og_image(source_url)
        elif name == "openai":
            img = _from_openai(query, headline)
        if img:
            log.info("Featured image found via %s", name)
            return img

    log.warning("No featured image found for: %s", headline)
    return None
