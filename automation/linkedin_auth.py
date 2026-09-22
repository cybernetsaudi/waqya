#!/usr/bin/env python3
"""
One-time LinkedIn OAuth for the Waqya company page.

Usage:
  1. Add to .env (repo root):
       LINKEDIN_CLIENT_ID=...
       LINKEDIN_CLIENT_SECRET=...
  2. In LinkedIn Developer app → Auth → add redirect URL:
       http://localhost:8765/linkedin/callback
  3. Request products: Community Management API, Sign In with LinkedIn (OpenID)
  4. Run:
       cd automation && python3 linkedin_auth.py

Sign in as a LinkedIn user who is ADMIN on https://www.linkedin.com/company/waqya/
"""

from __future__ import annotations

import json
import os
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

REDIRECT_URI = os.environ.get("LINKEDIN_REDIRECT_URI", "http://localhost:8765/linkedin/callback")
SCOPES = [
    "openid",
    "profile",
    "w_organization_social",
    "r_organization_admin",
]


def _credentials() -> tuple[str, str]:
    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "").strip()
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "Set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET in .env first "
            "(never commit the secret)."
        )
    return client_id, client_secret


def _auth_url(state: str) -> str:
    client_id, _ = _credentials()
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": " ".join(SCOPES),
    }
    return "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params)


def _exchange_code(code: str) -> dict:
    client_id, client_secret = _credentials()
    resp = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _organization_urn(access_token: str, vanity: str = "waqya") -> str:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": os.environ.get("LINKEDIN_API_VERSION", "202601"),
    }
    resp = requests.get(
        "https://api.linkedin.com/rest/organizations",
        headers=headers,
        params={"q": "vanityName", "vanityName": vanity},
        timeout=30,
    )
    resp.raise_for_status()
    elements = resp.json().get("elements") or []
    if not elements:
        raise SystemExit(f"Could not find organization vanityName={vanity!r}")
    return f"urn:li:organization:{elements[0]['id']}"


def main() -> None:
    state = secrets.token_urlsafe(16)
    auth_url = _auth_url(state)
    captured: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/linkedin/callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("state", [""])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch")
                return
            if "error" in qs:
                captured["error"] = qs.get("error_description", qs["error"])[0]
            else:
                captured["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>LinkedIn connected</h1>"
                b"<p>You can close this tab and return to the terminal.</p></body></html>"
            )

        def log_message(self, fmt, *args):  # noqa: A003
            return

    print("Opening LinkedIn authorization in your browser...")
    print(f"If it does not open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = HTTPServer(("127.0.0.1", 8765), Handler)
    server.handle_request()

    if captured.get("error"):
        raise SystemExit(f"LinkedIn OAuth error: {captured['error']}")
    code = captured.get("code", "")
    if not code:
        raise SystemExit("No authorization code received")

    tokens = _exchange_code(code)
    access = tokens.get("access_token", "")
    refresh = tokens.get("refresh_token", "")
    expires_in = int(tokens.get("expires_in", 0) or 0)
    expires_at = int(time.time()) + expires_in if expires_in else 0

    org_urn = _organization_urn(access)

    print("\n=== Add these to .env and GitHub Secrets ===\n")
    print(f"LINKEDIN_ACCESS_TOKEN={access}")
    if refresh:
        print(f"LINKEDIN_REFRESH_TOKEN={refresh}")
    if expires_at:
        print(f"LINKEDIN_ACCESS_TOKEN_EXPIRES_AT={expires_at}")
    print(f"LINKEDIN_ORGANIZATION_URN={org_urn}")
    print("\n=== GitHub Secrets (repo → Settings → Secrets) ===\n")
    print("LINKEDIN_CLIENT_ID")
    print("LINKEDIN_CLIENT_SECRET")
    print("LINKEDIN_ACCESS_TOKEN")
    print("LINKEDIN_REFRESH_TOKEN")
    print("LINKEDIN_ORGANIZATION_URN")
    print("LINKEDIN_ACCESS_TOKEN_EXPIRES_AT")
    print("\nDone. Re-run pipeline after secrets are set.")


if __name__ == "__main__":
    main()
