#!/usr/bin/env python3
"""
Diagnose WordPress outbound mail on the live server (SMTP auth + queue status).

Usage:
  export SSHPASS='...'
  python automation/test_wordpress_mail.py
  python automation/test_wordpress_mail.py --send hello@waqya.com
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

SSH_HOST = os.environ.get("WAQYA_SSH_HOST", "145.79.209.14")
SSH_PORT = os.environ.get("WAQYA_SSH_PORT", "65002")
SSH_USER = os.environ.get("WAQYA_SSH_USER", "u950050130")
WP_PATH = os.environ.get("WAQYA_WP_PATH", "~/domains/waqya.com/public_html")


def _load_env() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())


def _ssh(cmd: str, *, timeout: int = 90) -> subprocess.CompletedProcess[str]:
    sshpass = os.environ.get("SSHPASS")
    if not sshpass:
        raise SystemExit("Set SSHPASS in the environment.")
    full = [
        "sshpass",
        "-e",
        "ssh",
        "-p",
        SSH_PORT,
        "-o",
        "StrictHostKeyChecking=accept-new",
        f"{SSH_USER}@{SSH_HOST}",
        f"cd {WP_PATH} && {cmd}",
    ]
    return subprocess.run(
        full,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "SSHPASS": sshpass},
        timeout=timeout,
    )


def diagnose(send_to: str | None) -> int:
    checks = [
        ("mu-plugin", 'wp eval \'echo function_exists("waqya_smtp_configure") ? "loaded" : "missing";\''),
        ("smtp_host", "wp option get waqya_smtp_host"),
        ("smtp_port", "wp option get waqya_smtp_port"),
        ("smtp_user", "wp option get waqya_smtp_user"),
        ("mail_from", "wp option get waqya_mail_from"),
        ("pass_set", 'wp eval \'echo get_option("waqya_smtp_pass") ? "yes" : "no";\''),
        ("mx", "dig +short MX waqya.com"),
    ]

    print("=== Waqya mail diagnostics ===\n")
    for label, cmd in checks:
        r = _ssh(cmd, timeout=30)
        out = (r.stdout or r.stderr).strip()
        print(f"{label:12} {out or '(empty)'}")

    r = _ssh("wp option get waqya_mail_log --format=json 2>/dev/null || echo '[]'", timeout=30)
    print(f"\nrecent_log   {(r.stdout or '').strip()[:800]}")

    if send_to:
        print(f"\n--- Sending test to {send_to} (SMTP debug) ---\n")
        addr = send_to.replace("\\", "\\\\").replace('"', '\\"')
        php = f'''wp eval '
add_action("phpmailer_init", function($pm) {{
    $pm->SMTPDebug = 2;
    $pm->Debugoutput = function($str, $level) {{ fwrite(STDERR, $str . "\\n"); }};
}}, 99);
$ok = wp_mail("{addr}", "Waqya mail diagnostic", "Test at " . gmdate("c"));
fwrite(STDERR, "wp_mail: " . ($ok ? "true" : "false") . "\\n");
' 2>&1'''
        r = _ssh(php, timeout=60)
        print(r.stdout)
        print(r.stderr)

    print(
        "\nNote: wp_mail true + 'queued as …' means omniconsa accepted the message.\n"
        "If the inbox is empty, check omniconsa webmail, spam, quota, and inbound logs.\n"
        "MX for waqya.com should be mail.omniconsa.com (same host as SMTP)."
    )
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_env()
    p = argparse.ArgumentParser(description="Diagnose WordPress SMTP on production")
    p.add_argument("--send", metavar="EMAIL", help="Send a debug test message")
    args = p.parse_args()
    return diagnose(args.send)


if __name__ == "__main__":
    sys.exit(main())
