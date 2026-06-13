#!/usr/bin/env python3
"""
Configure hello@waqya.com SMTP on WordPress (Hostinger) from .env.

Required in .env (never commit real values):
  WP_SMTP_PASSWORD=your-mailbox-password
Optional:
  WP_SMTP_HOST=smtp.hostinger.com
  WP_SMTP_PORT=465
  WP_SMTP_USER=hello@waqya.com
  WP_SMTP_FROM=hello@waqya.com
  WP_SMTP_FROM_NAME=Waqya
  PLAUSIBLE_DOMAIN=waqya.com
"""

from __future__ import annotations

import logging
import os
import shlex
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


def _ssh(cmd: str) -> None:
    sshpass = os.environ.get("SSHPASS")
    if not sshpass:
        raise SystemExit(
            "Set SSHPASS for Hostinger SSH, or run wp option update commands manually on the server."
        )
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
    log.info("Running remote: %s", cmd.split("&&")[-1].strip()[:80])
    subprocess.run(full, check=True, env={**os.environ, "SSHPASS": sshpass})


def _wp_option(key: str, value: str, *, autoload: str = "yes") -> str:
    return f"wp option update {shlex.quote(key)} {shlex.quote(value)} --autoload={autoload}"


def _env(*keys: str, default: str = "") -> str:
    for key in keys:
        val = os.environ.get(key, "").strip()
        if val:
            return val
    return default


def configure() -> int:
    password = _env("WP_SMTP_PASSWORD", "SMTP_PASSWORD")
    if not password:
        log.error(
            "Missing WP_SMTP_PASSWORD or SMTP_PASSWORD in .env — add your mailbox password, then re-run."
        )
        return 1

    user = _env("WP_SMTP_USER", "SMTP_USER", default="hello@waqya.com")
    host = _env("WP_SMTP_HOST", "SMTP_HOST", default="smtp.hostinger.com")
    port = _env("WP_SMTP_PORT", "SMTP_PORT", default="465")
    secure = _env("WP_SMTP_SECURE", "SMTP_SECURE", default="ssl")
    from_addr = _env("WP_SMTP_FROM", "SMTP_FROM", default=user)
    from_name = _env("WP_SMTP_FROM_NAME", "SMTP_FROM_NAME", default="Waqya")
    plausible = os.environ.get("PLAUSIBLE_DOMAIN", "").strip()

    cmds = [
        _wp_option("waqya_smtp_host", host),
        _wp_option("waqya_smtp_port", port),
        _wp_option("waqya_smtp_secure", secure),
        _wp_option("waqya_smtp_user", user),
        _wp_option("waqya_smtp_pass", password, autoload="no"),
        _wp_option("waqya_mail_from", from_addr),
        _wp_option("waqya_mail_from_name", from_name),
        _wp_option("admin_email", from_addr),
    ]
    if plausible:
        cmds.append(_wp_option("waqya_plausible_domain", plausible))

    repo = Path(__file__).resolve().parent.parent
    mu_local = repo / "wordpress/mu-plugins/waqya-smtp.php"
    if mu_local.is_file():
        rsync = [
            "sshpass",
            "-e",
            "rsync",
            "-avz",
            "-e",
            f"ssh -p {SSH_PORT} -o StrictHostKeyChecking=accept-new",
            str(mu_local),
            f"{SSH_USER}@{SSH_HOST}:domains/waqya.com/public_html/wp-content/mu-plugins/",
        ]
        subprocess.run(rsync, check=True, env=os.environ)

    _ssh(" && ".join(cmds))
    _ssh("wp cache flush")
    log.info("SMTP configured for %s — test with: wp cron event run waqya_send_weekly_digest", from_addr)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _load_env()
    return configure()


if __name__ == "__main__":
    sys.exit(main())
