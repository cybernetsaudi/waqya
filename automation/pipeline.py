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
from pathlib import Path

import yaml
from dotenv import load_dotenv

log = logging.getLogger("waqya")

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def run() -> int:
    """Execute the full pipeline. Returns 0 on success, 1 on failure."""
    from budget_tracker import maybe_alert_monthly_cap, maybe_send_weekly_summary, record_run
    from dedup import prune
    from gatherer import gather
    from generator import generate_batch
    from image_dedup import prune as prune_images
    from notifier import notify_error, notify_pipeline_results
    from publisher import publish_batch
    from setup_trust_pages import ensure_trust_pages

    config = _load_config()

    maybe_send_weekly_summary(config)

    prune(max_age_days=3)
    prune_images(max_age_days=90)

    try:
        from sync_categories import sync_all

        sync_all()
    except Exception:
        log.exception("IPTC category sync failed (continuing)")

    try:
        n_pages = ensure_trust_pages()
        if n_pages:
            log.info("Created %d trust/policy pages", n_pages)
    except Exception:
        log.exception("Trust pages setup failed (continuing)")

    log.info("=" * 50)
    log.info("STEP 1 / 4 — Gathering news")
    log.info("=" * 50)
    stories = gather()
    if not stories:
        log.info("No new stories found — nothing to do")
        try:
            from gatherer import GATHER_STATS
            from notifier import notify_gather_empty

            notify_gather_empty(GATHER_STATS)
        except Exception:
            log.exception("Empty-gather notification failed")
        maybe_alert_monthly_cap(config)
        return 0

    log.info("=" * 50)
    log.info("STEP 2 / 4 — Generating articles (%d stories)", len(stories))
    log.info("=" * 50)
    articles = generate_batch(stories)
    if not articles:
        log.warning("Article generation produced nothing — exiting")
        return 0

    log.info("=" * 50)
    log.info("STEP 3 / 4 — Publishing to WordPress")
    log.info("=" * 50)
    results = publish_batch(articles)

    if articles and not results:
        from notifier import notify_publish_failed

        notify_publish_failed(len(articles))

    log.info("=" * 50)
    log.info("STEP 4 / 5 — Social distribution")
    log.info("=" * 50)
    social_summary = ""
    try:
        from social_poster import distribute_publish_results

        social_counts = distribute_publish_results(results, config)
        log.info("Social: %s", social_counts)
        social_summary = (
            f"Bluesky {social_counts.get('bluesky', 0)} · "
            f"Mastodon {social_counts.get('mastodon', 0)} · "
            f"TG {social_counts.get('telegram', 0)} · "
            f"errors {social_counts.get('errors', 0)}"
        )
    except Exception:
        log.exception("Social distribution failed (continuing)")
        social_summary = "failed (see Actions logs)"

    log.info("=" * 50)
    log.info("STEP 5 / 5 — Telegram + budget")
    log.info("=" * 50)
    wp_url = os.environ.get("WP_URL", "https://waqya.com").rstrip("/")
    notify_pipeline_results(results, wp_url, social_summary=social_summary)

    published = sum(1 for r in results if r.status == "publish")
    held = len(results) - published
    record_run(
        config,
        articles=len(results),
        published=published,
        held_draft=held,
    )
    maybe_alert_monthly_cap(config)

    log.info(
        "Pipeline complete: %d live, %d held (%d total)",
        published,
        held,
        len(results),
    )
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
