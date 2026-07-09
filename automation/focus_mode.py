"""
Editorial focus mode — temporarily bias gathering toward priority desks.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

log = logging.getLogger(__name__)


def focus_cfg(config: dict) -> dict:
    return config.get("focus_mode", {}) or {}


def focus_active(config: dict, *, today: date | None = None) -> bool:
    """True when focus_mode is enabled and within the configured date window."""
    cfg = focus_cfg(config)
    if not cfg.get("enabled"):
        return False

    today = today or datetime.now(timezone.utc).date()
    start_s = (cfg.get("start_date") or "").strip()
    end_s = (cfg.get("end_date") or "").strip()
    try:
        if start_s and today < date.fromisoformat(start_s):
            return False
        if end_s and today > date.fromisoformat(end_s):
            return False
    except ValueError:
        log.warning("focus_mode: invalid start_date/end_date — treating as inactive")
        return False
    return True


def focus_priority_desks(config: dict) -> list[str]:
    cfg = focus_cfg(config)
    desks = cfg.get("priority_desks") or []
    return [str(d).strip() for d in desks if str(d).strip()]


def focus_deprioritized_desks(config: dict) -> set[str]:
    cfg = focus_cfg(config)
    desks = cfg.get("deprioritized_desks") or []
    return {str(d).strip() for d in desks if str(d).strip()}


def focus_boost(config: dict) -> float:
    return float(focus_cfg(config).get("priority_boost", 6.0))


def focus_penalty(config: dict) -> float:
    return float(focus_cfg(config).get("deprioritize_penalty", 8.0))


def focus_topic_queries(config: dict) -> list[dict]:
    """Extra NewsAPI topic queries while focus mode is active."""
    if not focus_active(config):
        return []
    queries = focus_cfg(config).get("topic_queries") or []
    return [q for q in queries if isinstance(q, dict) and q.get("query")]


def focus_prompt_line(config: dict) -> str:
    """One-line hint for the article generator."""
    if not focus_active(config):
        return ""
    desks = focus_priority_desks(config)
    if not desks:
        return ""
    labels = ", ".join(desks)
    end = (focus_cfg(config).get("end_date") or "").strip()
    until = f" (until {end})" if end else ""
    return (
        f"Editorial focus mode{until}: prefer depth on these desks — {labels}. "
        "If the story fits a focus desk, write with that desk's audience in mind."
    )


def apply_focus_score_adjustments(candidates: list[dict], config: dict) -> list[dict]:
    """Boost priority desks and penalize deprioritized desks on candidate trend_score."""
    if not focus_active(config) or not candidates:
        return candidates

    priority = set(focus_priority_desks(config))
    deprioritized = focus_deprioritized_desks(config)
    boost = focus_boost(config)
    penalty = focus_penalty(config)
    if not priority and not deprioritized:
        return candidates

    boosted = 0
    penalized = 0
    for c in candidates:
        primary = c.get("suggested_primary") or c.get("_suggested_primary") or ""
        score = float(c.get("trend_score", 0))
        if primary in priority:
            c["trend_score"] = score + boost
            boosted += 1
        elif primary in deprioritized:
            c["trend_score"] = max(0.0, score - penalty)
            penalized += 1

    log.info(
        "Focus mode scoring: +%.1f on %d priority, -%.1f on %d deprioritized (desks=%s)",
        boost,
        boosted,
        penalty,
        penalized,
        ",".join(sorted(priority)) or "none",
    )
    return candidates
