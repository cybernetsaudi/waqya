# Waqya SEO (Yoast-aligned)

## Automated (every publish)

| Field | Rule |
|-------|------|
| **Focus keyphrase** | Desk + topic tags + headline (`yoast_seo.suggest_focus_keyword`) |
| **SEO title** | `Keyword: Hook` — max 55 chars, keyphrase first |
| **Meta description** | 135–155 chars, keyphrase in opening |
| **Slug** | Includes keyphrase tokens when missing from headline slug |
| **Body** | Focus in ¶1, 3–5 uses, 2–3 `##` H2 subheadings |
| **Images** | Alt text: `{focus} — {headline}` |
| **Related + schema** | `seo.optimize_published_post` |

## Trust pages

`/editorial-policy/`, `/corrections/`, `/about/`, `/contact/` — Yoast meta set on create and via backfill.

## Backfill existing content

```bash
cd automation
python3 backfill_yoast_seo.py
```

Updates posts (Yoast title, meta, focus, slug, image alt, related block) and pages.

## Yoast checklist (what we target)

- Keyphrase in introduction, meta, SEO title, subheading, slug
- Keyphrase density ~3–5 per article
- SEO title width ≤55 characters
- Meta description 135–155 characters
- Image alt includes keyphrase words
- Readability: short paragraphs, transitions, sentence length (prompt-driven)
