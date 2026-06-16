"""
NewsAPI request budget — free tier is ~100 requests/day.

Tracks usage in newsapi_usage.json (cached on GitHub Actions). Stops requests
when daily or per-run limits are hit, or after a 429 response.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

log = logging.getLogger(__name__)

USAGE_PATH = Path(__file__).parent / "newsapi_usage.json"
_rate_limited_run = False


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    if not USAGE_PATH.is_file():
        return {"day": "", "daily_count": 0, "run_count": 0}
    with open(USAGE_PATH) as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(USAGE_PATH, "w") as f:
        json.dump(data, f, indent=2)


def begin_run(config: dict) -> None:
    """Reset per-run counter; roll daily counter at UTC midnight."""
    global _rate_limited_run
    _rate_limited_run = False
    data = _load()
    today = _today()
    if data.get("day") != today:
        data = {"day": today, "daily_count": 0, "run_count": 0}
    else:
        data["run_count"] = 0
    _save(data)


def _limits(config: dict) -> tuple[int, int]:
    api_cfg = config.get("newsapi", {})
    daily = int(api_cfg.get("max_requests_per_day", 90))
    per_run = int(api_cfg.get("max_requests_per_run", 12))
    return daily, per_run


def can_request(config: dict) -> bool:
    if _rate_limited_run:
        return False
    if not config.get("newsapi", {}).get("enabled", True):
        return False
    daily_cap, run_cap = _limits(config)
    data = _load()
    if data.get("day") != _today():
        return True
    if data.get("daily_count", 0) >= daily_cap:
        return False
    if data.get("run_count", 0) >= run_cap:
        return False
    return True


def record_request() -> None:
    data = _load()
    today = _today()
    if data.get("day") != today:
        data = {"day": today, "daily_count": 0, "run_count": 0}
    data["daily_count"] = int(data.get("daily_count", 0)) + 1
    data["run_count"] = int(data.get("run_count", 0)) + 1
    _save(data)


def mark_rate_limited() -> None:
    global _rate_limited_run
    _rate_limited_run = True
    log.warning("NewsAPI rate limited (429) — skipping further NewsAPI calls this run")


def usage_summary(config: dict) -> str:
    daily_cap, run_cap = _limits(config)
    data = _load()
    if data.get("day") != _today():
        return f"NewsAPI today: 0/{daily_cap} (this run 0/{run_cap})"
    return (
        f"NewsAPI today: {data.get('daily_count', 0)}/{daily_cap} "
        f"(this run {data.get('run_count', 0)}/{run_cap})"
    )


def get(
    config: dict,
    url: str,
    *,
    params: dict[str, Any],
    timeout: int = 12,
    label: str = "",
) -> requests.Response | None:
    """GET with budget tracking. Returns None when skipped or on 429."""
    if not can_request(config):
        if label:
            log.info("NewsAPI skip (budget): %s", label)
        return None
    try:
        record_request()
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 429:
            mark_rate_limited()
            log.warning("NewsAPI 429 on %s", label or url)
            return None
        resp.raise_for_status()
        return resp
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 429:
            mark_rate_limited()
        log.exception("NewsAPI failed: %s", label or url)
        return None
    except Exception:
        log.exception("NewsAPI failed: %s", label or url)
        return None
