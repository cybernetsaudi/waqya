#!/usr/bin/env python3
"""
Waqya pipeline — the main orchestrator.

Runs the full cycle: gather → generate → publish → SEO → notify.
Designed to be triggered by GitHub Actions on a cron schedule.
"""

from __future__ import annotations

import logging
import os
import sys
import traceback

from dotenv import load_dotenv

log = logging.getLogger("waqya")


def run() -> int:
    """Execute the full pipeline. Returns 0 on success, 1 on failure."""
    from gatherer import gather
    from generator import generate_batch
    from publisher import publish_batch
    from notifier import notify_new_drafts, notify_error
    from dedup import prune

    prune(max_age_days=7)

    # Ensure IPTC categories exist in WordPress before publishing
    try:
        from sync_categories import sync_all
        sync_all()
    except Exception:
        log.exception("IPTC category sync failed (continuing)")

    log.info("=" * 50)
    log.info("STEP 1 / 4 — Gathering news")
    log.info("=" * 50)
    stories = gather()
    if not stories:
        log.info("No new stories found — nothing to do")
        return 0

    log.info("=" * 50)
    log.info("STEP 2 / 4 — Generating articles (%d stories)", len(stories))
    log.info("=" * 50)
    articles = generate_batch(stories)
    if not articles:
        log.warning("Article generation produced nothing — exiting")
        return 0

    log.info("=" * 50)
    log.info("STEP 3 / 4 — Publishing drafts to WordPress")
    log.info("=" * 50)
    results = publish_batch(articles)

    log.info("=" * 50)
    log.info("STEP 4 / 5 — Sending Telegram notification")
    log.info("=" * 50)
    wp_url = os.environ.get("WP_URL", "https://waqya.com").rstrip("/")
    notify_new_drafts(results, wp_url)

    log.info("Pipeline complete: %d drafts created", len(results))
    return 0


def main():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )

    try:
        sys.exit(run())
    except Exception:
        tb = traceback.format_exc()
        log.critical("Pipeline crashed:\n%s", tb)
        try:
            from notifier import notify_error
            notify_error(tb[-500:])
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
