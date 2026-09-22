"""
LinkedIn Posts API — link shares to the Waqya company page.

Requires OAuth tokens from linkedin_auth.py (never commit secrets).
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import requests

log = logging.getLogger(__name__)

API_BASE = "https://api.linkedin.com/rest"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
DEFAULT_API_VERSION = "202601"


def _api_version() -> str:
    return os.environ.get("LINKEDIN_API_VERSION", DEFAULT_API_VERSION).strip()


def _headers(access_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": _api_version(),
    }


def _client_credentials() -> tuple[str, str]:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET required")
    return client_id, client_secret


def refresh_access_token() -> str:
    """Exchange refresh token for a new access token; updates env for this process."""
    refresh = os.environ.get("LINKEDIN_REFRESH_TOKEN", "").strip()
    if not refresh:
        raise RuntimeError("LINKEDIN_REFRESH_TOKEN missing — run: python linkedin_auth.py")

    client_id, client_secret = _client_credentials()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    access = data.get("access_token", "")
    if not access:
        raise RuntimeError(f"LinkedIn token refresh failed: {data}")
    os.environ["LINKEDIN_ACCESS_TOKEN"] = access
    if data.get("refresh_token"):
        os.environ["LINKEDIN_REFRESH_TOKEN"] = data["refresh_token"]
    expires = int(data.get("expires_in", 0) or 0)
    if expires:
        os.environ["LINKEDIN_ACCESS_TOKEN_EXPIRES_AT"] = str(int(time.time()) + expires)
    log.info("LinkedIn access token refreshed (expires_in=%s)", expires)
    return access


def get_access_token() -> str:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    expires_at = int(os.environ.get("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT", "0") or "0")
    if token and expires_at and time.time() < expires_at - 300:
        return token
    if os.environ.get("LINKEDIN_REFRESH_TOKEN", "").strip():
        return refresh_access_token()
    if token:
        return token
    raise RuntimeError("LINKEDIN_ACCESS_TOKEN missing — run: python linkedin_auth.py")


def resolve_organization_urn(vanity: str = "waqya") -> str:
    """Look up company page URN by vanity name (e.g. waqya → linkedin.com/company/waqya)."""
    configured = os.environ.get("LINKEDIN_ORGANIZATION_URN", "").strip()
    if configured:
        return configured

    token = get_access_token()
    resp = requests.get(
        f"{API_BASE}/organizations",
        headers=_headers(token),
        params={"q": "vanityName", "vanityName": vanity},
        timeout=30,
    )
    resp.raise_for_status()
    elements = resp.json().get("elements") or []
    if not elements:
        raise RuntimeError(f"LinkedIn organization not found for vanityName={vanity!r}")
    org_id = elements[0].get("id")
    urn = f"urn:li:organization:{org_id}"
    log.info("Resolved LinkedIn org %s → %s", vanity, urn)
    return urn


def upload_image_from_url(image_url: str) -> str | None:
    """Upload thumbnail for article card; returns Image URN or None."""
    if not image_url:
        return None
    try:
        img_resp = requests.get(image_url, timeout=30)
        img_resp.raise_for_status()
        image_bytes = img_resp.content
        content_type = img_resp.headers.get("Content-Type", "image/jpeg").split(";")[0]
    except Exception:
        log.exception("LinkedIn thumbnail download failed")
        return None

    token = get_access_token()
    author = os.environ.get("LINKEDIN_ORGANIZATION_URN", "").strip()
    if not author:
        author = resolve_organization_urn()

    init_resp = requests.post(
        f"{API_BASE}/images?action=initializeUpload",
        headers=_headers(token),
        json={"initializeUploadRequest": {"owner": author}},
        timeout=30,
    )
    if not init_resp.ok:
        log.warning("LinkedIn image init failed: %s %s", init_resp.status_code, init_resp.text[:200])
        return None

    init = init_resp.json().get("value") or {}
    upload_url = init.get("uploadUrl")
    image_urn = init.get("image")
    if not upload_url or not image_urn:
        return None

    put_resp = requests.put(
        upload_url,
        data=image_bytes,
        headers={"Content-Type": content_type},
        timeout=60,
    )
    if not put_resp.ok:
        log.warning("LinkedIn image upload failed: %s", put_resp.status_code)
        return None
    return str(image_urn)


def post_article_link(
    *,
    title: str,
    article_url: str,
    commentary: str,
    description: str = "",
    thumbnail_url: str = "",
) -> str:
    """
    Publish a link share to the Waqya company page feed.
    Returns post URN from x-restli-id header.
    """
    token = get_access_token()
    author = os.environ.get("LINKEDIN_ORGANIZATION_URN", "").strip()
    if not author:
        author = resolve_organization_urn()

    article: dict[str, Any] = {
        "source": article_url,
        "title": title[:400],
    }
    if description:
        article["description"] = description[:4000]

    thumb_urn = upload_image_from_url(thumbnail_url)
    if thumb_urn:
        article["thumbnail"] = thumb_urn

    payload = {
        "author": author,
        "commentary": commentary[:3000],
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {"article": article},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    resp = requests.post(
        f"{API_BASE}/posts",
        headers=_headers(token),
        json=payload,
        timeout=30,
    )
    if resp.status_code == 401:
        token = refresh_access_token()
        resp = requests.post(
            f"{API_BASE}/posts",
            headers=_headers(token),
            json=payload,
            timeout=30,
        )
    resp.raise_for_status()
    post_id = resp.headers.get("x-restli-id") or resp.json().get("id", "")
    log.info("LinkedIn posted: %s", post_id)
    return str(post_id)
