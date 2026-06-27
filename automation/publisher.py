"""
WordPress publisher — posts drafts with hero + inline images and SEO.
"""

from __future__ import annotations

import html as html_module
import json
import logging
import os
import re
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

import yaml

from generator import Article
from image_fetcher import ArticleImages, FetchedImage
from wp_client import wp_credentials, wp_get, wp_post

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _gmt_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _initial_update_log(note: str = "First published") -> str:
    return json.dumps([{"at": _gmt_now_iso(), "note": note}], ensure_ascii=False)


def _wp_auth() -> tuple[str, str, str]:
    base, auth = wp_credentials()
    return base, auth[0], auth[1]


def _get_or_create_category(name: str, slug: str = "") -> Optional[int]:
    try:
        resp = wp_get(
            "/wp-json/wp/v2/categories",
            params={"search": name, "per_page": 20},
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
        resp = wp_post("/wp-json/wp/v2/categories", json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()["id"]
    except Exception:
        log.exception("Category lookup/create failed for '%s'", name)
        return None


def _get_or_create_tags(tag_names: list[str]) -> list[int]:
    tag_ids: list[int] = []
    for name in tag_names:
        try:
            resp = wp_get(
                "/wp-json/wp/v2/tags",
                params={"search": name, "per_page": 5},
                timeout=15,
            )
            resp.raise_for_status()
            found = None
            for tag in resp.json():
                if tag["name"].lower() == name.lower():
                    found = tag["id"]
                    break
            if not found:
                resp = wp_post("/wp-json/wp/v2/tags", json={"name": name}, timeout=15)
                resp.raise_for_status()
                found = resp.json()["id"]
            tag_ids.append(found)
        except Exception:
            log.exception("Tag lookup/create failed for '%s'", name)
    return tag_ids


def upload_media(image: FetchedImage, title: str) -> Optional[FetchedImage]:
    try:
        resp = wp_post(
            "/wp-json/wp/v2/media",
            data=image.data,
            headers={
                "Content-Disposition": f'attachment; filename="{image.filename}"',
                "Content-Type": image.mime_type,
            },
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
        image.wp_media_id = data["id"]
        image.wp_url = data.get("source_url") or data.get("guid", {}).get("rendered")
        update = {"title": title, "alt_text": image.alt_text}
        if image.credit:
            update["caption"] = image.credit
        wp_post(
            f"/wp-json/wp/v2/media/{image.wp_media_id}",
            json=update,
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


def _block_to_html(block: str) -> str:
    block = block.strip()
    if not block:
        return ""

    if block.startswith("## "):
        lines = block.split("\n", 1)
        title = html_module.escape(_normalize_text(lines[0][3:]))
        html = f"<h2>{title}</h2>"
        if len(lines) > 1 and lines[1].strip():
            html += "\n\n" + _block_to_html(lines[1].strip())
        return html

    if block.startswith("### "):
        lines = block.split("\n", 1)
        title = html_module.escape(_normalize_text(lines[0][4:]))
        html = f"<h3>{title}</h3>"
        if len(lines) > 1 and lines[1].strip():
            html += "\n\n" + _paragraphs_to_html(lines[1].strip())
        return html

    return _paragraphs_to_html(block)


def _normalize_text(text: str) -> str:
    return html_module.unescape(text.strip())


def _paragraphs_to_html(text: str) -> str:
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not parts:
        return ""
    return "\n\n".join(
        _block_to_html(p) if p.startswith("#") else f"<p>{html_module.escape(_normalize_text(p))}</p>"
        for p in parts
    )


def _build_article_html(article: Article, images: Optional[ArticleImages]) -> str:
    blocks = [p.strip() for p in article.body.split("\n\n") if p.strip()]
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
    para_idx = 0
    for block in blocks:
        html_parts.append(_block_to_html(block))
        if block.startswith("#"):
            continue
        if para_idx in insert_at and inline_idx < len(inline_figures):
            html_parts.append(inline_figures[inline_idx])
            inline_idx += 1
        para_idx += 1
    while inline_idx < len(inline_figures):
        html_parts.append(inline_figures[inline_idx])
        inline_idx += 1

    html_parts.append(
        f'<p class="source-attribution"><em>Source: <a href="{article.source_url}" '
        f'target="_blank" rel="noopener noreferrer">'
        f"{html_module.escape(article.source_name)}</a></em></p>"
    )
    return "\n\n".join(html_parts)


def _upload_all_images(article: Article) -> Optional[ArticleImages]:
    images = article.images
    if not images:
        return None

    if images.featured:
        upload_media(images.featured, article.headline)
    for i, img in enumerate(images.inline):
        upload_media(img, f"{article.headline} — image {i + 2}")
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
    quality_notes: str = ""
    llm_body: str = ""
    llm_headline: str = ""


def publish_draft(
    article: Article,
    *,
    post_status: str | None = None,
    quality_score: int = 0,
    is_breaking: bool = False,
    held_reason: str = "",
    quality_notes: str = "",
) -> Optional[PublishResult]:
    base_url, _, _ = _wp_auth()
    config = _load_config()

    from taxonomy import resolve_primary

    primary = resolve_primary(article.category or article.iptc_topic)
    cat_name = article.wp_category or primary["label"]
    cat_slug = primary["slug"]
    cat_id = _get_or_create_category(cat_name, cat_slug)

    tag_names = list(article.tags)
    if is_breaking and "Breaking" not in tag_names:
        tag_names.insert(0, "Breaking")
    otr_cfg = config.get("on_the_record", {})
    if article.article_format == "on_the_record":
        otr_tag = otr_cfg.get("tag", "On The Record")
        if otr_tag not in tag_names:
            tag_names.insert(0, otr_tag)
    tag_ids = _get_or_create_tags(tag_names)

    from html_utils import wp_plain_text
    from yoast_seo import (
        build_image_alt,
        build_meta_description,
        build_post_slug,
        build_seo_title,
        suggest_focus_keyword,
    )

    focus = article.focus_keyword or suggest_focus_keyword(
        headline=article.headline,
        primary_key=article.category,
        topic_tags=article.tags,
        tags=article.tags,
        subjects=article.subjects,
    )
    seo_title = article.seo_title or build_seo_title(focus, article.headline)
    metadesc = build_meta_description(focus, article.meta_description, article.headline)
    post_slug = build_post_slug(focus, article.headline)

    if article.images:
        if article.images.featured:
            article.images.featured.alt_text = build_image_alt(focus, article.headline, "featured")
        for i, img in enumerate(article.images.inline):
            img.alt_text = build_image_alt(focus, article.headline, f"inline {i + 1}")

    images = _upload_all_images(article)
    content_html = _build_article_html(article, images)
    content_html += _editorial_footer_html(article, primary)

    from content_seo import optimize_post_html

    content_html = optimize_post_html(content_html, focus, article.headline)

    featured_media_id = None
    featured_url = None
    if images and images.featured and images.featured.wp_media_id:
        featured_media_id = images.featured.wp_media_id
        featured_url = images.featured.wp_url

    subjects_str = ", ".join(article.subjects) if article.subjects else ""
    regions_str = ", ".join(article.regions) if article.regions else ""

    if post_status is None:
        post_status = "publish" if config.get("pipeline", {}).get("auto_publish", False) else "draft"

    from datetime_utils import source_date_gmt

    post_data = {
        "title": wp_plain_text(article.headline),
        "slug": post_slug,
        "content": content_html,
        "status": post_status,
        "excerpt": wp_plain_text(article.excerpt),
        "categories": [cat_id] if cat_id else [],
        "tags": tag_ids,
        "meta": {
            "_waqya_quality_score": str(quality_score),
            "_waqya_is_breaking": "1" if is_breaking else "0",
            "_waqya_developing": "1" if is_breaking else "0",
            "_yoast_wpseo_metadesc": metadesc,
            "_yoast_wpseo_title": seo_title,
            "_yoast_wpseo_focuskw": focus[:60],
            "_waqya_primary_category": article.category,
            "_waqya_iptc_topic": article.iptc_topic,
            "_waqya_iptc_code": article.iptc_code,
            "_waqya_iptc_label": article.iptc_label,
            "_waqya_dc_subjects": subjects_str,
            "_waqya_coverage": regions_str,
            "_waqya_menu_group": primary.get("menu_group", ""),
            "_waqya_source_url": article.source_url,
        },
    }
    if article.llm_body_provider:
        post_data["meta"]["_waqya_llm_body_provider"] = article.llm_body_provider
        post_data["meta"]["_waqya_llm_body_model"] = article.llm_body_model or ""
    if article.llm_headline_provider:
        post_data["meta"]["_waqya_llm_headline_provider"] = article.llm_headline_provider
        post_data["meta"]["_waqya_llm_headline_model"] = article.llm_headline_model or ""
    if quality_notes:
        post_data["meta"]["_waqya_quality_notes"] = quality_notes[:500]
    if article.source_story:
        published_gmt = source_date_gmt(article.source_story.get("published"))
        if published_gmt:
            post_data["date_gmt"] = published_gmt
    if article.article_format == "on_the_record":
        post_data["meta"]["_waqya_format"] = "on_the_record"
        if article.interview_tone:
            post_data["meta"]["_waqya_interview_tone"] = article.interview_tone[:32]
    if is_breaking:
        note = (
            "Interview review published"
            if article.article_format == "on_the_record"
            else "Story first published"
        )
        post_data["meta"]["_waqya_update_log"] = _initial_update_log(note)
    if article.headline_ar:
        post_data["meta"]["_waqya_headline_ar"] = article.headline_ar[:120]
    if article.headline_ur:
        post_data["meta"]["_waqya_headline_ur"] = article.headline_ur[:120]
    if featured_media_id:
        post_data["featured_media"] = featured_media_id

    try:
        resp = wp_post("/wp-json/wp/v2/posts", json=post_data, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        post_id = data["id"]
        post_url = data.get("link", f"{base_url}/?p={post_id}")
        edit_url = f"{base_url}/wp-admin/post.php?post={post_id}&action=edit"
        log.info("Published %s #%d: %s", post_status, post_id, article.headline)

        if images:
            from image_dedup import mark_article_images

            mark_article_images(images, article.headline)

        from seo import optimize_published_post

        optimize_published_post(
            post_id=post_id,
            headline=article.headline,
            meta_description=metadesc,
            tags=article.tags,
            content_html=content_html,
            post_url=post_url,
            featured_image_url=featured_url,
            category_ids=[cat_id] if cat_id else [],
            focus_keyword=focus,
            seo_title=seo_title,
            primary_key=article.category,
        )

        llm_body = ""
        if article.llm_body_provider:
            llm_body = f"{article.llm_body_provider}/{article.llm_body_model or '?'}"
        llm_headline = ""
        if article.llm_headline_provider:
            llm_headline = f"{article.llm_headline_provider}/{article.llm_headline_model or '?'}"

        return PublishResult(
            post_id=post_id,
            edit_url=edit_url,
            title=article.headline,
            post_url=post_url,
            status=post_status,
            quality_score=quality_score,
            is_breaking=is_breaking,
            held_reason=held_reason,
            quality_notes=quality_notes,
            llm_body=llm_body,
            llm_headline=llm_headline,
        )
    except Exception:
        log.exception("Failed to publish draft: %s", article.headline)
        return None


def _clear_featured_home() -> None:
    try:
        resp = wp_get(
            "/wp-json/wp/v2/posts",
            params={
                "per_page": 5,
                "status": "publish",
                "meta_key": "_waqya_featured_home",
                "meta_value": "1",
                "_fields": "id",
            },
            timeout=15,
        )
        resp.raise_for_status()
        for post in resp.json():
            wp_post(
                f"/wp-json/wp/v2/posts/{post['id']}",
                json={"meta": {"_waqya_featured_home": ""}},
                timeout=15,
            )
    except Exception:
        log.exception("Could not clear previous featured-home flag")


def _set_featured_home(post_id: int) -> None:
    try:
        _clear_featured_home()
        wp_post(
            f"/wp-json/wp/v2/posts/{post_id}",
            json={"meta": {"_waqya_featured_home": "1"}},
            timeout=15,
        )
        log.info("Editor's pick set on post #%d", post_id)
    except Exception:
        log.exception("Could not set featured-home on #%d", post_id)


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
        notes_text = "; ".join(q.notes[:6])
        reason = ""
        if status == "draft":
            if not q.publish_recommended:
                reason = f"Score {q.score}/100 below threshold (need {config.get('pipeline', {}).get('require_min_quality_score', 78)})"
            else:
                reason = f"Held at score {q.score}/100"
            negatives = [n for n in q.notes if any(
                k in n.lower()
                for k in ("too short", "tabloid", "resembles", "missing", "boilerplate", "disclaimer")
            )]
            if negatives:
                reason = f"{reason} — {'; '.join(negatives[:3])}"

        result = publish_draft(
            article,
            post_status=status,
            quality_score=q.score,
            is_breaking=q.is_breaking,
            held_reason=reason,
            quality_notes=notes_text,
        )
        if result:
            results.append(result)
    published = sum(1 for r in results if r.status == "publish")
    log.info("Published %d live, %d held / %d articles", published, len(results) - published, len(articles))

    live = [r for r in results if r.status == "publish" and r.post_id]
    if live:
        best = max(live, key=lambda r: (r.quality_score or 0, r.is_breaking))
        _set_featured_home(best.post_id)

    return results
