# Privacy & compliance — Waqya

Status after May 2026 implementation. **Not legal advice** — have counsel review before scale.

## Current posture

| Area | Status | Implementation |
|------|--------|----------------|
| Analytics consent (GA4, Plausible) | **Fixed** | Consent banner + Google Consent Mode v2 default denied + scripts gated |
| Privacy Policy | **Live** | `/privacy-policy/` (trust page template) |
| Email digest (GDPR) | **Good** | Double opt-in, unchecked consent box, unsubscribe |
| Cookie settings UI | **Live** | Footer “Cookie settings” reopens banner |
| CCPA “Do not sell” | **N/A** | We do not sell data; policy states this |

## What was wrong (before)

- Google Site Kit (`GT-MR2TFT7C`) loaded on every visit **without** consent.
- Plausible loaded on every visit **without** consent.
- No cookie banner, no Privacy Policy page in repo.

## Files

| File | Role |
|------|------|
| `wordpress/mu-plugins/waqya-privacy.php` | Consent Mode defaults; gate `script` tags |
| `wordpress/theme/waqya/inc/consent.php` | Banner UI + deferred Plausible |
| `wordpress/theme/waqya/assets/js/consent.js` | Opt-in / opt-out + activate scripts |
| `wordpress/theme/waqya/content/trust-pages/privacy-policy.html` | Policy copy |

## Deploy / sync

```bash
python automation/sync_trust_pages.py   # creates privacy-policy + links WP setting
# rsync theme + mu-plugins to Hostinger, purge cache
```

## Future risks to prepare for

| Risk | When it bites | Mitigation |
|------|----------------|------------|
| **WooCommerce** active but unused | Shop cookies without disclosure | Deactivate WC if no store; policy section exists |
| **MonsterInsights + Site Kit** both on | Duplicate GA, double consent | Use one analytics stack only |
| **Hostinger Reach / marketing plugins** | New trackers without consent | Audit plugins before install; extend `waqya-privacy.php` gate list |
| **Embedded YouTube/Twitter** | Third-party cookies | Use privacy-enhanced embeds or block until consent |
| **Comments enabled** | IP/email in comments | Keep off or add moderation + policy update |
| **EU paywall / reg wall** | Extra lawful basis | Legal review before accounts |
| **AI training on user data** | Subscriber emails | Never train on inbox; policy already limits use |
| **Data breach** | Any PII leak | Document breach process; encrypt backups; 72h ICO notice plan |
| **Children’s data** | Under-16 signups | No child-directed features; block in forms |
| **US state laws** (VA, CO, CT…) | Traffic from those states | Policy covers access/delete; honor requests via hello@waqya.com |
| **Newsletter to EU without consent** | Fines | Keep double opt-in; no purchased lists |

## Recommended next steps (non-code)

1. **Disable WooCommerce** if you are not selling anything (reduces cookie surface).
2. **Pick one analytics tool** — GA4 *or* Plausible, not both, to simplify consent copy.
3. **Sign DPA** with Google / Hostinger if processing EU traffic at scale.
4. **Register ICO** (UK) if required for your structure and turnover.
5. **Annual review** of privacy policy when adding features (apps, accounts, ads).

## Analytics without consent

You can still see **aggregate** trends:

- Server logs (Hostinger)
- Google Search Console (no on-site cookie)
- Plausible self-hosted with no cookies (still get legal advice for EU)

On-site engagement metrics require consent under current UK/EU interpretation.
