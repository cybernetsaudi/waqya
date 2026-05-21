"""
WordPress publisher — posts drafts with hero + inline images and SEO.
"""

from __future__ import annotations

import html as html_module
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
    base_url: str, auth: tuple[str, str], name: str, slug: str = ""
) -> Optional[int]:
    try:
        resp = requests.get(
            f"{base_url}/wp-json/wp/v2/categories",
            params={"search": name, "per_page": 20},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        for cat in resp.json():
            decoded = html_module.unescape(cat["name"])
            if decoded.lower() == name.lower() or (slug and cat.get("slug") == slug):
                return cat["id"]
        payload: dict[str, str] = {"name": name}
        if slug:
            payload["slug"] = slug
        resp = requests.post(
            f"{base_url}/wp-json/wp/v2/categories",
            json=payload,
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


def _waqya_read_html(article: Article) -> str:
    if not article.waqya_read:
        return ""
    bullets = [b.strip() for b in article.waqya_read.split("|") if b.strip()]
    if len(bullets) < 2:
        return ""
    items = "".join(f"<li>{html_module.escape(b)}</li>" for b in bullets[:3])
    return (
        '<aside class="waqya-read" role="note">'
        "<h2>The Waqya read</h2>"
        f"<ul>{items}</ul>"
        "</aside>"
    )


def _editorial_footer_html(article: Article, primary: dict) -> str:
    desk = html_module.escape(primary.get("label", "Waqya"))
    updated = "Published"
    return (
        '<footer class="waqya-editorial-footer">'
        f"<p><strong>Commentary</strong> · {desk} desk · "
        "Facts attributed to sources · "
        '<a href="/editorial-policy/">Editorial policy</a> · '
        '<a href="/corrections/">Corrections</a></p>'
        "</footer>"
    )


def _build_article_html(article: Article, images: Optional[ArticleImages]) -> str:
    paragraphs = [p.strip() for p in article.body.split("\n\n") if p.strip()]
    html_parts: list[str] = []
    read_box = _waqya_read_html(article)
    if read_box:
        html_parts.append(read_box)

    inline_figures: list[str] = []
    if images:
        for img in images.inline:
            if img.wp_url:
                inline_figures.append(_figure_html(img))

    # Insert inline images after paragraphs 2, 4, 6 (spread through article)
    insert_at = [1, 3, 5]
    inline_idx = 0
    for i, para in enumerate(paragraphs):
        html_parts.append(f"<p>{html_module.escape(para)}</p>")
        if i in insert_at and inline_idx < len(inline_figures):
            html_parts.append(inline_figures[inline_idx])
            inline_idx += 1

    while inline_idx < len(inline_figures):
        html_parts.append(inline_figures[inline_idx])
        inline_idx += 1

    html_parts.append(
        f'<p class="source-attribution"><em>Source: <a href="{article.source_url}" '
        f'target="_blank" rel="noopener noreferrer">'
        f"{html_module.escape(article.source_name)}</a></em></p>"
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
    status: str = "draft"
    quality_score: int = 0
    is_breaking: bool = False
    held_reason: str = ""


def publish_draft(
    article: Article,
    *,
    post_status: str | None = None,
    quality_score: int = 0,
    is_breaking: bool = False,
    held_reason: str = "",
) -> Optional[PublishResult]:
    base_url, user, password = _wp_auth()
    auth = (user, password)
    config = _load_config()

    from taxonomy import resolve_primary

    primary = resolve_primary(article.category or article.iptc_topic)
    cat_name = article.wp_category or primary["label"]
    cat_slug = primary["slug"]
    cat_id = _get_or_create_category(base_url, auth, cat_name, cat_slug)

    tag_names = list(article.tags)
    if is_breaking and "Breaking" not in tag_names:
        tag_names.insert(0, "Breaking")
    tag_ids = _get_or_create_tags(base_url, auth, tag_names)

    images = _upload_all_images(base_url, auth, article)
    content_html = _build_article_html(article, images)
    content_html += _editorial_footer_html(article, primary)

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

    if post_status is None:
        post_status = "publish" if config.get("pipeline", {}).get("auto_publish", False) else "draft"

    from html_utils import wp_plain_text

    post_data = {
        "title": wp_plain_text(article.headline),
        "content": content_html,
        "status": post_status,
        "excerpt": wp_plain_text(article.excerpt),
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "meta": {
            "_waqya_quality_score": str(quality_score),
            "_waqya_is_breaking": "1" if is_breaking else "0",
            "_yoast_wpseo_metadesc": wp_plain_text(article.meta_description)[:155],
            "_yoast_wpseo_title": wp_plain_text(article.headline)[:60],
            "_yoast_wpseo_focuskw": focus[:60],
            "_waqya_primary_category": article.category,
            "_waqya_iptc_topic": article.iptc_topic,
            "_waqya_iptc_code": article.iptc_code,
            "_waqya_iptc_label": article.iptc_label,
            "_waqya_dc_subjects": subjects_str,
            "_waqya_coverage": regions_str,
            "_waqya_menu_group": primary.get("menu_group", ""),
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
        log.info("Published %s #%d: %s", post_status, post_id, article.headline)

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
            post_id=post_id,
            edit_url=edit_url,
            title=article.headline,
            post_url=post_url,
            status=post_status,
            quality_score=quality_score,
            is_breaking=is_breaking,
            held_reason=held_reason,
        )
    except Exception:
        log.exception("Failed to publish draft: %s", article.headline)
        return None


def publish_batch(
    articles: list[Article],
    qualities: list | None = None,
) -> list[PublishResult]:
    from quality_gate import QualityResult, resolve_post_status, score_article

    config = _load_config()
    results: list[PublishResult] = []
    for i, article in enumerate(articles):
        q: QualityResult
        if qualities and i < len(qualities):
            q = qualities[i]
        else:
            q = score_article(article, article.source_story, config)
            article.quality_score = q.score
            article.is_breaking = q.is_breaking

        status = resolve_post_status(q, config)
        reason = ""
        if status == "draft" and not q.publish_recommended:
            reason = f"Quality score {q.score}/100 below threshold"

        result = publish_draft(
            article,
            post_status=status,
            quality_score=q.score,
            is_breaking=q.is_breaking,
            held_reason=reason,
        )
        if result:
            results.append(result)
    published = sum(1 for r in results if r.status == "publish")
    log.info("Published %d live, %d held / %d articles", published, len(results) - published, len(articles))
    return results
