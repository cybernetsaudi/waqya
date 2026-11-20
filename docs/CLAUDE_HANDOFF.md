# Waqya — Claude handoff (read this first)

**Owner:** Waqas  
**Site:** https://waqya.com  
**Repo:** local folder `/Users/waqas/waqya` → GitHub `cybernetsaudi/waqya` (`main`)  
**Role of the agent:** dedicated engineering agent for the Waqya automated news commentary system. Audit first; implement only what the owner prioritizes. Do not rewrite the UI unless asked. Never paste secrets (`APP`/API keys, DB passwords, full `.env`, WP app passwords).

---

## What this project is

Waqya is an **AI commentary / analysis news site** (not a wire rewrite farm by intent). Pipeline:

1. Gather stories (RSS + optional NewsAPI / focus queries)  
2. Dedup (`automation/seen.db`)  
3. Generate commentary via LLM (`automation/generator.py`, `llm_client.py`)  
4. Quality gate → WordPress publish (`publisher.py`)  
5. Optional social + syndication  

**CMS:** WordPress on **Hostinger**  
**Automation:** Python under `automation/`, scheduled by **GitHub Actions** (`.github/workflows/pipeline.yml`)  
**Theme:** `wordpress/theme/waqya/`  
**Taxonomy source of truth:** `automation/waqya_categories.yaml`

---

## Live infrastructure

| Piece | Detail |
|-------|--------|
| App URL | `https://waqya.com` |
| WP REST | `/wp-json/wp/v2/…` (creds in local `.env` + GH secrets) |
| Host | Hostinger shared hosting |
| SSH | `ssh hostinger` (host, port and user live only in `~/.ssh/config` — this repo is public) |
| SSH alias | `Host hostinger` in `~/.ssh/config`, key `~/.ssh/hostinger_key` |
| Live WP root | `~/domains/waqya.com/public_html/` |
| Live theme | `~/domains/waqya.com/public_html/wp-content/themes/waqya/` |
| Secrets | Local `.env` (never commit). GitHub Actions secrets for pipeline. `.env.example` is placeholders only. |

**Theme deploy (safe):**

```bash
# Backup first
ssh hostinger 'cp -a ~/domains/waqya.com/public_html/wp-content/themes/waqya ~/domains/waqya.com/public_html/wp-content/themes/waqya.bak-$(date +%Y%m%d-%H%M%S)'

# NEVER use rsync --delete on this theme (local/remote trees have differed; --delete wiped assets once)
rsync -avz -e ssh \
  wordpress/theme/waqya/ \
  hostinger:domains/waqya.com/public_html/wp-content/themes/waqya/

ssh hostinger 'cd ~/domains/waqya.com/public_html && wp cache flush; wp litespeed-purge all'
```

If SSH fails, check the IP in `~/.ssh/config` against hPanel — Hostinger has changed it before.

---

## Intentional operating constraints (do not undo casually)

As of handoff (Nov 2026 context; last major throttle commit ~Sep 2026 `e32c683`):

1. **Volume capped for Gemini free tier**  
   - Cron: `15 5,13,21 * * *` (3×/day), not every 4h  
   - `pipeline.max_articles_per_run: 2`  
   - LLM **Groq primary** (body + headline), Gemini fallback only  
   - Groq models: `openai/gpt-oss-120b` / `openai/gpt-oss-20b` (old Llama IDs are dead on Groq)  
   - `on_the_record.enabled: false`

2. **Bluesky paused (spam label)**  
   - `@waqya.bsky.social` got a Bluesky **spam** label after ~1200 posts / ~7 followers  
   - `social.bluesky.enabled: false`  
   - After appeal clears: enable with `max_posts_per_day: 1`, keep promos off  
   - Telegram: live but capped (`max_posts_per_day: 3`, `max_posts_per_run: 1`, join CTAs off)

3. **AdSense slots OFF until measurable sessions**  
   - Head script + `/ads.txt` live (`ca-pub-7582233404244373`)  
   - `waqya_adsense_slots_enabled` defaults **false** — no in-article units yet  
   - See `docs/ADSENSE.md`  
   - Do **not** turn on Auto ads / empty inventory while traffic ≈ 0

4. **Strategy honesty**  
   - This is a **content factory**, not yet a media business. Distribution was near-zero (Telegram 1–2 views; Bluesky spam).  
   - Prefer **focus desks** + quality over firehose volume. Google treats undifferentiated AI scale as a risk.  
   - Owner was told: monetize/mainstream is unlikely on current trajectory without niche + audience + human-edited top pieces.

---

## Important bugs / fixes already landed

| Issue | Fix |
|-------|-----|
| Categories with `&` (e.g. Technology & AI) → Uncategorized | `publisher._get_or_create_category` is **slug-first**; WP `search=` breaks on `&` |
| Metaphorical “war” titles → War desk | Removed bare `war` keyword; tightened fallback signals in `taxonomy.py` |
| ~999 Uncategorized posts | Backfilled with `automation/recategorize_uncategorized.py` → Uncategorized count hit **0** |
| Subject-aware heroes | `image_fetcher.py`: prefer OG → Wikipedia portraits → Pexels; config `prefer_og_featured`, `wikipedia_portraits` |
| Focus mode dates | Refreshed in `config.yaml` (check `focus_mode.start_date` / `end_date` — may need another refresh if expired) |
| Groq 404s | Migrated off deprecated `llama-3.3-70b-versatile` / `llama-3.1-8b-instant` |

---

## Key files

```
automation/
  pipeline.py          # orchestrator
  config.yaml          # knobs (volume, LLM, social, focus, images, syndication)
  gatherer.py / sources.py / dedup.py
  generator.py / llm_client.py / quality_gate.py
  publisher.py / taxonomy.py / waqya_categories.yaml
  image_fetcher.py / backfill_images.py / image_dedup.py
  social_poster.py     # Bluesky / Mastodon / Telegram
  syndication.py / linkedin_*.py
  recategorize_uncategorized.py
wordpress/theme/waqya/ # live theme source
wordpress/site-assets/ads.txt
.github/workflows/pipeline.yml
docs/                  # ADSENSE, SOCIAL, SEO, SETUP, SYNDICATION, PRIVACY, …
```

Useful docs: `docs/ADSENSE.md`, `docs/SOCIAL.md`, `docs/SETUP.md`, `docs/GOOGLE_PUBLISHER.md`, `docs/EDITORIAL_ROADMAP.md`.

---

## Secrets / services (names only)

Expect in `.env` / GH secrets: `GEMINI_API_KEY`, `GROQ_API_KEY`, `NEWSAPI_KEY`, `WP_URL`, `WP_USER`, `WP_APP_PASSWORD`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_CHANNEL_ID`, `PEXELS_API_KEY`, `BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, optional Mastodon/LinkedIn/Medium/IndexNow.

LinkedIn syndication scaffolding exists; **tokens were never completed** → syndication stays 0 until OAuth secrets are set.

---

## How to operate day-to-day

```bash
# Manual pipeline
gh workflow run "Waqya News Pipeline" --ref main
gh run list --workflow="Waqya News Pipeline" --limit 5

# Local one-off (from repo root, with .env loaded)
cd automation && python pipeline.py

# Recategorize leftovers if Uncategorized creeps back
cd automation && python recategorize_uncategorized.py --limit 250
```

Quality gate: `publish_mode: quality_gated`, `require_min_quality_score: 78`.

---

## Known open work / owner decisions pending

- [ ] Bluesky spam appeal (owner); then re-enable at 1/day  
- [ ] Gemini **billing** if quality/volume must rise above free-tier  
- [ ] AdSense account status + payment profile (owner); slots only after real sessions  
- [ ] Refresh `focus_mode` dates if window expired  
- [ ] LinkedIn OAuth if company-page syndication wanted  
- [ ] Hostinger SSH works again — use it; never `--delete` rsync casually  
- [ ] Audience/niche strategy still the real blocker — engineering cannot invent traffic  

---

## Agent working rules

- Prefer small, reversible changes; backup theme before deploy.  
- Commit only when the owner asks (or when they say “ship/do it” for a clear ship recommendation).  
- Do not force-push `main`. Do not change DNS. Do not HTTP-hit destructive docroot scripts.  
- Do not re-enable Bluesky blast posting or AdSense slots “to help growth” without owner OK + evidence.  
- When asked for status: be critical — hide nothing (ops health ≠ business health).

---

## First actions for a new agent session

1. Read this file + `automation/config.yaml` + latest `git log -15`.  
2. Check live: recent posts, Uncategorized count, news sitemap, GH Actions last run.  
3. Confirm SSH `hostinger` still works before any theme deploy.  
4. Ask the owner what outcome they want next (ops fix vs growth vs monetization) — don’t assume volume = success.
