"""
Image fetcher — hero + inline images for each article.

Strategy (relevance first, free only):
  1. Person death/tributes: source og:image or Wikipedia portrait of THAT person.
  2. Otherwise prefer source og:image as featured.
  3. Pexels with concrete visual queries (entities / places / desk scenes).
  Never use a random stock portrait for a named-person story.

Requires PEXELS_API_KEY in .env (not .env.example).
"""

from __future__ import annotations

import html
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin

import requests
import yaml

from image_dedup import (
    ImageBatchContext,
    fingerprint,
    is_image_used,
    is_source_url_used,
    mark_image_used,
)

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
USER_AGENT = "WaqyaBot/1.0 (+https://waqya.com)"

# Words that produce useless stock photos when used alone as search terms.
_STOP_VISUAL = {
    "a", "an", "the", "and", "or", "of", "in", "on", "to", "for", "with", "from",
    "is", "are", "was", "were", "be", "been", "being", "its", "it's", "this", "that",
    "when", "what", "why", "how", "who", "whom", "whose", "which", "will", "would",
    "could", "should", "can", "may", "might", "must", "not", "no", "yes", "just",
    "into", "over", "under", "after", "before", "about", "against", "between",
    "through", "during", "again", "further", "then", "once", "here", "there",
    "all", "each", "few", "more", "most", "other", "some", "such", "than", "too",
    "very", "s", "t", "don", "now", "new", "says", "said", "amid", "raises",
    "fears", "raises", "challenge", "impossible", "becomes", "again", "first",
    "price", "cut", "got", "just", "pack", "capable", "story", "news", "latest",
    "update", "explainer", "analysis", "commentary", "opinion", "breaking",
    "instability", "impact", "crisis", "concern", "concerns", "warning",
    "warnings", "threat", "threats", "risk", "risks", "hope", "hopes",
    "regional", "global", "major", "massive", "sudden", "growing", "rising",
}

# Desk → concrete scene phrases Pexels handles well.
_DESK_SCENES: dict[str, list[str]] = {
    "middle-east": [
        "Middle East city skyline dusk",
        "Arabic street market crowd",
        "desert highway border checkpoint",
    ],
    "south-asia": [
        "South Asia city monsoon street",
        "New Delhi parliament building",
        "Karachi harbor shipping",
    ],
    "united-kingdom": [
        "London parliament Big Ben",
        "UK politics Downing Street",
        "British newspaper newsroom",
    ],
    "united-states": [
        "Washington DC Capitol building",
        "White House exterior day",
        "US flag congress hearing",
    ],
    "war-conflict": [
        "soldiers military convoy desert",
        "damaged city buildings conflict",
        "military checkpoint border",
    ],
    "diplomacy": [
        "diplomats handshake summit table",
        "UN general assembly hall",
        "flags international summit",
    ],
    "technology-ai": [
        "server room data center lights",
        "circuit board microchip closeup",
        "AI robot hand computer screen",
    ],
    "markets-finance": [
        "stock exchange trading floor",
        "Wall Street stock tickers",
        "financial charts laptop desk",
    ],
    "business-economy": [
        "container ship cargo port",
        "office skyline business district",
        "factory production line workers",
    ],
    "health-medicine": [
        "hospital corridor doctors",
        "medical laboratory microscope",
        "vaccine syringe sterile tray",
    ],
    "climate-environment": [
        "flooded street climate disaster",
        "smoke pollution industrial plant",
        "solar panels renewable energy",
    ],
    "fashion-style": [
        "runway fashion show models",
        "designer clothing boutique rack",
        "fashion week street style",
    ],
    "entertainment-arts": [
        "film camera cinema set",
        "concert stage lights crowd",
        "retro gaming console desk",
    ],
    "politics-government": [
        "parliament assembly chamber",
        "ballot box election voting",
        "government building columns",
    ],
    "science": [
        "laboratory research scientist",
        "telescope observatory night sky",
        "particle physics experiment",
    ],
}


@dataclass
class FetchedImage:
    data: bytes
    filename: str
    mime_type: str
    alt_text: str
    credit: str
    pexels_id: Optional[int] = None
    wp_media_id: Optional[int] = None
    wp_url: Optional[str] = None


@dataclass
class ArticleImages:
    featured: Optional[FetchedImage] = None
    inline: list[FetchedImage] = field(default_factory=list)


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _download(url: str, timeout: int = 25) -> Optional[bytes]:
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        if len(resp.content) < 1024:
            return None
        return resp.content
    except Exception:
        log.exception("Image download failed: %s", url)
        return None


def _pexels_key() -> str:
    return os.environ.get("PEXELS_API_KEY", "").strip()


def _clean_query(text: str, *, max_words: int = 6) -> str:
    """Short, safe search string for stock photo APIs."""
    text = html.unescape(re.sub(r"<[^>]+>", "", text or ""))
    text = re.sub(r"[^\w\s'-]", " ", text)
    words = [w for w in text.split() if w and w.lower() not in _STOP_VISUAL]
    return " ".join(words[:max_words]) if words else ""


def _extract_entities(headline: str, tags: list[str]) -> list[str]:
    """Pull likely place/person/org nouns for photo search."""
    out: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        q = _clean_query(raw, max_words=4)
        key = q.lower()
        if len(q) < 3 or key in seen:
            return
        # Drop leftover abstract singletons after stop-word stripping.
        toks = key.split()
        if len(toks) == 1 and (toks[0] in _STOP_VISUAL or len(toks[0]) < 4):
            return
        if all(t in _STOP_VISUAL for t in toks):
            return
        seen.add(key)
        out.append(q)

    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", headline or ""):
        phrase = m.group(1)
        # Skip capitalized verbs / fillers at start of title-case sentence fragments.
        first = phrase.split()[0].lower()
        if first in _STOP_VISUAL or first.endswith("ing"):
            if " " not in phrase:
                continue
            phrase = " ".join(phrase.split()[1:])
        add(phrase)

    for tag in tags or []:
        if " " in tag or tag[:1].isupper() or "-" not in tag:
            add(tag)

    return out[:8]


def _desk_scenes(desk: str) -> list[str]:
    if not desk:
        return []
    key = desk.strip().lower().replace("_", "-")
    return list(_DESK_SCENES.get(key, []))


def _build_visual_queries(
    headline: str,
    image_query: str,
    tags: list[str],
    desk: str,
    *,
    count: int,
) -> list[str]:
    """Concrete, distinct Pexels queries ordered by expected relevance."""
    queries: list[str] = []
    seen: set[str] = set()

    def add(q: str) -> None:
        q = (q or "").strip()[:80]
        key = q.lower()
        if not q or key in seen:
            return
        # Reject overly abstract single words.
        words = key.split()
        if len(words) == 1 and words[0] in _STOP_VISUAL:
            return
        seen.add(key)
        queries.append(q)

    llm_q = _clean_query(image_query, max_words=5)
    if llm_q:
        add(llm_q)
        add(f"{llm_q} documentary")

    for ent in _extract_entities(headline, tags):
        add(ent)
        add(f"{ent} news")

    for scene in _desk_scenes(desk):
        add(scene)

    head = _clean_query(headline, max_words=5)
    if head:
        add(head)

    # Pad with related desk scenes if still short.
    for scene in _desk_scenes(desk):
        if len(queries) >= count:
            break
        add(f"{scene} editorial")

    if not queries:
        add("world news journalism")

    return queries[: max(count, 6)]



_PERSON_STORY_RE = re.compile(
    r"\b("
    r"dies?|died|passes?\s+away|passed\s+away|obituar|"
    r"tributes?\s+paid|funeral|mourning|grief for|in\s+memoriam|"
    r"killed|assassinated|late\s+[A-Z]|"
    r"death(?!\s+sentence|\s+toll|\s+row)"
    r")\b",
    re.I,
)

_GENERIC_NAME_BITS = {
    "Death", "Grief", "Nation", "System", "Icon", "Attention", "Collective",
    "Reflection", "Tribute", "Tributes", "Presenter", "Senator", "Former",
    "Emir", "Global", "Huge", "Crowds", "Street", "Streets", "Future",
}


def _html_unescape_url(url: str) -> str:
    return html.unescape((url or "").replace("&#038;", "&")).strip()


def detect_person_subjects(headline: str, tags: list[str] | None = None) -> list[str]:
    """Named people who must appear in the hero when the story is about them."""
    headline = html.unescape(headline or "")
    if not _PERSON_STORY_RE.search(headline) and not re.search(
        r"\bDeath\b|\bDies\b|\bFuneral\b", headline
    ):
        return []

    subjects: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        name = re.sub(r"\s+", " ", (name or "").strip(" ,.—–-'\"")).strip()
        name = re.sub(r"['’]s$", "", name)
        if len(name.split()) < 2 and len(name) < 5:
            return
        if any(bit.lower() == name.lower() for bit in _GENERIC_NAME_BITS):
            return
        key = name.lower()
        if key in seen or len(name) < 4:
            return
        toks = [t for t in re.findall(r"[A-Za-z]+", name) if t.lower() not in _STOP_VISUAL]
        if not toks or all(t in _GENERIC_NAME_BITS for t in toks):
            return
        seen.add(key)
        subjects.append(name)

    for pat in (
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,4})['’]s\s+(?:Death|Funeral|Legacy)",
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){0,3})['’]s\s+funeral\b",
        r"(?:Death|Deaths|Funeral|Obituary|Tributes?(?:\s+paid)?(?:\s+to)?)\s+(?:of\s+|to\s+)?"
        r"(?:TV presenter\s+|US Senator\s+|Senator\s+|actor\s+)?"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,4})",
        r"(Sheikh\s+[A-Z][a-z]+(?:\s+(?:bin|ibn|al|Al|von|de|da|van)\s+[A-Z][a-z]+)+)",
        r"(?:US Senator|Senator|President|King|Queen|Prime Minister)\s+"
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,3})\s+(?:dies|died|passes|passed)",
        r"\b((?:[A-Z][a-z]+\s+){1,2}[A-Z][a-z]+)\s+dies\b",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z'\-]+){1,3})\s*[:—–-]",
    ):
        for m in re.finditer(pat, headline):
            add(m.group(m.lastindex or 1))

    for tag in tags or []:
        if re.search(r"\s", tag) and tag[:1].isupper():
            add(tag)

    return subjects[:3]


def _subject_tokens(name: str) -> list[str]:
    return [
        t.lower()
        for t in re.findall(r"[A-Za-z]+", name)
        if len(t) >= 3 and t.lower() not in _STOP_VISUAL and t not in _GENERIC_NAME_BITS
    ]


def _photo_matches_subject(photo: dict, subjects: list[str]) -> bool:
    if not subjects:
        return True
    hay = " ".join(
        [
            (photo.get("alt") or ""),
            (photo.get("url") or ""),
            (photo.get("photographer") or ""),
        ]
    ).lower()
    for name in subjects:
        toks = _subject_tokens(name)
        if not toks:
            continue
        if toks[-1] in hay:
            return True
        if len(toks) >= 2 and all(t in hay for t in toks[-2:]):
            return True
    return False


def _photo_relevance(photo: dict, query: str) -> int:
    """Score how well a Pexels result matches the search intent."""
    hay = " ".join(
        [
            (photo.get("alt") or ""),
            (photo.get("url") or ""),
            " ".join(photo.get("tags") or []) if isinstance(photo.get("tags"), list) else "",
        ]
    ).lower()
    score = 0
    for token in re.findall(r"[a-z0-9]+", (query or "").lower()):
        if len(token) < 3 or token in _STOP_VISUAL:
            continue
        if token in hay:
            score += 2
    if any(w in hay for w in ("street", "building", "city", "soldier", "flag", "crowd", "protest")):
        score += 1
    if any(w in hay for w in ("selfie", "studio backdrop", "fashion model")):
        score -= 2
    return score


def _photo_to_image(
    photo: dict,
    idx: int,
    query: str,
    *,
    exclude_pexels: set[str] | None = None,
    allow_reuse: bool = False,
) -> Optional[FetchedImage]:
    pexels_id = photo.get("id")
    if pexels_id is not None:
        pid = str(pexels_id)
        if exclude_pexels and pid in exclude_pexels:
            return None
        if not allow_reuse and is_image_used(pexels_id=pexels_id):
            return None

    src = photo.get("src", {}).get("large") or photo.get("src", {}).get("medium")
    if not src:
        return None
    data = _download(src)
    if not data:
        return None
    if not allow_reuse and is_image_used(data, pexels_id=pexels_id):
        return None

    photographer = html.escape(photo.get("photographer") or "Pexels")
    link = photo.get("url") or "https://www.pexels.com"
    credit = (
        f'Photo: <a href="{html.escape(link, quote=True)}" '
        f'rel="noopener noreferrer" target="_blank">{photographer}</a> / Pexels'
    )
    alt = (photo.get("alt") or query or "News photo").strip()[:120]
    return FetchedImage(
        data=data,
        filename=f"image-{idx}.jpg",
        mime_type="image/jpeg",
        alt_text=alt,
        credit=credit,
        pexels_id=int(pexels_id) if pexels_id is not None else None,
    )


def _pexels_search(
    query: str,
    per_page: int = 4,
    start_page: int = 1,
    max_pages: int = 4,
    *,
    exclude_pexels: set[str] | None = None,
    require_subjects: list[str] | None = None,
    allow_reuse: bool = False,
) -> list[FetchedImage]:
    api_key = _pexels_key()
    if not api_key or not query:
        if not api_key:
            log.warning("PEXELS_API_KEY not set")
        return []

    candidates: list[tuple[int, dict]] = []
    try:
        for page in range(start_page, start_page + max_pages):
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                params={
                    "query": query,
                    "per_page": min(15, max(per_page * 3, 12)),
                    "page": page,
                    "orientation": "landscape",
                },
                headers={"Authorization": api_key},
                timeout=20,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                break
            for photo in photos:
                if require_subjects and not _photo_matches_subject(photo, require_subjects):
                    continue
                candidates.append((_photo_relevance(photo, query), photo))
            if len(candidates) >= per_page * 4:
                break

        candidates.sort(key=lambda x: x[0], reverse=True)
        out: list[FetchedImage] = []
        for _score, photo in candidates:
            if len(out) >= per_page:
                break
            img = _photo_to_image(
                photo,
                len(out) + 1,
                query,
                exclude_pexels=exclude_pexels,
                allow_reuse=allow_reuse,
            )
            if img:
                out.append(img)
        return out
    except Exception:
        log.exception("Pexels search failed: %s", query)
        return []


def _from_wikipedia(subject: str) -> Optional[FetchedImage]:
    """Public-figure portrait via Wikipedia REST (correct for obituaries)."""
    if not subject:
        return None
    title = subject.strip().replace(" ", "_")
    try:
        resp = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=12,
        )
        if resp.status_code == 404:
            short = re.sub(
                r"^(Sheikh|Senator|Sir|Dr|President|King|Queen)\s+",
                "",
                subject,
                flags=re.I,
            ).strip()
            if short != subject:
                return _from_wikipedia(short)
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("type") == "disambiguation":
            return None
        thumb = data.get("originalimage") or data.get("thumbnail") or {}
        image_url = thumb.get("source")
        if not image_url:
            return None
        raw = _download(image_url, timeout=20)
        if not raw:
            return None
        page_url = (data.get("content_urls") or {}).get("desktop", {}).get("page") or (
            f"https://en.wikipedia.org/wiki/{title}"
        )
        safe = html.escape(page_url, quote=True)
        display = html.escape(data.get("title") or subject)
        return FetchedImage(
            data=raw,
            filename="wikipedia-portrait.jpg",
            mime_type="image/jpeg",
            alt_text=f"{data.get('title') or subject} portrait",
            credit=(
                f'Photo: <a href="{safe}" rel="noopener noreferrer" target="_blank">'
                f"{display}</a> / Wikipedia"
            ),
        )
    except Exception:
        log.exception("Wikipedia image failed for %s", subject)
        return None


def _from_og_image(page_url: str, *, allow_reuse: bool = False) -> Optional[FetchedImage]:
    page_url = _html_unescape_url(page_url)
    if not page_url or page_url.rstrip("/").endswith("waqya.com"):
        return None
    try:
        resp = requests.get(page_url, timeout=15, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        page_html = resp.text[:500_000]
    except Exception:
        return None

    for pat in (
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    ):
        m = re.search(pat, page_html, re.I)
        if not m:
            continue
        image_url = urljoin(page_url, html.unescape(m.group(1).strip()))
        lower = image_url.lower()
        if any(x in lower for x in ("logo", "favicon", "sprite", "1x1", "pixel")):
            continue
        data = _download(image_url)
        if not data:
            continue
        if not allow_reuse and (is_image_used(data) or is_source_url_used(image_url)):
            continue
        safe_url = html.escape(page_url, quote=True)
        return FetchedImage(
            data=data,
            filename="featured.jpg",
            mime_type="image/jpeg",
            alt_text="Story image from source",
            credit=(
                f'Source: <a href="{safe_url}" rel="noopener noreferrer" '
                f'target="_blank">original report</a>'
            ),
        )
    return None


def fetch_article_images(
    headline: str,
    image_query: str,
    source_url: str,
    tags: list[str] | None = None,
    *,
    desk: str = "",
    exclude_pexels: set[str] | None = None,
    batch_ctx: ImageBatchContext | None = None,
    allow_reuse: bool = False,
) -> ArticleImages:
    """
    Fetch 1 featured + N inline images.

    Editorial rule: person death/tributes stories must use that person's photo
    (source og:image or Wikipedia) — never a random stock portrait.
    """
    config = _load_config()
    img_cfg = config.get("images", {})
    if not img_cfg.get("enabled", True):
        return ArticleImages()

    inline_count = int(img_cfg.get("inline_count", 3))
    total_needed = 1 + inline_count
    prefer_og = bool(img_cfg.get("prefer_og_featured", True))
    use_wikipedia = bool(img_cfg.get("wikipedia_portraits", True))
    tag_list = list(tags or [])
    subjects = detect_person_subjects(headline, tag_list)
    person_led = bool(subjects)

    queries = _build_visual_queries(
        headline,
        image_query,
        tag_list,
        desk,
        count=max(total_needed + 2, 8),
    )
    if person_led:
        person_queries: list[str] = []
        for name in subjects:
            person_queries.extend([f"{name} portrait", f"{name} official", name])
        queries = person_queries + [q for q in queries if q not in person_queries]

    collected: list[FetchedImage] = []
    merged_exclude: set[str] = set(exclude_pexels or set())
    if batch_ctx:
        merged_exclude |= batch_ctx.exclude_pexels

    def _add(img: FetchedImage) -> bool:
        fp = fingerprint(img.data)
        if batch_ctx and batch_ctx.is_session_duplicate(img.data):
            return False
        if fp in {fingerprint(x.data) for x in collected}:
            return False
        collected.append(img)
        if batch_ctx:
            batch_ctx.reserve(img)
        if img.pexels_id is not None:
            merged_exclude.add(str(img.pexels_id))
        return True

    if prefer_og or person_led:
        og = _from_og_image(source_url, allow_reuse=allow_reuse or person_led)
        if og:
            if subjects:
                og.alt_text = f"{subjects[0]} — story image from source"
            if og and _add(og):
                log.info(
                    "Featured from source og:image for '%s'%s",
                    headline[:50],
                    f" (subject: {subjects[0]})" if subjects else "",
                )

    if person_led and use_wikipedia and not collected:
        for name in subjects:
            wiki = _from_wikipedia(name)
            if wiki and _add(wiki):
                log.info("Featured Wikipedia portrait for subject '%s'", name)
                break

    for i, q in enumerate(queries):
        if len(collected) >= total_needed:
            break
        need = total_needed - len(collected)
        require_subject = person_led and not collected
        batch = _pexels_search(
            q,
            per_page=max(need, 2),
            start_page=1 + (i % 3),
            max_pages=3 if person_led else 4,
            exclude_pexels=merged_exclude,
            require_subjects=subjects if require_subject else None,
            allow_reuse=allow_reuse,
        )
        for img in batch:
            if len(collected) >= total_needed:
                break
            _add(img)

    if person_led and not collected and use_wikipedia:
        for name in subjects:
            wiki = _from_wikipedia(name)
            if wiki and _add(wiki):
                break

    if len(collected) < total_needed and not prefer_og and not person_led:
        og = _from_og_image(source_url, allow_reuse=allow_reuse)
        if og:
            _add(og)

    result = ArticleImages()
    if collected:
        result.featured = collected[0]
        result.inline = collected[1 : 1 + inline_count]
        for img in collected:
            mark_image_used(img.data, img.pexels_id, context=headline[:120])
        log.info(
            "Images for '%s': 1 featured + %d inline (person=%s queries=%s)",
            headline[:50],
            len(result.inline),
            subjects[0] if subjects else "-",
            "; ".join(queries[:4]),
        )
    else:
        log.warning("No images found for: %s", headline)
    return result


def fetch_featured_image(
    headline: str,
    image_query: str,
    source_url: str,
    tags: list[str] | None = None,
) -> Optional[FetchedImage]:
    images = fetch_article_images(headline, image_query, source_url, tags)
    return images.featured
