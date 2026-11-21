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
            lines.append(
                f"Desk scheduling note for {weekday.title()} (context only): {focus}. "
                "This note is about which desks are prioritised today. Do not let it "
                "change this article's subject, tone, vocabulary or metaphors; write "
                "in the register of the story's own desk."
            )

    return "\n".join(lines)
