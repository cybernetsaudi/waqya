"""
Editorial calendar hints — weekday focus injected into the generator.
"""

from __future__ import annotations

from datetime import datetime, timezone


def today_focus(config: dict) -> str:
    """Return editorial focus lines for the generator prompt."""
    lines: list[str] = []

    from focus_mode import focus_prompt_line

    focus_line = focus_prompt_line(config)
    if focus_line:
        lines.append(focus_line)

    cal = config.get("editorial_calendar", {})
    if cal.get("enabled", True):
        weekday = datetime.now(timezone.utc).strftime("%A").lower()
        schedule = cal.get("weekdays", {})
        focus = schedule.get(weekday, schedule.get("default", ""))
        if focus:
            lines.append(f"Editorial focus for today ({weekday.title()}): {focus}")

    return "\n".join(lines)
