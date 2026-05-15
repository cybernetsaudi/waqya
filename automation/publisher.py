"""
WordPress publisher — posts generated articles as drafts
via the WordPress REST API using Application Passwords.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

import requests
import yaml

from generator import Article

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _wp_auth() -> tuple[str, str, str]:
    """Return (base_url, user, app_password) from environment."""
    url = os.environ["WP_URL"].rstrip("/")
    user = os.environ["WP_USER"]
    password = os.environ["WP_APP_PASSWORD"]
    return url, user, password


def _get_or_create_category(
    base_url: str, auth: tuple[str, str], name: str
) -> Optional[int]:
    """Resolve a category name to its WP ID, creating it if needed."""
    try:
        resp = requests.get(
            f"{base_url}/wp-json/wp/v2/categories",
            params={"search": name, "per_page": 5},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        for cat in resp.json():
            if cat["name"].lower() == name.lower():
                return cat["id"]

        # Category doesn't exist — create it
        resp = requests.post(
            f"{base_url}/wp-json/wp/v2/categories",
            json={"name": name},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["id"]
    except Exception:
        log.exception("Category lookup/create failed for '%s'", name)
        return None


def _get_or_create_tags(
    base_url: str, auth: tuple[str, str], tag_names: list[str]
) -> list[int]:
    """Resolve tag names to WP IDs, creating any that don't exist."""
    tag_ids: list[int] = []
    for name in tag_names:
        try:
            resp = requests.get(
                f"{base_url}/wp-json/wp/v2/tags",
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
                    f"{base_url}/wp-json/wp/v2/tags",
                    json={"name": name},
                    auth=auth,
                    timeout=15,
                )
                resp.raise_for_status()
                found = resp.json()["id"]

            tag_ids.append(found)
        except Exception:
            log.exception("Tag lookup/create failed for '%s'", name)
    return tag_ids


def _build_article_html(article: Article) -> str:
    """Convert article body text to basic HTML with source attribution."""
    paragraphs = [p.strip() for p in article.body.split("\n\n") if p.strip()]
    html_parts = [f"<p>{p}</p>" for p in paragraphs]

    # Source attribution footer
    html_parts.append(
        f'<p><em>Source: <a href="{article.source_url}" '
        f'target="_blank" rel="noopener noreferrer">'
        f"{article.source_name}</a></em></p>"
    )
    return "\n\n".join(html_parts)


@dataclass
class PublishResult:
    post_id: int
    edit_url: str
    title: str


def publish_draft(article: Article) -> Optional[PublishResult]:
    """Post a single article as a WordPress draft. Returns the post ID or None."""
    base_url, user, password = _wp_auth()
    auth = (user, password)
    config = _load_config()

    category_map = config.get("categories", {})
    category_name = category_map.get(article.category, config.get("default_category", "World"))
    cat_id = _get_or_create_category(base_url, auth, category_name)
    tag_ids = _get_or_create_tags(base_url, auth, article.tags)

    content_html = _build_article_html(article)

    post_data = {
        "title": article.headline,
        "content": content_html,
        "status": "draft",
        "excerpt": article.excerpt,
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "meta": {
            "_yoast_wpseo_metadesc": article.meta_description,
        },
    }

    try:
        resp = requests.post(
            f"{base_url}/wp-json/wp/v2/posts",
            json=post_data,
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        post_id = data["id"]
        edit_url = f"{base_url}/wp-admin/post.php?post={post_id}&action=edit"
        log.info("Published draft #%d: %s", post_id, article.headline)
        return PublishResult(post_id=post_id, edit_url=edit_url, title=article.headline)
    except Exception:
        log.exception("Failed to publish draft: %s", article.headline)
        return None


def publish_batch(articles: list[Article]) -> list[PublishResult]:
    """Publish a batch of articles as WordPress drafts."""
    results: list[PublishResult] = []
    for article in articles:
        result = publish_draft(article)
        if result:
            results.append(result)
    log.info("Published %d / %d drafts", len(results), len(articles))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("Publisher module loaded. Use publish_draft() or publish_batch() programmatically.")
    print("Run pipeline.py for the full workflow.")
