"""
Track images already used on Waqya so the same photo is not reused across posts.

Persisted in SQLite (uploaded with seen.db via GitHub Actions cache).
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).parent / "images.db"


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
    conn.commit()
    return conn


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:32]


def is_image_used(data: bytes | None = None, pexels_id: int | str | None = None) -> bool:
    """True if this image bytes or Pexels photo id was used before."""
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


def mark_article_images(images, headline: str = "") -> None:
    """Register all images from an ArticleImages bundle."""
    if not images:
        return
    if images.featured:
        mark_image_used(
            images.featured.data,
            getattr(images.featured, "pexels_id", None),
            context=headline,
        )
    for img in images.inline or []:
        mark_image_used(
            img.data,
            getattr(img, "pexels_id", None),
            context=headline,
        )


def count_used() -> int:
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM used_images").fetchone()[0]
    conn.close()
    return int(n)


def prune(max_age_days: int = 90) -> int:
    cutoff = time.time() - (max_age_days * 86400)
    conn = _connect()
    cur = conn.execute("DELETE FROM used_images WHERE seen_at < ?", (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted
