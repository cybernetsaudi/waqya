"""
Track images already used on Waqya so the same photo is not reused across posts.

Persisted in SQLite (uploaded with seen.db via GitHub Actions cache).
"""

from __future__ import annotations

import hashlib
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import requests

log = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent / "images.db"

_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
_PEXELS_ID_RE = re.compile(r"pexels\.com/photo/[^/\"]+-(\d+)", re.I)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS used_images (
            fingerprint   TEXT PRIMARY KEY,
            pexels_id     TEXT,
            seen_at       REAL,
            context       TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_used_images_pexels ON used_images (pexels_id)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS used_source_urls (
            url_fp TEXT PRIMARY KEY,
            url    TEXT,
            seen_at REAL
        )
        """
    )
    conn.commit()
    return conn


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


def normalize_image_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    try:
        p = urlparse(url.split("?")[0])
        if not p.netloc:
            return url.lower()
        path = p.path.rstrip("/") or "/"
        return f"{p.scheme or 'https'}://{p.netloc.lower()}{path}"
    except Exception:
        return url.lower().split("?")[0]


def source_url_fingerprint(url: str) -> str:
    norm = normalize_image_url(url)
    if not norm:
        return ""
    return hashlib.sha256(norm.encode()).hexdigest()[:24]


def is_source_url_used(url: str) -> bool:
    fp = source_url_fingerprint(url)
    if not fp:
        return False
    conn = _connect()
    row = conn.execute("SELECT 1 FROM used_source_urls WHERE url_fp = ?", (fp,)).fetchone()
    conn.close()
    return row is not None


def mark_source_url_used(url: str, context: str = "") -> bool:
    """Register URL; returns True if newly added."""
    norm = normalize_image_url(url)
    fp = source_url_fingerprint(norm)
    if not fp:
        return False
    conn = _connect()
    cur = conn.execute(
        "INSERT OR IGNORE INTO used_source_urls (url_fp, url, seen_at) VALUES (?, ?, ?)",
        (fp, norm, time.time()),
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def is_image_used(data: bytes | None = None, pexels_id: int | str | None = None) -> bool:
    conn = _connect()

    if pexels_id is not None:
        pid = str(pexels_id)
        row = conn.execute(
            "SELECT 1 FROM used_images WHERE pexels_id = ?", (pid,)
        ).fetchone()
        if row is not None:
            conn.close()
            return True

    if data:
        fp = fingerprint(data)
        row = conn.execute(
            "SELECT 1 FROM used_images WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if row is not None:
            conn.close()
            return True

    conn.close()
    return False


def mark_image_used(
    data: bytes,
    pexels_id: int | str | None = None,
    context: str = "",
    source_url: str = "",
) -> None:
    fp = fingerprint(data)
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO used_images (fingerprint, pexels_id, seen_at, context) "
        "VALUES (?, ?, ?, ?)",
        (fp, str(pexels_id) if pexels_id is not None else None, time.time(), context[:200]),
    )
    conn.commit()
    conn.close()
    if source_url:
        mark_source_url_used(source_url, context)


def mark_article_images(images, headline: str = "") -> None:
    if not images:
        return
    if images.featured:
        mark_image_used(
            images.featured.data,
            getattr(images.featured, "pexels_id", None),
            context=headline,
            source_url=getattr(images.featured, "wp_url", "") or "",
        )
    for img in images.inline or []:
        mark_image_used(
            img.data,
            getattr(img, "pexels_id", None),
            context=headline,
            source_url=getattr(img, "wp_url", "") or "",
        )


def count_used() -> int:
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM used_images").fetchone()[0]
    conn.close()
    return int(n)


def pexels_id_from_caption(caption_html: str) -> str | None:
    m = _PEXELS_ID_RE.search(caption_html or "")
    return m.group(1) if m else None


def extract_image_urls_from_html(html: str) -> list[str]:
    urls: list[str] = []
    for src in _IMG_SRC_RE.findall(html or ""):
        if "/wp-content/" in src or "pexels.com" in src:
            urls.append(src)
    return urls


def _register_pexels_id(pid: str, context: str = "wp-sync") -> bool:
    if is_image_used(pexels_id=pid):
        return False
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO used_images (fingerprint, pexels_id, seen_at, context) "
        "VALUES (?, ?, ?, ?)",
        (f"pexels-{pid}", pid, time.time(), context[:200]),
    )
    conn.commit()
    conn.close()
    return True


def sync_used_from_published_posts(max_pages: int = 10) -> dict[str, int]:
    """
    Register images already on live posts (featured + inline) into images.db.
    Uses post pagination + batched media lookups (avoids scanning entire media library).
    """
    import os

    base = os.environ.get("WP_URL", "").rstrip("/")
    user = os.environ.get("WP_USER", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    stats = {"posts": 0, "pexels_ids": 0, "source_urls": 0, "media_batches": 0}
    if not base or not user or not password:
        return stats

    auth = (user, password)
    featured_ids: set[int] = set()
    inline_urls: set[str] = set()

    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/posts",
                params={
                    "per_page": 100,
                    "page": page,
                    "status": "publish",
                    "_fields": "id,featured_media,content",
                },
                auth=auth,
                timeout=45,
            )
            if resp.status_code == 400:
                break
            resp.raise_for_status()
            batch = resp.json()
        except Exception:
            log.exception("Post sync page %d failed", page)
            break
        if not batch:
            break
        stats["posts"] += len(batch)
        for post in batch:
            fm = int(post.get("featured_media") or 0)
            if fm:
                featured_ids.add(fm)
            html = (post.get("content") or {}).get("rendered", "") or ""
            for u in extract_image_urls_from_html(html):
                inline_urls.add(u)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break

    id_list = sorted(featured_ids)
    for i in range(0, len(id_list), 100):
        chunk = id_list[i : i + 100]
        if not chunk:
            continue
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/media",
                params={"include": ",".join(str(x) for x in chunk), "per_page": 100, "_fields": "id,source_url,caption"},
                auth=auth,
                timeout=45,
            )
            resp.raise_for_status()
            stats["media_batches"] += 1
            for item in resp.json():
                src = item.get("source_url", "")
                if src and mark_source_url_used(src, "featured"):
                    stats["source_urls"] += 1
                cap = (item.get("caption") or {}).get("rendered", "")
                pid = pexels_id_from_caption(cap)
                if pid and _register_pexels_id(pid):
                    stats["pexels_ids"] += 1
        except Exception:
            log.exception("Media batch sync failed for %d ids", len(chunk))

    for url in inline_urls:
        if mark_source_url_used(url, "inline"):
            stats["source_urls"] += 1
        pid = pexels_id_from_caption(url)
        if pid and _register_pexels_id(pid):
            stats["pexels_ids"] += 1

    return stats


def sync_used_from_wordpress(max_pages: int = 5) -> int:
    """Legacy: scan media library captions for Pexels IDs (small page window)."""
    import os

    base = os.environ.get("WP_URL", "").rstrip("/")
    user = os.environ.get("WP_USER", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    if not base or not user or not password:
        return 0

    synced = 0
    auth = (user, password)
    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(
                f"{base}/wp-json/wp/v2/media",
                params={"per_page": 100, "page": page, "_fields": "id,caption,source_url"},
                auth=auth,
                timeout=30,
            )
            if resp.status_code != 200:
                break
            batch = resp.json()
        except Exception:
            log.exception("Media library sync page %d failed", page)
            break
        if not batch:
            break
        for item in batch:
            cap = (item.get("caption") or {}).get("rendered", "")
            pid = pexels_id_from_caption(cap)
            if pid and _register_pexels_id(pid):
                synced += 1
            src = item.get("source_url", "")
            if src:
                mark_source_url_used(src)
        total_pages = int(resp.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages:
            break
    return synced


def load_exclude_pexels() -> set[str]:
    conn = _connect()
    rows = conn.execute(
        "SELECT pexels_id FROM used_images WHERE pexels_id IS NOT NULL"
    ).fetchall()
    conn.close()
    return {str(r[0]) for r in rows if r[0]}


@dataclass
class ImageBatchContext:
    """Shared reserve pool for one pipeline run (no duplicate images in batch)."""

    exclude_pexels: set[str] = field(default_factory=set)
    session_fingerprints: set[str] = field(default_factory=set)

    def reserve(self, img) -> None:
        fp = fingerprint(img.data)
        self.session_fingerprints.add(fp)
        if getattr(img, "pexels_id", None) is not None:
            self.exclude_pexels.add(str(img.pexels_id))

    def is_session_duplicate(self, data: bytes) -> bool:
        return fingerprint(data) in self.session_fingerprints


def prepare_pipeline_image_pool(config: dict | None = None) -> ImageBatchContext:
    """
    Sync live site images into images.db, return batch context for fetch_article_images.
    Call once per pipeline run before attach_images.
    """
    if config is None:
        import yaml

        with open(Path(__file__).parent / "config.yaml") as f:
            config = yaml.safe_load(f)

    img_cfg = config.get("images", {})
    ctx = ImageBatchContext(exclude_pexels=load_exclude_pexels())

    if not img_cfg.get("enabled", True):
        return ctx

    if img_cfg.get("sync_from_site", True):
        stats = sync_used_from_published_posts(
            max_pages=int(img_cfg.get("sync_max_post_pages", 10))
        )
        log.info(
            "Image pool synced from site: %d posts, %d pexels ids, %d urls (%d batches)",
            stats["posts"],
            stats["pexels_ids"],
            stats["source_urls"],
            stats["media_batches"],
        )
        ctx.exclude_pexels = load_exclude_pexels()

    return ctx


def prune(max_age_days: int = 90) -> int:
    cutoff = time.time() - (max_age_days * 86400)
    conn = _connect()
    cur = conn.execute("DELETE FROM used_images WHERE seen_at < ?", (cutoff,))
    deleted = int(cur.rowcount)
    cur2 = conn.execute("DELETE FROM used_source_urls WHERE seen_at < ?", (cutoff,))
    deleted += int(cur2.rowcount)
    conn.commit()
    conn.close()
    return deleted
