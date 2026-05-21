"""
Editorial calendar hints — weekday focus injected into the generator.
"""

from __future__ import annotations

from datetime import datetime, timezone


def today_focus(config: dict) -> str:
    """Return a one-line editorial focus for the generator prompt."""
    cal = config.get("editorial_calendar", {})
    if not cal.get("enabled", True):
        return ""

    weekday = datetime.now(timezone.utc).strftime("%A").lower()
    schedule = cal.get("weekdays", {})
    focus = schedule.get(weekday, schedule.get("default", ""))
    if not focus:
        return ""
    return f"Editorial focus for today ({weekday.title()}): {focus}"
