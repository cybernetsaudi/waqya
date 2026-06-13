"""
Deduplication store backed by SQLite.

Tracks story URLs and fingerprints so the same wire story or topic
cannot be republished with a new headline.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

from url_utils import normalize_story_url, url_fingerprint

DB_PATH = Path(__file__).parent / "seen.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_stories (
            fingerprint TEXT PRIMARY KEY,
            title       TEXT,
            source      TEXT,
            seen_at     REAL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS seen_urls (
            url_fp TEXT PRIMARY KEY,
            url    TEXT,
            seen_at REAL
        )
        """
    )
    conn.commit()
    return conn


def fingerprint(title: str, url: str) -> str:
    raw = f"{title.strip().lower()}|{normalize_story_url(url)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def recent_titles(max_age_days: int = 7, limit: int = 120) -> list[str]:
    cutoff = time.time() - (max_age_days * 86400)
    conn = _connect()
    rows = conn.execute(
        "SELECT title FROM seen_stories WHERE seen_at >= ? ORDER BY seen_at DESC LIMIT ?",
        (cutoff, limit),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]


def is_url_seen(url: str) -> bool:
    fp = url_fingerprint(url)
    if not fp:
        return False
    conn = _connect()
    row = conn.execute("SELECT 1 FROM seen_urls WHERE url_fp = ?", (fp,)).fetchone()
    conn.close()
    return row is not None


def is_similar_event(title: str, summary: str = "", threshold: float = 0.42) -> bool:
    try:
        from story_diversity import cluster_key, clusters_match, story_entities
    except ImportError:
        return False

    ck = cluster_key(title, summary)
    for prev in recent_titles():
        if clusters_match(ck, cluster_key(prev), threshold):
            return True
        if story_entities(title, summary) & story_entities(prev):
            return True
    return False


def is_seen(title: str, url: str, summary: str = "") -> bool:
    if is_url_seen(url):
        return True
    conn = _connect()
    fp = fingerprint(title, url)
    row = conn.execute(
        "SELECT 1 FROM seen_stories WHERE fingerprint = ?", (fp,)
    ).fetchone()
    conn.close()
    if row is not None:
        return True
    return is_similar_event(title, summary)


def mark_seen(title: str, url: str, source: str) -> None:
    conn = _connect()
    fp = fingerprint(title, url)
    conn.execute(
        "INSERT OR IGNORE INTO seen_stories (fingerprint, title, source, seen_at) "
        "VALUES (?, ?, ?, ?)",
        (fp, title, source, time.time()),
    )
    url_fp = url_fingerprint(url)
    norm = normalize_story_url(url)
    if url_fp and norm:
        conn.execute(
            "INSERT OR IGNORE INTO seen_urls (url_fp, url, seen_at) VALUES (?, ?, ?)",
            (url_fp, norm, time.time()),
        )
    conn.commit()
    conn.close()


def count_seen() -> int:
    conn = _connect()
    n = conn.execute("SELECT COUNT(*) FROM seen_stories").fetchone()[0]
    conn.close()
    return int(n)


def prune(max_age_days: int = 30) -> int:
    cutoff = time.time() - (max_age_days * 86400)
    conn = _connect()
    cur = conn.execute("DELETE FROM seen_stories WHERE seen_at < ?", (cutoff,))
    deleted = int(cur.rowcount)
    cur2 = conn.execute("DELETE FROM seen_urls WHERE seen_at < ?", (cutoff,))
    deleted += int(cur2.rowcount)
    conn.commit()
    conn.close()
    return deleted
