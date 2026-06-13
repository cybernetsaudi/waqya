#!/usr/bin/env python3
"""Push trust page HTML from theme content/ to WordPress."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import requests

log = logging.getLogger(__name__)

THEME_CONTENT = Path(__file__).resolve().parent.parent / "wordpress/theme/waqya/content/trust-pages"

SLUGS = ["editorial-policy", "corrections", "about", "contact", "privacy-policy"]


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


def _page_html(slug: str) -> str:
    path = THEME_CONTENT / f"{slug}.html"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path.read_text().strip()


def sync() -> int:
    from yoast_seo import PAGE_SEO

    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    updated = 0

    for slug in SLUGS:
        params = {"slug": slug, "context": "edit"}
        if slug == "privacy-policy":
            params["status"] = "any"
        r = requests.get(
            f"{base}/wp-json/wp/v2/pages",
            params=params,
            auth=auth,
            timeout=30,
        )
        r.raise_for_status()
        pages = r.json()
        if not pages:
            log.warning("Page not found: %s — run setup_trust_pages.py first", slug)
            continue

        page_id = pages[0]["id"]
        seo = PAGE_SEO.get(slug, {})
        html = _page_html(slug)

        payload = {
            "content": html,
            "meta": {
                "_yoast_wpseo_title": seo.get("seo_title", pages[0]["title"]["raw"]),
                "_yoast_wpseo_metadesc": seo.get("metadesc", "")[:155],
                "_yoast_wpseo_focuskw": seo.get("focuskw", ""),
            },
        }

        requests.post(
            f"{base}/wp-json/wp/v2/pages/{page_id}",
            json=payload,
            auth=auth,
            timeout=60,
        ).raise_for_status()
        log.info("Synced trust page: /%s/ (%d bytes)", slug, len(html))
        updated += 1

    _link_privacy_policy_page(base, auth)
    return updated


def _link_privacy_policy_page(base: str, auth: tuple[str, str]) -> None:
    """Set WordPress privacy policy page ID for subscriber plugin + core."""
    r = requests.get(
        f"{base}/wp-json/wp/v2/pages",
        params={"slug": "privacy-policy", "per_page": 1},
        auth=auth,
        timeout=30,
    )
    r.raise_for_status()
    pages = r.json()
    if not pages:
        log.warning("privacy-policy page not found — run setup_trust_pages.py")
        return
    page_id = pages[0]["id"]
    requests.post(
        f"{base}/wp-json/wp/v2/settings",
        json={"page_for_privacy_policy": page_id},
        auth=auth,
        timeout=30,
    ).raise_for_status()
    log.info("Linked WP privacy policy page ID %d", page_id)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_env()
    n = sync()
    log.info("Done — %d pages updated", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
