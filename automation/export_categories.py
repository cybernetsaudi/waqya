#!/usr/bin/env python3
"""Export waqya_categories.yaml → JSON for WordPress theme / frontend agent."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent
OUT = ROOT.parent / "wordpress" / "theme" / "waqya" / "config" / "categories.json"


def main() -> int:
    with open(ROOT / "waqya_categories.yaml") as f:
        data = yaml.safe_load(f)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Exported → {OUT}")
    print(f"  Primary categories: {len(data.get('primary_categories', {}))}")
    print(f"  Menu groups: {len(data.get('menu', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
