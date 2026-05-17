#!/usr/bin/env python3
"""
Reclassify existing WordPress posts to IPTC Media Topics categories + tags.

Usage:
  cd automation && python recategorize_posts.py
  python recategorize_posts.py --status publish
"""

from __future__ import annotations

import argparse
import html
import logging
import os
import re
import sys
import time

import requests
from dotenv import load_dotenv
from openai import OpenAI

from taxonomy import (
    normalize_tags,
    primary_catalog_for_prompt,
    resolve_primary,
    suggest_primary_from_story,
)

log = logging.getLogger("recategorize")

CLASSIFY_PROMPT = """You classify news articles using the Waqya taxonomy (IPTC-aligned).

ALLOWED PRIMARY category keys (pick exactly one):
{catalog}

Given the article title and excerpt, respond with ONLY these lines:
PRIMARY: <key from list>
TAGS: <8-12 comma-separated tags>
REGION_TAGS: <0-3 regions>
TOPIC_TAGS: <0-4 themes e.g. War, Immigration, Religion>
SUBJECTS: <4-8 subject keywords>
"""


def _auth():
    base = os.environ["WP_URL"].rstrip("/")
    return base, (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])


def _strip_html(raw: str) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return re.sub(r"\s+", " ", text).strip()


def _load_category_ids(base: str, auth: tuple[str, str]) -> dict[str, int]:
    """Map wp_category display name (lower) -> id."""
    import html as html_module

    name_to_id: dict[str, int] = {}
    page = 1
    while True:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/categories",
            params={"per_page": 100, "page": page},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        for cat in batch:
            name = html_module.unescape(cat["name"]).strip()
            name_to_id[name.lower()] = cat["id"]
        page += 1
        if len(batch) < 100:
            break
    return name_to_id


def _get_tag_ids(base: str, auth: tuple[str, str], names: list[str]) -> list[int]:
    ids: list[int] = []
    for name in names:
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/tags",
                params={"search": name, "per_page": 5},
                auth=auth,
                timeout=15,
            )
            resp.raise_for_status()
            found = None
            for tag in resp.json():
                if tag["name"].lower() == name.lower():
                    found = tag["id"]
                    break
            if not found:
                resp = requests.post(
                    f"{base}/wp-json/wp/v2/tags",
                    json={"name": name},
                    auth=auth,
                    timeout=15,
                )
                resp.raise_for_status()
                found = resp.json()["id"]
            ids.append(found)
        except Exception:
            log.exception("Tag failed: %s", name)
    return ids


def _parse_classification(raw: str) -> dict:
    fields = {
        "primary": "",
        "iptc_topic": "",
        "tags": [],
        "subjects": "",
        "regions": "",
        "region_tags": "",
        "topic_tags": "",
    }
    for line in raw.splitlines():
        line = line.strip()
        u = line.upper()
        if u.startswith("PRIMARY:"):
            fields["primary"] = line.split(":", 1)[1].strip()
        elif u.startswith("IPTC_TOPIC:"):
            fields["iptc_topic"] = line.split(":", 1)[1].strip()
        elif u.startswith("REGION_TAGS:"):
            fields["region_tags"] = line.split(":", 1)[1].strip()
        elif u.startswith("TOPIC_TAGS:"):
            fields["topic_tags"] = line.split(":", 1)[1].strip()
        elif u.startswith("TAGS:"):
            fields["tags"] = [t.strip() for t in line.split(":", 1)[1].split(",") if t.strip()]
        elif u.startswith("SUBJECTS:"):
            fields["subjects"] = line.split(":", 1)[1].strip()
        elif u.startswith("REGIONS:"):
            fields["regions"] = line.split(":", 1)[1].strip()
    return fields


def classify_post(client: OpenAI, title: str, excerpt: str) -> dict:
    prompt = CLASSIFY_PROMPT.format(catalog=primary_catalog_for_prompt())
    user = f"TITLE: {title}\n\nEXCERPT: {excerpt[:2000]}"
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=250,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
    )
    return _parse_classification(resp.choices[0].message.content.strip())


def recategorize_post(
    post: dict,
    base: str,
    auth: tuple[str, str],
    cat_ids: dict[str, int],
    client: OpenAI,
) -> bool:
    post_id = post["id"]
    title = _strip_html(post["title"]["rendered"])
    raw = post.get("content", {}).get("rendered", "")
    excerpt = _strip_html(post.get("excerpt", {}).get("rendered", "") or raw[:800])

    parsed = classify_post(client, title, excerpt)
    suggested = suggest_primary_from_story(title, excerpt)
    primary = resolve_primary(
        parsed.get("primary") or parsed.get("iptc_topic") or suggested,
        title=title,
        summary=excerpt,
    )
    if primary["primary_key"] == "current-affairs" and suggested != "current-affairs":
        alt = resolve_primary(suggested, title=title, summary=excerpt)
        if alt["primary_key"] != "current-affairs":
            primary = alt
    regions = [
        r.strip()
        for r in (parsed.get("region_tags") or parsed.get("regions", "")).split(",")
        if r.strip()
    ]
    topic_tags = [t.strip() for t in parsed.get("topic_tags", "").split(",") if t.strip()]
    subjects = [s.strip() for s in parsed["subjects"].split(",") if s.strip()]
    tags = normalize_tags(parsed["tags"], regions=regions, topic_tags=topic_tags, max_tags=15)
    if primary["label"] not in tags:
        tags.insert(0, primary["label"])

    cat_id = cat_ids.get(primary["wp_category"].lower())
    if not cat_id:
        log.error("No WP category id for %s", primary["wp_category"])
        return False

    tag_ids = _get_tag_ids(base, auth, tags)
    subjects_str = ", ".join(subjects)
    regions_str = ", ".join(regions)

    resp = requests.post(
        f"{base}/wp-json/wp/v2/posts/{post_id}",
        json={
            "categories": [cat_id],
            "tags": tag_ids,
            "meta": {
                "_waqya_primary_category": primary["primary_key"],
                "_waqya_iptc_topic": primary["primary_key"],
                "_waqya_iptc_code": primary["iptc_code"],
                "_waqya_iptc_label": primary["label"],
                "_waqya_dc_subjects": subjects_str,
                "_waqya_coverage": regions_str,
                "_waqya_menu_group": primary.get("menu_group", ""),
            },
        },
        auth=auth,
        timeout=30,
    )
    resp.raise_for_status()
    log.info(
        "  #%d → %s | %s",
        post_id,
        primary["wp_category"],
        title[:50],
    )
    return True


def main() -> int:
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser()
    parser.add_argument("--status", default="publish,draft")
    args = parser.parse_args()

    from sync_categories import sync_all

    log.info("Ensuring IPTC categories exist…")
    sync_all()

    base, auth = _auth()
    cat_ids = _load_category_ids(base, auth)
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    posts: list[dict] = []
    for status in args.status.split(","):
        r = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={"status": status.strip(), "per_page": 100},
            auth=auth,
            timeout=15,
        )
        r.raise_for_status()
        posts.extend(r.json())

    log.info("Reclassifying %d posts…\n", len(posts))
    ok = 0
    for i, post in enumerate(posts):
        if i > 0:
            time.sleep(2)
        try:
            if recategorize_post(post, base, auth, cat_ids, client):
                ok += 1
        except Exception:
            log.exception("Failed #%s", post.get("id"))

    log.info("\nDone: %d / %d posts recategorized.", ok, len(posts))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
