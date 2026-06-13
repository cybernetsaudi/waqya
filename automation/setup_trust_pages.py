#!/usr/bin/env python3
"""
Create or update trust / policy pages on WordPress from theme content files.
"""

from __future__ import annotations

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

THEME_CONTENT = Path(__file__).resolve().parent.parent / "wordpress/theme/waqya/content/trust-pages"

PAGES = [
    {"slug": "editorial-policy", "title": "Editorial Policy"},
    {"slug": "corrections", "title": "Corrections"},
    {"slug": "about", "title": "About Waqya"},
    {"slug": "contact", "title": "Contact"},
    {"slug": "privacy-policy", "title": "Privacy Policy"},
]


def _html(slug: str) -> str:
    return (THEME_CONTENT / f"{slug}.html").read_text().strip()


def ensure_trust_pages() -> int:
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    from yoast_seo import PAGE_SEO

    touched = 0

    for page in PAGES:
        slug = page["slug"]
        try:
            r = requests.get(
                f"{base}/wp-json/wp/v2/pages",
                params={"slug": slug, "per_page": 1},
                auth=auth,
                timeout=15,
            )
            r.raise_for_status()
            existing = r.json()
            seo = PAGE_SEO.get(slug, {})
            meta = {
                "_yoast_wpseo_title": seo.get("seo_title", page["title"]),
                "_yoast_wpseo_metadesc": seo.get("metadesc", "")[:155],
                "_yoast_wpseo_focuskw": seo.get("focuskw", ""),
            }
            body = {"content": _html(slug), "meta": meta}

            if existing:
                page_id = existing[0]["id"]
                requests.post(
                    f"{base}/wp-json/wp/v2/pages/{page_id}",
                    json=body,
                    auth=auth,
                    timeout=60,
                ).raise_for_status()
                log.info("Updated page: %s", slug)
            else:
                requests.post(
                    f"{base}/wp-json/wp/v2/pages",
                    json={
                        "title": page["title"],
                        "slug": slug,
                        "status": "publish",
                        **body,
                    },
                    auth=auth,
                    timeout=60,
                ).raise_for_status()
                log.info("Created page: %s", slug)
            touched += 1
        except Exception:
            log.exception("Page setup failed: %s", slug)
    return touched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _load_env()
    ensure_trust_pages()
