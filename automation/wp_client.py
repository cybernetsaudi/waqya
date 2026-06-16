"""
Shared WordPress REST client for the automation pipeline.

Hostinger / LiteSpeed often block default python-requests User-Agents from
cloud IPs. Use a stable UA and shared auth for all WP JSON calls.
"""

from __future__ import annotations

import os
from typing import Any

import requests

WP_USER_AGENT = "WaqyaPipeline/1.0 (+https://waqya.com; automation@waqya.com)"
DEFAULT_TIMEOUT = 30


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


def wp_get(path: str, *, params: dict | None = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    base, auth = wp_credentials()
    url = path if path.startswith("http") else f"{base}{path}"
    return requests.get(
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
    return requests.post(
        url,
        json=json,
        data=data,
        auth=auth,
        headers=wp_headers(headers),
        timeout=timeout,
    )
