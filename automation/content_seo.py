"""
Post-publish HTML optimization for Yoast SEO checks.

Ensures focus keyphrase in introduction, density, H2 subheadings, and image alt text.
Idempotent: safe to run on backfill without stacking boilerplate.
"""

from __future__ import annotations

import re
from html import escape

from html_utils import wp_plain_text
from yoast_seo import build_image_alt, count_keyphrase

_SKIP_BLOCKS = re.compile(
    r"<aside[^>]*>.*?</aside>|<footer[^>]*>.*?</footer>|"
    r'<section[^>]*class="[^"]*waqya-related.*?</section>|'
    r"<script[^>]*>.*?</script>",
    re.I | re.S,
)

_INTRO_BOILERPLATE = re.compile(
    r"((?:[A-Za-zÀ-ÿ0-9][^.]{0,90}?\s+)?is at the centre of this story:\s*)+",
    re.I,
)

_DENSITY_SNIPPETS = (
    "That tension around {focus} is not going away.",
    "Observers say {focus} will shape the debate for months.",
    "The question is who benefits if {focus} dominates the agenda.",
)

_H2_TEMPLATES = (
    "Why {focus} matters now",
    "The stakes around {focus}",
    "What {focus} means next",
    "{focus}: what to watch",
)


def _focus_pattern(focus: str) -> re.Pattern[str]:
    focus = re.escape(focus.strip().lower())
    if " " in focus:
        return re.compile(re.escape(focus), re.I)
    return re.compile(rf"\b{focus}\b", re.I)


def _contains_focus(text: str, focus: str) -> bool:
    return bool(_focus_pattern(focus).search(wp_plain_text(text)))


def _main_body_html(html: str) -> str:
    return _SKIP_BLOCKS.sub("", html)


def _content_after_aside(html: str) -> tuple[str, int]:
    """Return (suffix after aside, byte offset in full html where suffix starts)."""
    m = re.search(r"<aside[^>]*>.*?</aside>\s*", html, re.I | re.S)
    if m:
        return html[m.end() :], m.end()
    return html, 0


def _first_main_paragraph_span(html: str) -> tuple[int, int, str] | None:
    """Byte span (start, end) and inner HTML of the first main-column paragraph."""
    suffix, offset = _content_after_aside(html)
    local = re.search(r"<p>(.*?)</p>", suffix, re.I | re.S)
    if not local:
        return None
    return offset + local.start(1), offset + local.end(1), local.group(1)


def clean_seo_artifacts(html: str, focus: str = "") -> str:
    """Remove stacked intro prefixes, auto H2s, and density filler from prior runs."""
    if not html:
        return html

    def clean_para_inner(inner: str) -> str:
        inner = _INTRO_BOILERPLATE.sub("", inner)
        inner = re.sub(
            r"^((?:[A-Za-zÀ-ÿ0-9][^.]{0,90}?\s+)?frames the debate here:\s*)+",
            "",
            inner,
            flags=re.I,
        )
        return inner.lstrip()

    span = _first_main_paragraph_span(html)
    if span:
        start, end, inner = span
        html = html[:start] + clean_para_inner(inner) + html[end:]

    if focus:
        for template in _H2_TEMPLATES:
            title = template.format(focus=focus)
            html = re.sub(
                rf"<h2>\s*{re.escape(title)}\s*</h2>\s*",
                "",
                html,
                flags=re.I,
            )
        for snippet in _DENSITY_SNIPPETS:
            line = snippet.format(focus=focus)
            html = re.sub(
                rf"<p>\s*{re.escape(line)}\s*</p>\s*",
                "",
                html,
                flags=re.I,
            )

    return html


def _inject_intro_keyphrase(first_para: str, focus: str) -> str:
    plain = wp_plain_text(first_para)
    plain = _INTRO_BOILERPLATE.sub("", plain).strip()
    if _contains_focus(plain, focus):
        return plain
    lead = focus[0].upper() + focus[1:] if focus else "This story"
    return f"{lead} frames the debate here: {plain}"


def _h2_with_focus(focus: str, variant: int = 0) -> str:
    title = _H2_TEMPLATES[variant % len(_H2_TEMPLATES)].format(focus=focus)
    return f"<h2>{escape(title)}</h2>"


def _count_body_h2(html: str) -> int:
    return len(re.findall(r"<h2[^>]*>", _main_body_html(html), re.I))


def _insert_body_h2s(html: str, focus: str, needed: int) -> str:
    if needed <= 0:
        return html

    parts = re.split(r"(</aside>)", html, maxsplit=1)
    if len(parts) >= 3:
        before, aside_end, after = parts[0], parts[1], parts[2]
    else:
        before, aside_end, after = "", "", html

    paragraphs = list(re.finditer(r"<p>.*?</p>", after, re.I | re.S))
    if len(paragraphs) < 3:
        return html

    insert_at = [min(1, len(paragraphs) - 1), min(3, len(paragraphs) - 1)]
    offset = 0
    inserted = 0
    for idx, h2_idx in enumerate(insert_at):
        if inserted >= needed:
            break
        if h2_idx >= len(paragraphs):
            continue
        m = paragraphs[h2_idx]
        pos = m.start() + offset
        h2 = _h2_with_focus(focus, idx) + "\n\n"
        after = after[:pos] + h2 + after[pos:]
        offset += len(h2)
        inserted += 1

    return before + aside_end + after


def _boost_keyphrase_density(html: str, focus: str, target_min: int = 3) -> str:
    plain = wp_plain_text(_SKIP_BLOCKS.sub(" ", html))
    current = count_keyphrase(plain, focus)
    if current >= target_min:
        return html

    additions = min(1, target_min - current)
    snippets = [s.format(focus=focus) for s in _DENSITY_SNIPPETS]
    snippet_html = "".join(f"<p>{escape(snippets[i % len(snippets)])}</p>" for i in range(additions))

    for marker in ('<p class="source-attribution"', "<footer", '<section class="waqya-related"'):
        pos = html.find(marker)
        if pos != -1:
            return html[:pos] + snippet_html + html[pos:]
    return html + snippet_html


def _fix_image_alts(html: str, focus: str, headline: str) -> str:
    def repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        alt_m = re.search(r'alt=["\']([^"\']*)["\']', tag, re.I)
        if alt_m and _contains_focus(alt_m.group(1), focus):
            return tag
        alt = escape(build_image_alt(focus, headline, "photo"))
        if re.search(r"\balt=", tag, re.I):
            return re.sub(r'alt=["\'][^"\']*["\']', f'alt="{alt}"', tag, count=1, flags=re.I)
        return tag.replace("<img ", f'<img alt="{alt}" ', 1)

    return re.sub(r"<img\b[^>]*>", repl, html, flags=re.I)


def _apply_first_paragraph(html: str, new_inner: str) -> str:
    span = _first_main_paragraph_span(html)
    if not span:
        return html
    start, end, _ = span
    return html[:start] + new_inner + html[end:]


def optimize_post_html(html: str, focus: str, headline: str) -> str:
    """Light SEO pass: image alt text only; preserve editorial voice."""
    if not html:
        return html

    if focus:
        html = clean_seo_artifacts(html, focus)

    html = _fix_image_alts(html, focus or headline[:40], headline)
    return html


def body_plain_word_count(html: str) -> int:
    return len(wp_plain_text(_SKIP_BLOCKS.sub(" ", html)).split())
