"""
WordPress publisher — posts drafts with hero + inline images and SEO.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Optional

import requests
import yaml

from generator import Article
from image_fetcher import ArticleImages, FetchedImage

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _wp_auth() -> tuple[str, str, str]:
    url = os.environ["WP_URL"].rstrip("/")
    return url, os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"]


def _get_or_create_category(
    base_url: str, auth: tuple[str, str], name: str
) -> Optional[int]:
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


def upload_media(
    base_url: str,
    auth: tuple[str, str],
    image: FetchedImage,
    title: str,
) -> Optional[FetchedImage]:
    headers = {
        "Content-Disposition": f'attachment; filename="{image.filename}"',
        "Content-Type": image.mime_type,
    }
    try:
        resp = requests.post(
            f"{base_url}/wp-json/wp/v2/media",
            headers=headers,
            data=image.data,
            auth=auth,
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        image.wp_media_id = data["id"]
        image.wp_url = data.get("source_url") or data.get("guid", {}).get("rendered")
        update = {"title": title, "alt_text": image.alt_text}
        if image.credit:
            update["caption"] = image.credit
        requests.post(
            f"{base_url}/wp-json/wp/v2/media/{image.wp_media_id}",
            json=update,
            auth=auth,
            timeout=15,
        )
        return image
    except Exception:
        log.exception("Media upload failed: %s", title)
        return None


def _figure_html(img: FetchedImage) -> str:
    if not img.wp_url:
        return ""
    cap = f"<figcaption>{img.credit}</figcaption>" if img.credit else ""
    cls = f' class="wp-image-{img.wp_media_id}"' if img.wp_media_id else ""
    return (
        f'<figure class="wp-block-image size-large">'
        f'<img src="{img.wp_url}" alt="{img.alt_text}"{cls} loading="lazy"/>'
        f"{cap}</figure>"
    )


def _build_article_html(article: Article, images: Optional[ArticleImages]) -> str:
    paragraphs = [p.strip() for p in article.body.split("\n\n") if p.strip()]
    html_parts: list[str] = []

    inline_figures: list[str] = []
    if images:
        for img in images.inline:
            if img.wp_url:
                inline_figures.append(_figure_html(img))

    # Insert inline images after paragraphs 2, 4, 6 (spread through article)
    insert_at = [1, 3, 5]
    inline_idx = 0
    for i, para in enumerate(paragraphs):
        html_parts.append(f"<p>{para}</p>")
        if i in insert_at and inline_idx < len(inline_figures):
            html_parts.append(inline_figures[inline_idx])
            inline_idx += 1

    while inline_idx < len(inline_figures):
        html_parts.append(inline_figures[inline_idx])
        inline_idx += 1

    html_parts.append(
        f'<p><em>Source: <a href="{article.source_url}" '
        f'target="_blank" rel="noopener noreferrer">'
        f"{article.source_name}</a></em></p>"
    )
    return "\n\n".join(html_parts)


def _upload_all_images(
    base_url: str, auth: tuple[str, str], article: Article
) -> Optional[ArticleImages]:
    images = article.images
    if not images:
        return None

    if images.featured:
        upload_media(base_url, auth, images.featured, article.headline)
    for i, img in enumerate(images.inline):
        upload_media(base_url, auth, img, f"{article.headline} — image {i + 2}")
    return images


@dataclass
class PublishResult:
    post_id: int
    edit_url: str
    title: str
    post_url: str


def publish_draft(article: Article) -> Optional[PublishResult]:
    base_url, user, password = _wp_auth()
    auth = (user, password)
    config = _load_config()

    category_name = article.wp_category or config.get("default_category", "Society")
    cat_id = _get_or_create_category(base_url, auth, category_name)
    tag_ids = _get_or_create_tags(base_url, auth, article.tags)

    images = _upload_all_images(base_url, auth, article)
    content_html = _build_article_html(article, images)

    featured_media_id = None
    featured_url = None
    if images and images.featured and images.featured.wp_media_id:
        featured_media_id = images.featured.wp_media_id
        featured_url = images.featured.wp_url

    focus = (
        article.subjects[0]
        if article.subjects
        else (article.tags[0] if article.tags else article.headline.split()[0])
    )
    subjects_str = ", ".join(article.subjects) if article.subjects else ""
    regions_str = ", ".join(article.regions) if article.regions else ""

    post_data = {
        "title": article.headline,
        "content": content_html,
        "status": "draft",
        "excerpt": article.excerpt,
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "meta": {
            "_yoast_wpseo_metadesc": article.meta_description,
            "_yoast_wpseo_title": article.headline[:60],
            "_yoast_wpseo_focuskw": focus[:60],
            "_waqya_iptc_topic": article.iptc_topic,
            "_waqya_iptc_code": article.iptc_code,
            "_waqya_iptc_label": article.iptc_label,
            "_waqya_dc_subjects": subjects_str,
            "_waqya_coverage": regions_str,
        },
    }
    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    try:
        resp = requests.post(
            f"{base_url}/wp-json/wp/v2/posts",
            json=post_data,
            auth=auth,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        post_id = data["id"]
        post_url = data.get("link", f"{base_url}/?p={post_id}")
        edit_url = f"{base_url}/wp-admin/post.php?post={post_id}&action=edit"
        log.info("Published draft #%d: %s", post_id, article.headline)

        from seo import optimize_published_post

        optimize_published_post(
            post_id=post_id,
            headline=article.headline,
            meta_description=article.meta_description,
            tags=article.tags,
            content_html=content_html,
            post_url=post_url,
            featured_image_url=featured_url,
            category_ids=[cat_id] if cat_id else [],
        )

        return PublishResult(
            post_id=post_id, edit_url=edit_url, title=article.headline, post_url=post_url
        )
    except Exception:
        log.exception("Failed to publish draft: %s", article.headline)
        return None


def publish_batch(articles: list[Article]) -> list[PublishResult]:
    results: list[PublishResult] = []
    for article in articles:
        result = publish_draft(article)
        if result:
            results.append(result)
    log.info("Published %d / %d drafts", len(results), len(articles))
    return results
