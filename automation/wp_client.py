"""
Shared WordPress REST client for the automation pipeline.

Hostinger / LiteSpeed may block cloud IPs (403). Retries with backoff and a
small gap between requests reduce false WAF failures from GitHub Actions.
"""

from __future__ import annotations

import logging
import os
import random
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests
import yaml

log = logging.getLogger(__name__)

WP_USER_AGENT = "WaqyaPipeline/1.0 (+https://waqya.com; automation@waqya.com)"
DEFAULT_TIMEOUT = 30
CONFIG_PATH = Path(__file__).parent / "config.yaml"

_last_request_at = 0.0


@lru_cache(maxsize=1)
def _wp_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("wordpress", {})
    except Exception:
        return {}


def wp_credentials() -> tuple[str, tuple[str, str]]:
    base = os.environ.get("WP_URL", "").strip().rstrip("/")
    user = os.environ.get("WP_USER", "").strip()
    password = os.environ.get("WP_APP_PASSWORD", "").strip()
    if not base or not user or not password:
        raise RuntimeError("Missing WP_URL, WP_USER, or WP_APP_PASSWORD")
    return base, (user, password)


def wp_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {
        "User-Agent": WP_USER_AGENT,
        "Accept": "application/json",
    }
    if extra:
        headers.update(extra)
    return headers


def _throttle() -> None:
    global _last_request_at
    gap = float(_wp_config().get("request_delay_seconds", 0.25))
    if gap <= 0:
        return
    now = time.monotonic()
    wait = gap - (now - _last_request_at)
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _retryable_statuses() -> set[int]:
    codes = _wp_config().get("retry_status_codes", [403, 429, 502, 503, 504])
    return {int(c) for c in codes}


def _request_with_retry(method: str, url: str, **kwargs: Any) -> requests.Response:
    wcfg = _wp_config()
    max_attempts = max(1, int(wcfg.get("retry_max_attempts", 5)))
    base_delay = float(wcfg.get("retry_backoff_seconds", 3))
    retryable = _retryable_statuses()

    last_resp: requests.Response | None = None
    for attempt in range(1, max_attempts + 1):
        _throttle()
        resp = requests.request(method, url, **kwargs)
        if resp.status_code not in retryable:
            return resp
        last_resp = resp
        if attempt >= max_attempts:
            break
        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.5)
        path = url.split("/wp-json", 1)[-1][:80] if "/wp-json" in url else url[-80:]
        log.warning(
            "WordPress %s %s → HTTP %d, retry %d/%d in %.1fs",
            method,
            path,
            resp.status_code,
            attempt,
            max_attempts,
            delay,
        )
        time.sleep(delay)

    assert last_resp is not None
    return last_resp


def wp_get(path: str, *, params: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    base, auth = wp_credentials()
    url = path if path.startswith("http") else f"{base}{path}"
    return _request_with_retry(
        "GET",
        url,
        params=params,
        auth=auth,
        headers=wp_headers(),
        timeout=timeout,
    )


def wp_post(
    path: str,
    *,
    json: dict | list | None = None,
    data: Any = None,
    headers: dict[str, str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> requests.Response:
    base, auth = wp_credentials()
    url = path if path.startswith("http") else f"{base}{path}"
    return _request_with_retry(
        "POST",
        url,
        json=json,
        data=data,
        auth=auth,
        headers=wp_headers(headers),
        timeout=timeout,
    )
