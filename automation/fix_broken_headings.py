#!/usr/bin/env python3
"""Fix stored post HTML where paragraphs were saved inside h2/h3 tags."""

from __future__ import annotations

import os
import re
import sys
from html import escape
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_H_RE = re.compile(r"<(h[23])([^>]*)>(.*?)</\1>", re.I | re.S)


def _fix_html(html: str) -> str:
    def _repl(match: re.Match[str]) -> str:
        tag = match.group(1).lower()
        attrs = match.group(2)
        inner = match.group(3)
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip()
        has_br = bool(re.search(r"<br\s*/?>", inner, re.I))
        has_nl = bool(re.search(r"\n", inner))
        looks_long = len(plain) > 90
        if not has_br and not has_nl and not looks_long:
            return match.group(0)
        if has_br:
            parts = re.split(r"<br\s*/?>", inner, maxsplit=1, flags=re.I)
        else:
            parts = re.split(r"\n+", inner.strip(), maxsplit=1)
        title = re.sub(r"<[^>]+>", "", parts[0]).strip()
        rest = re.sub(r"<[^>]+>", "", parts[1]).strip() if len(parts) > 1 else ""
        if not title:
            return match.group(0)
        out = f"<{tag}{attrs}>{escape(title)}</{tag}>"
        if rest:
            out += f"<p>{escape(rest)}</p>"
        return out

    return _H_RE.sub(_repl, html)


def main() -> int:
    base = os.environ["WP_URL"].rstrip("/")
    auth = (os.environ["WP_USER"], os.environ["WP_APP_PASSWORD"])
    page = 1
    fixed = 0
    while True:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={"per_page": 50, "page": page, "status": "publish", "context": "edit"},
            auth=auth,
            timeout=30,
        )
        resp.raise_for_status()
        posts = resp.json()
        if not posts:
            break
        for post in posts:
            raw = post.get("content", {}).get("raw", "")
            if not raw or "<h2" not in raw.lower():
                continue
            new_raw = _fix_html(raw)
            if new_raw == raw:
                continue
            upd = requests.post(
                f"{base}/wp-json/wp/v2/posts/{post['id']}",
                json={"content": new_raw},
                auth=auth,
                timeout=60,
            )
            upd.raise_for_status()
            fixed += 1
            print(f"Fixed #{post['id']}: {post.get('title', {}).get('rendered', '')[:60]}")
        page += 1
    print(f"Done — {fixed} post(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
