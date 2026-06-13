# Waqya SEO (Yoast) playbook

## Common blunders (and fixes)

| Symptom in Yoast | Root cause | Fix |
|------------------|------------|-----|
| “No focus keyphrase” while REST shows meta | Editor/indexable not synced after API save | `waqya-yoast-sync.php` + re-open post or run backfill |
| Stacked “is at the centre of this story” in lede | Backfill ran `optimize_post_html()` multiple times | `clean_seo_artifacts()` before optimize (idempotent) |
| Duplicate “Analysis and context…” in meta | `build_meta_description()` appended suffix twice | Dedupe suffix in `yoast_seo.py` |
| SEO title `AI disarmament: … Disarmament…` | Keyphrase prepended when headline already contains tokens | `build_seo_title()` token check |
| Red score despite meta set | Yoast analysis uses **empty** sidebar keyphrase | Sync meta; content must have keyphrase in **first main** `<p>` (not aside) |

## What Yoast checks on posts

| Check | How we satisfy it |
|-------|-------------------|
| Focus keyphrase set | `suggest_focus_keyword()` → `_yoast_wpseo_focuskw` |
| Keyphrase in SEO title | `build_seo_title()` — keyphrase first or headline already starts with it |
| Meta description 135–155 chars | `build_meta_description()` — keyphrase near start |
| Keyphrase in introduction | `content_seo.optimize_post_html()` — first `<p>` after the aside |
| Keyphrase density | 3+ mentions in body (subtle closing lines if needed) |
| Keyphrase in subheading | 2+ `<h2>` in main body (not only “The Waqya read”) |
| Keyphrase in slug | `build_post_slug()` prepends keyphrase tokens when missing |
| Image alt | Featured + inline via `build_image_alt()` |
| Previously used keyphrase | Backfill tracks `used_focus`; variants get a disambiguator |

## Headline style (engaging, not sleazy)

- Lead with **who / what changed**, not “You won’t believe…”
- Use tension: stakes, deadline, surprise policy shift
- SEO title can shorten the H1; keep keyphrase in the first 55 characters
- Example: `AI disarmament: Pope Leo's call before it's too late`

## Pipeline

1. **Generate** — `prompts/commentary.md` asks for `##` H2s and keyphrase in the lede
2. **Publish** — `publisher.py` runs `optimize_post_html()` before save
3. **Post-save** — `seo.optimize_published_post()` re-applies HTML + Yoast meta + related links + schema
4. **Backfill** — `python backfill_yoast_seo.py` (all posts) or `--post-id=2488` for one

```bash
cd automation
python3 backfill_yoast_seo.py --post-id=2488   # test one
python3 backfill_yoast_seo.py --limit=500      # all published posts
```

## After deploy

1. Rsync `wordpress/mu-plugins/waqya-yoast-sync.php` to Hostinger (same path as `waqya-smtp.php`).
2. Run full backfill: `python3 backfill_yoast_seo.py --limit=500` (≈3 min per 30 posts).
3. Open a post in wp-admin → Yoast panel → **Update SEO data** if scores look stale (caches analysis).
