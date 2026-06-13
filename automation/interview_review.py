"""
On The Record — presidential / leader interview detection and tone selection.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

INTERVIEW_PATTERN = re.compile(
    r"\b(interview|interviews|interviewed|sit-?down|exclusive|one-on-one|"
    r"tells\s+(?:fox|cnn|nbc|abc|cbs|bbc|sky)|speaks\s+to|in\s+conversation\s+with)\b",
    re.I,
)

LEADER_PATTERN = re.compile(
    r"\b(trump|biden|harris|president|prime\s+minister|pm\s+|chancellor|"
    r"macron|starmer|modi|imran\s+khan|netanyahu)\b",
    re.I,
)

DEFAULT_TONES = (
    "critical",
    "contradiction",
    "skeptical",
    "encouraging",
    "wry",
)


def is_interview_story(story: dict[str, Any]) -> bool:
    if story.get("story_format") == "on_the_record":
        return True
    text = f"{story.get('title', '')} {story.get('summary', '')}"
    if not INTERVIEW_PATTERN.search(text):
        return False
    return bool(LEADER_PATTERN.search(text))


def pick_interview_tone(story: dict[str, Any], tones: list[str] | None = None) -> str:
    if story.get("interview_tone"):
        return str(story["interview_tone"])
    options = [t for t in (tones or DEFAULT_TONES) if t]
    if not options:
        options = list(DEFAULT_TONES)
    seed = f"{story.get('title', '')}|{story.get('url', '')}"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(options)
    return options[idx]


def annotate_interview_stories(stories: list[dict[str, Any]], config: dict) -> None:
    """Mark eligible stories for On The Record generation."""
    otr = config.get("on_the_record", {})
    if not otr.get("enabled", True):
        return
    tones = otr.get("tones") or list(DEFAULT_TONES)
    boost = float(otr.get("trend_score_boost", 4.0))
    for story in stories:
        if story.get("story_format") == "on_the_record" or is_interview_story(story):
            story["story_format"] = "on_the_record"
            story["interview_tone"] = pick_interview_tone(story, tones)
            story["trend_score"] = float(story.get("trend_score", 0)) + boost
            if not story.get("suggested_primary"):
                story["suggested_primary"] = otr.get("default_desk", "united-states")
