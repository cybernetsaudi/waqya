# Waqya Editorial Roadmap — Director Review

Strategic review saved for Waqya as a news/commentary agency. **Tier 1 is wired in code** (this sprint). Tiers 2–4 are planned for later.

---

## Executive summary (director view)

Waqya already runs a credible **gather → write → publish** machine with diversity, dedup, SEO, Telegram, and a strong theme. The next wins are **editorial product**, not more plumbing: trust (E-E-A-T), urgency (breaking lane), habit (homepage “Today”), and **gates** so automation does not become repetition or embarrassment.

**Go live with quality_gated publish:** high scores auto-publish; low scores stay draft and ping you on Telegram.

---

## What you already have (strong foundation)

- Automated pipeline on **GitHub Actions** (every 4 hours)
- **33+ editorial desks**, anti-echo diversity, image dedup
- **SEO** (schema, related links, sitemaps), Pexels images
- **Subscribers** (+Follow, digest), date filters on archives
- **Brand theme**, `llms.txt` / `ai.txt` for AI discovery

---

## Tier 1 — Implemented now

| # | Feature | Where |
|---|---------|--------|
| 1 | **Editorial quality gate** (0–100, draft below threshold) | `automation/quality_gate.py`, `config.yaml` → `pipeline.publish_mode` |
| 2 | **Breaking / Developing** (tag + homepage strip) | `breaking` config, homepage `waqya_render_developing_strip()` |
| 3 | **Trust & E-E-A-T** (desk byline, article footer, policy pages) | `setup_trust_pages.py`, theme footer/single, publisher HTML |
| 4 | **Telegram workflow** (live vs held + scores) | `notifier.notify_pipeline_results()` |
| 5 | **Reader retention** (“Today on Waqya”, developing strip) | `inc/home.php`, `front-page.php` |
| 6 | **Weekly budget alerts** | `budget_tracker.py`, `budget-weekly.yml`, pipeline start-of-run summary |
| 7 | **Strategic gaps** | Editorial calendar hints, **Waqya Read** box, crisis mode desk filter, monthly cap alert |

### Config knobs (`automation/config.yaml`)

```yaml
pipeline:
  publish_mode: quality_gated      # draft | auto | quality_gated
  require_min_quality_score: 70
  always_draft_below_score: 55
  auto_publish: true

breaking: { enabled, min_trend_score, desks }
crisis_mode: { enabled: false, desks: [...] }
editorial_calendar: { weekdays: { monday: "...", ... } }
budget: { monthly_cap_usd: 80, weekly_summary: true, alert_at_percent: 80 }
```

### Trust pages (auto-created if missing)

- `/editorial-policy/`
- `/corrections/`
- `/about/`
- `/contact/`

---

## Tier 2 — Growth & distribution (next quarter)

| Feature | Why |
|--------|-----|
| Auto social cards + optional post to X/Bluesky | Commentary spreads on social |
| Google Publisher Center / News sitemap | News/Discover surfaces |
| Section newsletters (Middle East weekly, Tech weekly) | Higher open rates |
| Topic pages (“Iran”, “AI regulation”) from tags | Long-tail SEO |
| Explainers hub | Authority beyond hot takes |
| Multilingual headlines/dek (Urdu/Arabic) | South Asia / ME audiences |

---

## Tier 3 — Operations & money (when traffic justifies)

| Feature | Why |
|--------|-----|
| Analytics dashboard | Unit economics visibility |
| Stale story decay (noindex old dead topics) | Avoid content graveyard |
| Ethical ads / sponsorship | Sustainability |
| Wire/API for partners | B2B revenue |
| Multi-source fact linker | Legal/reputation risk |

---

## Tier 4 — Avoid for now

Native app, podcasts, comments/forums, gimmick verticals (e.g. UFO desk as primary brand).

---

## Recommended 90-day sequence

**Month 1:** Quality gate + trust pages + Telegram review flow *(Tier 1 — done)*  
**Month 2:** Breaking lane + section feeds + homepage “Today” *(mostly Tier 1)*  
**Month 3:** Google News readiness + section digests + social distribution *(Tier 2)*

---

## Bottom line

Production is built. Protect the brand with **gates and trust**, build **habit** on the homepage, and watch **budget** on Telegram. Revisit Tier 2 in a few days when you are ready to scale distribution.
