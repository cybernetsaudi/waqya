"""
Diversity-aware story selection — avoids echo-chamber clustering.

- Entity caps: max 1 Trump / Iran / etc. per day on site (not just per run)
- Topic clusters: similar titles collapse; shared entities (trump, iran) always match
- Source URL: same wire story blocked even if headline changes
- Category quotas: spread picks across primary desks per run / per day
"""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

import requests

from taxonomy import suggest_primary_from_story
from url_utils import normalize_story_url, url_fingerprint

log = logging.getLogger(__name__)

STOPWORDS = frozenset(
    """
    a an the and or but in on at to for of is are was were be been being
    that this with from as by it its into over after before not no yes
    says said will can about up out new just more most other than when
    how what who which their they them his her she he we you your our
    has have had could would should may might also amid while during
    """.split()
)

GENERIC_TOKENS = frozenset(
    """
    news report reports latest update breaking global world international
    officials government minister president leader country countries
    people public health officials experts analysts say says told
    """.split()
)

# High-signal entities: one story per entity per day (trump fatigue, etc.)
ENTITY_TOKENS = frozenset(
    """
    trump biden harris netanyahu putin zelenskyy zelensky
    iran israel gaza hamas hezbollah yemen houthi
    china taiwan ukraine russia india pakistan
    nvidia tesla apple google openai
    hantavirus covid webb jwst
    """.split()
)

_SOURCE_LINK_RE = re.compile(
    r'class="source-attribution"[^>]*>.*?href="(https?://[^"]+)"',
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class DiversityConfig:
    enabled: bool = True
    max_per_cluster_per_run: int = 1
    max_per_primary_per_run: int = 2
    min_distinct_primaries_per_run: int = 3
    cluster_overlap_threshold: float = 0.35
    recent_hours: int = 72
    entity_window_hours: int = 24
    max_per_entity_per_day: int = 1
    hard_block_recent_clusters: bool = True
    trending_score_cap: float = 8.0
    saturation_penalty: float = 12.0
    primary_daily_cap: int = 3
    source_url_window_hours: int = 168


@dataclass
class SaturationState:
    clusters: list[frozenset[str]] = field(default_factory=list)
    entity_counts: Counter[str] = field(default_factory=Counter)
    primary_counts: Counter[str] = field(default_factory=Counter)
    source_urls: set[str] = field(default_factory=set)
    source_url_fps: set[str] = field(default_factory=set)


def load_diversity_config(config: dict) -> DiversityConfig:
    raw = config.get("pipeline", {}).get("diversity", {})
    return DiversityConfig(
        enabled=raw.get("enabled", True),
        max_per_cluster_per_run=int(raw.get("max_per_cluster_per_run", 1)),
        max_per_primary_per_run=int(raw.get("max_per_primary_per_run", 2)),
        min_distinct_primaries_per_run=int(raw.get("min_distinct_primaries_per_run", 3)),
        cluster_overlap_threshold=float(raw.get("cluster_overlap_threshold", 0.35)),
        recent_hours=int(raw.get("recent_hours", 72)),
        entity_window_hours=int(raw.get("entity_window_hours", 24)),
        max_per_entity_per_day=int(raw.get("max_per_entity_per_day", 1)),
        hard_block_recent_clusters=bool(raw.get("hard_block_recent_clusters", True)),
        trending_score_cap=float(raw.get("trending_score_cap", 8.0)),
        saturation_penalty=float(raw.get("saturation_penalty", 12.0)),
        primary_daily_cap=int(raw.get("primary_daily_cap", 3)),
        source_url_window_hours=int(raw.get("source_url_window_hours", 168)),
    )


def story_entities(title: str, summary: str = "") -> frozenset[str]:
    text = f"{title} {summary}".lower()
    found: set[str] = set()
    for ent in ENTITY_TOKENS:
        if re.search(rf"\b{re.escape(ent)}\b", text):
            found.add(ent)
    return frozenset(found)


def topic_tokens(title: str, summary: str = "") -> set[str]:
    text = f"{title} {summary}".lower()
    words = re.findall(r"[a-z][a-z0-9'-]{2,}", text)
    out: set[str] = set()
    for w in words:
        if w in STOPWORDS or w in GENERIC_TOKENS:
            continue
        if len(w) < 3:
            continue
        out.add(w)
    for m in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", f"{title} {summary}"):
        phrase = m.lower().replace(" ", "_")
        if phrase not in STOPWORDS:
            out.add(phrase)
    out |= set(story_entities(title, summary))
    return out


def cluster_key(title: str, summary: str = "") -> frozenset[str]:
    return frozenset(topic_tokens(title, summary))


def cluster_overlap(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def clusters_match(
    a: frozenset[str],
    b: frozenset[str],
    threshold: float,
) -> bool:
    ent_a = a & ENTITY_TOKENS
    ent_b = b & ENTITY_TOKENS
    if ent_a and ent_b and (ent_a & ent_b):
        return True
    if cluster_overlap(a, b) >= threshold:
        return True
    shared = a & b
    for tok in shared:
        if len(tok) >= 9:
            return True
    return False


def extract_source_url_from_html(html: str) -> str:
    if not html:
        return ""
    m = _SOURCE_LINK_RE.search(html)
    return m.group(1).strip() if m else ""


def fetch_saturation_state(div: DiversityConfig) -> SaturationState:
    """Recent WP posts: clusters, entity counts, published source URLs."""
    base = os.environ.get("WP_URL", "").rstrip("/")
    user = os.environ.get("WP_USER", "")
    password = os.environ.get("WP_APP_PASSWORD", "")
    state = SaturationState()
    if not base or not user or not password:
        return state

    cluster_after = datetime.now(timezone.utc) - timedelta(hours=div.recent_hours)
    entity_after = datetime.now(timezone.utc) - timedelta(hours=div.entity_window_hours)
    url_after = datetime.now(timezone.utc) - timedelta(hours=div.source_url_window_hours)
    cluster_iso = cluster_after.strftime("%Y-%m-%dT%H:%M:%S")

    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/posts",
            params={
                "per_page": 100,
                "status": "publish",
                "orderby": "date",
                "order": "desc",
                "after": cluster_iso,
                "_fields": "title,date,content,categories,meta",
            },
            auth=(user, password),
            timeout=25,
        )
        resp.raise_for_status()
        posts = resp.json()
    except Exception:
        log.exception("Could not fetch recent WP posts for diversity")
        return state

    slug_by_id = _wp_category_slug_map(base, (user, password))
    entity_after_dt = entity_after.replace(tzinfo=timezone.utc)
    url_after_dt = url_after.replace(tzinfo=timezone.utc)

    for post in posts:
        from html_utils import wp_plain_text

        title = wp_plain_text((post.get("title") or {}).get("rendered", ""))
        content = (post.get("content") or {}).get("rendered", "") or ""
        meta = post.get("meta") or {}
        if not isinstance(meta, dict):
            meta = {}

        pub = post.get("date", "")
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pub_dt = datetime.now(timezone.utc)

        if title:
            state.clusters.append(cluster_key(title))

        if pub_dt >= entity_after_dt:
            for ent in story_entities(title):
                state.entity_counts[ent] += 1

        if pub_dt >= url_after_dt:
            src = (meta.get("_waqya_source_url") or "").strip()
            if not src:
                src = extract_source_url_from_html(content)
            if src:
                norm = normalize_story_url(src)
                state.source_urls.add(norm)
                fp = url_fingerprint(src)
                if fp:
                    state.source_url_fps.add(fp)

        if pub_dt >= entity_after_dt:
            for cat_id in post.get("categories") or []:
                slug = slug_by_id.get(cat_id, "")
                if slug:
                    state.primary_counts[slug] += 1

    if state.entity_counts:
        log.info("WP entity saturation (%dh): %s", div.entity_window_hours, dict(state.entity_counts.most_common(8)))
    return state


def _wp_category_slug_map(base: str, auth: tuple[str, str]) -> dict[int, str]:
    try:
        resp = requests.get(
            f"{base}/wp-json/wp/v2/categories",
            params={"per_page": 100},
            auth=auth,
            timeout=15,
        )
        resp.raise_for_status()
        return {c["id"]: c.get("slug", "") for c in resp.json()}
    except Exception:
        return {}


def story_blocked(
    title: str,
    url: str,
    summary: str,
    div: DiversityConfig,
    saturation: SaturationState,
    *,
    run_clusters: list[frozenset[str]] | None = None,
    run_entity_counts: Counter[str] | None = None,
) -> str | None:
    """Return reason string if story must not be selected."""
    norm_url = normalize_story_url(url)
    fp = url_fingerprint(url)
    if norm_url and norm_url in saturation.source_urls:
        return "source_url_on_site"
    if fp and fp in saturation.source_url_fps:
        return "source_url_fp_on_site"

    ck = cluster_key(title, summary)
    entities = story_entities(title, summary)

    pools: list[list[frozenset[str]]] = []
    if run_clusters:
        pools.append(run_clusters)
    if div.hard_block_recent_clusters:
        pools.append(saturation.clusters)

    for pool in pools:
        for rc in pool:
            if clusters_match(ck, rc, div.cluster_overlap_threshold):
                return "cluster_saturated"

    for ent in entities:
        if saturation.entity_counts.get(ent, 0) >= div.max_per_entity_per_day:
            return f"entity_saturated:{ent}"
        if run_entity_counts and run_entity_counts.get(ent, 0) >= div.max_per_entity_per_day:
            return f"entity_run_cap:{ent}"

    return None


def adjusted_score(
    story: dict,
    div: DiversityConfig,
    saturation: SaturationState,
) -> float:
    score = float(story.get("trend_score", 0))
    score = min(score, div.trending_score_cap)

    primary = suggest_primary_from_story(
        story.get("title", ""),
        story.get("summary", ""),
        story.get("category"),
    )
    story["_suggested_primary"] = primary
    if saturation.primary_counts.get(primary, 0) >= div.primary_daily_cap:
        score -= div.saturation_penalty * 0.75

    if story.get("category") not in ("world", "current-affairs", ""):
        score += 2.0

    return score


def select_diverse_stories(
    candidates: list[dict],
    max_new: int,
    config: dict,
    *,
    skip_if_seen: Callable[..., bool],
) -> list[dict]:
    """
    Pick up to max_new stories with topic + category + entity diversity.
    skip_if_seen(title, url, summary='') -> True when already processed.
    """
    div = load_diversity_config(config)
    if not div.enabled or max_new <= 0:
        out = []
        for s in candidates:
            if skip_if_seen(s.get("title", ""), s.get("url", ""), s.get("summary", "")):
                continue
            out.append(s)
            if len(out) >= max_new:
                break
        return out

    saturation = fetch_saturation_state(div)

    scored: list[tuple[float, dict]] = []
    skipped = Counter()
    for story in candidates:
        title = story.get("title", "")
        url = story.get("url", "")
        summary = story.get("summary", "")
        if skip_if_seen(title, url, summary):
            skipped["seen_db"] += 1
            continue
        reason = story_blocked(title, url, summary, div, saturation)
        if reason:
            skipped[reason.split(":")[0]] += 1
            continue
        adj = adjusted_score(story, div, saturation)
        scored.append((adj, story))

    scored.sort(key=lambda x: x[0], reverse=True)

    selected: list[dict] = []
    otr_cfg = config.get("on_the_record", {})
    otr_max = int(otr_cfg.get("max_per_run", 0)) if otr_cfg.get("enabled") else 0
    run_clusters: list[frozenset[str]] = []
    run_primary_counts: Counter[str] = Counter()
    run_entity_counts: Counter[str] = Counter()

    def can_add(story: dict, primary: str) -> bool:
        if run_primary_counts[primary] >= div.max_per_primary_per_run:
            return False
        title = story.get("title", "")
        url = story.get("url", "")
        summary = story.get("summary", "")
        if story_blocked(
            title,
            url,
            summary,
            div,
            saturation,
            run_clusters=run_clusters,
            run_entity_counts=run_entity_counts,
        ):
            return False
        return True

    def record_pick(story: dict, primary: str) -> None:
        ck = cluster_key(story.get("title", ""), story.get("summary", ""))
        run_clusters.append(ck)
        run_primary_counts[primary] += 1
        for ent in story_entities(story.get("title", ""), story.get("summary", "")):
            run_entity_counts[ent] += 1

    if otr_max > 0:
        otr_picked = 0
        for _adj, story in scored:
            if story.get("story_format") != "on_the_record":
                continue
            if otr_picked >= otr_max or len(selected) >= max_new:
                break
            primary = story.get("suggested_primary") or story.get("_suggested_primary") or suggest_primary_from_story(
                story.get("title", ""),
                story.get("summary", ""),
                story.get("category"),
            )
            if not can_add(story, primary):
                continue
            selected.append(story)
            record_pick(story, primary)
            otr_picked += 1
            log.info("On The Record reserved: %s", story.get("title", "")[:60])
        if otr_picked:
            log.info("Reserved %d On The Record slot(s)", otr_picked)

    primaries_needed = min(div.min_distinct_primaries_per_run, max_new)
    by_primary: dict[str, list[tuple[float, dict]]] = {}
    for adj, story in scored:
        primary = story.get("_suggested_primary") or suggest_primary_from_story(
            story.get("title", ""),
            story.get("summary", ""),
            story.get("category"),
        )
        by_primary.setdefault(primary, []).append((adj, story))

    used_primaries: set[str] = set()
    for primary in sorted(
        by_primary.keys(),
        key=lambda p: (run_primary_counts[p], saturation.primary_counts.get(p, 0)),
    ):
        if len(used_primaries) >= primaries_needed:
            break
        if primary == "current-affairs" and len(used_primaries) < primaries_needed - 1:
            continue
        for _adj, story in by_primary[primary]:
            if can_add(story, primary):
                selected.append(story)
                record_pick(story, primary)
                used_primaries.add(primary)
                break

    selected_urls = {normalize_story_url(s.get("url", "")) for s in selected}
    for adj, story in scored:
        if len(selected) >= max_new:
            break
        norm = normalize_story_url(story.get("url", ""))
        if norm in selected_urls:
            continue
        if story.get("story_format") == "on_the_record" and otr_max > 0:
            otr_count = sum(1 for s in selected if s.get("story_format") == "on_the_record")
            if otr_count >= otr_max:
                continue
        primary = story.get("_suggested_primary") or suggest_primary_from_story(
            story.get("title", ""),
            story.get("summary", ""),
            story.get("category"),
        )
        if not can_add(story, primary):
            continue
        selected.append(story)
        selected_urls.add(norm)
        record_pick(story, primary)

    if skipped:
        log.info("Diversity skipped: %s", dict(skipped))
    if len(selected) < max_new:
        log.warning(
            "Diversity picked %d / %d — %d eligible after filters",
            len(selected),
            max_new,
            len(scored),
        )
    if selected:
        log.info(
            "Diversity pick: %d stories, primaries=%s, run_entities=%s",
            len(selected),
            dict(run_primary_counts),
            dict(run_entity_counts),
        )
    return selected[:max_new]


def select_diverse_fallback(
    candidates: list[dict],
    need: int,
    *,
    skip_if_seen: Callable[..., bool] | None = None,
    exclude_urls: set[str] | None = None,
) -> list[dict]:
    """
    When strict diversity picks nothing, fill from top-scored candidates.
    Skips WP saturation / cluster blocks; only blocks URLs already published.
    """
    if need <= 0:
        return []

    from dedup import is_url_seen
    from url_utils import normalize_story_url

    exclude_norm = {normalize_story_url(u) for u in (exclude_urls or set()) if u}
    scored = sorted(candidates, key=lambda c: float(c.get("trend_score", 0)), reverse=True)
    picked: list[dict] = []
    for story in scored:
        if len(picked) >= need:
            break
        url = story.get("url", "")
        norm = normalize_story_url(url)
        if norm and norm in exclude_norm:
            continue
        if is_url_seen(url):
            continue
        picked.append(story)
        exclude_norm.add(norm)

    return picked
