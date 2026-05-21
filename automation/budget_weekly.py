#!/usr/bin/env python3
"""Send weekly Telegram budget summary (GitHub Actions cron)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

CONFIG_PATH = Path(__file__).parent / "config.yaml"


def main() -> int:
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.is_file():
        load_dotenv(env_path)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    from budget_tracker import maybe_alert_monthly_cap, maybe_send_weekly_summary

    maybe_send_weekly_summary(config)
    maybe_alert_monthly_cap(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
