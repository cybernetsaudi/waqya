#!/usr/bin/env python3
"""
Create trust / policy pages on WordPress if missing (run from pipeline).
"""

from __future__ import annotations

import logging
import os

import requests
from dotenv import load_dotenv

log = logging.getLogger(__name__)

PAGES = [
    {
        "slug": "editorial-policy",
        "title": "Editorial Policy",
        "content": """
<h2>What Waqya publishes</h2>
<p>Waqya publishes original commentary and analysis on news events. We do not copy wire stories. Every piece adds context, stakes, and a clear point of view while attributing facts to named sources.</p>
<h2>Sources</h2>
<p>Facts are drawn from reputable public sources listed at the end of each article. We do not invent quotes, statistics, or events.</p>
<h2>Corrections</h2>
<p>If we get something wrong, we correct it promptly. See our <a href="/corrections/">Corrections</a> page.</p>
<h2>Automation</h2>
<p>Research and drafting may use automation under human editorial standards. Low-quality or unverified pieces are held as drafts, not published.</p>
""",
    },
    {
        "slug": "corrections",
        "title": "Corrections",
        "content": """
<p>We correct errors of fact as soon as we are aware of them. Material changes are noted at the top of the article with a timestamp.</p>
<p>To report an error: contact us via the email on our Contact page with the article URL and what should change.</p>
""",
    },
    {
        "slug": "about",
        "title": "About Waqya",
        "content": """
<p><strong>Waqya</strong> (واقعة — “the incident”) is an English-language commentary desk covering world news with clarity and edge.</p>
<p>We organise coverage by region and topic — Middle East, South Asia, technology, conflict, and more — so readers can follow what matters to them.</p>
""",
    },
    {
        "slug": "contact",
        "title": "Contact",
        "content": """
<p>For corrections, partnerships, or press inquiries, reach the team through the site administrator.</p>
""",
    },
]


def ensure_trust_pages() -> int:
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    created = 0

    for page in PAGES:
        try:
            r = requests.get(
                f"{base}/wp-json/wp/v2/pages",
                params={"slug": page["slug"], "per_page": 1},
                auth=auth,
                timeout=15,
            )
            r.raise_for_status()
            if r.json():
                continue
            from yoast_seo import PAGE_SEO

            seo = PAGE_SEO.get(page["slug"], {})
            meta = {}
            if seo:
                meta = {
                    "_yoast_wpseo_title": seo.get("seo_title", page["title"]),
                    "_yoast_wpseo_metadesc": seo.get("metadesc", "")[:155],
                    "_yoast_wpseo_focuskw": seo.get("focuskw", ""),
                }
            requests.post(
                f"{base}/wp-json/wp/v2/pages",
                json={
                    "title": page["title"],
                    "slug": page["slug"],
                    "content": page["content"].strip(),
                    "status": "publish",
                    "meta": meta,
                },
                auth=auth,
                timeout=30,
            ).raise_for_status()
            created += 1
            log.info("Created page: %s", page["slug"])
        except Exception:
            log.exception("Page setup failed: %s", page["slug"])
    return created


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    ensure_trust_pages()
