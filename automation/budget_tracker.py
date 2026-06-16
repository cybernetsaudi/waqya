"""
Track estimated API spend and send Telegram budget alerts.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

USAGE_PATH = Path(__file__).parent / "budget_usage.json"

# Rough USD estimates (adjust in config.yaml → budget.estimates)
DEFAULT_ESTIMATES = {
    "openai_per_1k_output_tokens": 0.0006,
    "openai_per_article_tokens": 2500,
    "newsapi_per_request": 0.0,
    "pexels_per_search": 0.0,
    "pipeline_base_per_run": 0.02,
}


def _load_usage() -> dict:
    if not USAGE_PATH.is_file():
        return {"months": {}, "last_weekly_alert": ""}
    with open(USAGE_PATH) as f:
        return json.load(f)


def _save_usage(data: dict) -> None:
    with open(USAGE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _week_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-W%W")


def estimate_run_cost(
    config: dict,
    *,
    articles: int,
    newsapi_requests: int = 28,
    pexels_searches: int = 0,
) -> float:
    est = {**DEFAULT_ESTIMATES, **config.get("budget", {}).get("estimates", {})}
    cost = float(est.get("pipeline_base_per_run", 0.02))
    llm_per_article = est.get("llm_per_article_usd")
    if llm_per_article is not None:
        cost += articles * float(llm_per_article)
    else:
        cost += articles * (
            float(est.get("openai_per_article_tokens", 2500))
            / 1000
            * float(est.get("openai_per_1k_output_tokens", 0.0006))
        )
    cost += newsapi_requests * float(est.get("newsapi_per_request", 0))
    cost += pexels_searches * float(est.get("pexels_per_search", 0))
    return round(cost, 4)


def record_run(
    config: dict,
    *,
    articles: int,
    published: int,
    held_draft: int,
    newsapi_requests: int = 28,
) -> float:
    """Add this run's estimated cost to the current month."""
    pexels = articles * 4 if config.get("images", {}).get("enabled") else 0
    cost = estimate_run_cost(
        config,
        articles=articles,
        newsapi_requests=newsapi_requests,
        pexels_searches=pexels,
    )
    data = _load_usage()
    month = _month_key()
    bucket = data.setdefault("months", {}).setdefault(
        month,
        {"spent_usd": 0.0, "runs": 0, "articles": 0, "published": 0, "held": 0},
    )
    bucket["spent_usd"] = round(bucket.get("spent_usd", 0) + cost, 4)
    bucket["runs"] = bucket.get("runs", 0) + 1
    bucket["articles"] = bucket.get("articles", 0) + articles
    bucket["published"] = bucket.get("published", 0) + published
    bucket["held"] = bucket.get("held", 0) + held_draft
    _save_usage(data)
    log.info("Budget: run ~$%.4f (month %s total ~$%.2f)", cost, month, bucket["spent_usd"])
    return cost


def month_summary(config: dict) -> dict:
    data = _load_usage()
    month = _month_key()
    bucket = data.get("months", {}).get(month, {})
    cap = float(config.get("budget", {}).get("monthly_cap_usd", 80))
    spent = float(bucket.get("spent_usd", 0))
    return {
        "month": month,
        "spent_usd": spent,
        "cap_usd": cap,
        "pct": round(100 * spent / cap, 1) if cap else 0,
        "runs": bucket.get("runs", 0),
        "articles": bucket.get("articles", 0),
        "published": bucket.get("published", 0),
        "held": bucket.get("held", 0),
    }


def maybe_alert_monthly_cap(config: dict) -> bool:
    """Telegram if over alert threshold. Returns True if alert sent."""
    bcfg = config.get("budget", {})
    if not bcfg.get("enabled", True):
        return False

    summary = month_summary(config)
    cap = summary["cap_usd"]
    pct_threshold = float(bcfg.get("alert_at_percent", 80))
    if cap <= 0 or summary["pct"] < pct_threshold:
        return False

    from notifier import send_message

    text = (
        f"<b>💰 Waqya budget alert</b>\n\n"
        f"Month <b>{summary['month']}</b>: ~${summary['spent_usd']:.2f} "
        f"of ${cap:.0f} cap ({summary['pct']}%)\n"
        f"Runs: {summary['runs']} · Articles: {summary['articles']}\n"
        f"Published: {summary['published']} · Held as draft: {summary['held']}"
    )
    return send_message(text)


def maybe_send_weekly_summary(config: dict) -> bool:
    """Send at most one weekly summary per calendar week."""
    bcfg = config.get("budget", {})
    if not bcfg.get("weekly_summary", True):
        return False

    data = _load_usage()
    week = _week_key()
    if data.get("last_weekly_alert") == week:
        return False

    summary = month_summary(config)
    from notifier import send_message

    from desk_report import format_desk_report_lines

    desk_lines = format_desk_report_lines(days=7)
    text = (
        f"<b>📊 Waqya weekly ops summary</b>\n\n"
        f"<b>Month {summary['month']}</b> (est. costs)\n"
        f"Spend: ~${summary['spent_usd']:.2f} / ${summary['cap_usd']:.0f}\n"
        f"Pipeline runs: {summary['runs']}\n"
        f"Articles generated: {summary['articles']}\n"
        f"Live: {summary['published']} · Drafts held: {summary['held']}\n\n"
        f"Crisis mode: {'ON' if config.get('crisis_mode', {}).get('enabled') else 'off'}\n\n"
        + "\n".join(desk_lines)
    )
    ok = send_message(text)
    if ok:
        data["last_weekly_alert"] = week
        _save_usage(data)
    return ok
