"""
Load supplemental news sources (Google News RSS, extra feeds).
"""

from __future__ import annotations

import os

import yaml

EXTRA_SOURCES_PATH = os.path.join(os.path.dirname(__file__), "extra_sources.yaml")


def merge_extra_sources(cfg: dict) -> dict:
    """Append google_news + extra RSS from extra_sources.yaml into config."""
    if not os.path.isfile(EXTRA_SOURCES_PATH):
        return cfg

    with open(EXTRA_SOURCES_PATH) as f:
        extra = yaml.safe_load(f) or {}

    if extra.get("google_news"):
        cfg["google_news"] = extra["google_news"]

    extra_rss = extra.get("rss_feeds") or []
    if extra_rss:
        cfg["rss_feeds"] = list(cfg.get("rss_feeds", [])) + extra_rss

    return cfg
