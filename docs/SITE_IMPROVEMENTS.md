# Waqya — Site improvement audit

Updated May 2026 after P0–P2 implementation.

---

## Completed

| Tier | Item | Notes |
|------|------|--------|
| — | Trust pages (professional layout) | Theme v1.7+ |
| P0 | Contact email on site | hello@waqya.com on Contact page |
| P0 | Google News sitemap | `/news-sitemap.xml` + `docs/GOOGLE_PUBLISHER.md` |
| P0 | Org / article schema | NewsMediaOrganization + NewsArticle JSON-LD |
| P0 | Search UX | Desk shortcuts on search results |
| P0 | Performance | Hero `fetchpriority=high`, lazy cards |
| P1 | Section digests | Waqya Subscribers plugin + weekly cron |
| P1 | Topic hubs | `/topic/{slug}/` URLs, index when 3+ posts |
| P1 | Explainers desk | `explainers` category in `categories.json` |
| P1 | Social OG | `inc/social.php` on single posts |
| P1 | Stale noindex | Posts 120+ days old, not updated 90d |
| P2 | Analytics | Plausible optional via `PLAUSIBLE_DOMAIN` |
| P2 | Wire / API | `GET /wp-json/waqya/v1/feed` |
| P2 | Multilingual headlines | `HEADLINE_AR` / `HEADLINE_UR` in pipeline |

---

## Your action: enable digest email

1. Add `WP_SMTP_PASSWORD=...` to `.env` (see `docs/SUBSCRIBERS.md`)
2. Run `python automation/setup_wordpress_mail.py`
3. Subscribe on site and confirm the double opt-in email
4. Submit Publisher Center — `docs/GOOGLE_PUBLISHER.md`

---

## Still open (manual or later)

| Item | Why |
|------|-----|
| Google Publisher Center verification | Requires your Google account |
| Privacy Policy page content | Legal copy — link from subscribe modal |
| Ethical sponsorship units | Wait for traffic threshold |
| Native app, forums, podcasts | P3 — deferred |

---

## Ops commands

```bash
python automation/sync_trust_pages.py      # after editing trust HTML
python automation/setup_wordpress_mail.py  # after changing SMTP in .env
python automation/sync_categories.py       # after categories.json changes
wp rewrite flush                           # after topic/news sitemap deploy
```

---

## 90-day focus

**Month 1:** SMTP live, Publisher Center, first 100 confirmed subscribers  
**Month 2:** Topic hubs ranking, Plausible or GA4 desk dashboards  
**Month 3:** Explainers cadence, sponsorship pilot, wire API partners
