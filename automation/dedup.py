"""
Deduplication store backed by SQLite.

Tracks every news story the pipeline has already seen so the same event
is never processed twice, even across separate GitHub Actions runs
(the DB file is uploaded/downloaded as a workflow artifact).
"""

import hashlib
import sqlite3
import time
from pathlib import Path

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
    conn.commit()
    return conn


def fingerprint(title: str, url: str) -> str:
    """Stable hash for a story based on its title + URL."""
    raw = f"{title.strip().lower()}|{url.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def recent_titles(max_age_days: int = 3, limit: int = 80) -> list[str]:
    """Titles processed recently (for similar-event detection)."""
    cutoff = time.time() - (max_age_days * 86400)
    conn = _connect()
    rows = conn.execute(
        "SELECT title FROM seen_stories WHERE seen_at >= ? ORDER BY seen_at DESC LIMIT ?",
        (cutoff, limit),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]


def is_similar_event(title: str, summary: str = "", threshold: float = 0.52) -> bool:
    """True if title overlaps a recently processed story cluster."""
    try:
        from story_diversity import cluster_key, clusters_match
    except ImportError:
        return False

    ck = cluster_key(title, summary)
    for prev in recent_titles():
        if clusters_match(ck, cluster_key(prev), threshold):
            return True
    return False


def is_seen(title: str, url: str) -> bool:
    conn = _connect()
    fp = fingerprint(title, url)
    row = conn.execute(
        "SELECT 1 FROM seen_stories WHERE fingerprint = ?", (fp,)
    ).fetchone()
    conn.close()
    if row is not None:
        return True
    return is_similar_event(title)


def mark_seen(title: str, url: str, source: str) -> None:
    conn = _connect()
    fp = fingerprint(title, url)
    conn.execute(
        "INSERT OR IGNORE INTO seen_stories (fingerprint, title, source, seen_at) "
        "VALUES (?, ?, ?, ?)",
        (fp, title, source, time.time()),
    )
    conn.commit()
    conn.close()


def prune(max_age_days: int = 30) -> int:
    """Remove entries older than *max_age_days*. Returns count deleted."""
    cutoff = time.time() - (max_age_days * 86400)
    conn = _connect()
    cur = conn.execute("DELETE FROM seen_stories WHERE seen_at < ?", (cutoff,))
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted
