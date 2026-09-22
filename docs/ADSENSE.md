# AdSense — status and checklist

## What’s already done (code / site)

- Publisher ID `ca-pub-7582233404244373` in theme head script
- Live `/ads.txt` with Google DIRECT line
- Consent Mode gates advertising until the visitor allows ads
- Privacy policy mentions ads
- **Ad slots intentionally off** (`waqya_adsense_slots_enabled` defaults false) until the site has measurable sessions

## What AdSense / you still need to do

1. **AdSense account status** — In [adsense.google.com](https://www.google.com/adsense/): confirm site `waqya.com` is added, and whether status is *Getting ready*, *Ready*, *Requires attention*, or *Approved*.
2. **Site verification** — Keep the head script + ads.txt (already live). In AdSense, complete any “verify site” / crawl steps.
3. **Payment profile** — Legal name/address, tax info, and a payout method (bank). Ads won’t pay without this even after approval.
4. **Policy readiness** (Google rejects or limits AI-heavy sites often):
   - Clear **About**, **Contact**, **Editorial / corrections** pages (you have trust pages — keep them linked in footer)
   - No deceptive titles, no scraped full-text wire copy
   - Enough **original value** that a human would choose the site
5. **Traffic before slots** — Wait until Search Console (or GA/Site Kit) shows real sessions (rough rule: consistent organic/referral visitors for 2+ weeks, not just you hitting the site). Then:
   - Create ad units in AdSense → copy slot IDs
   - Set WP option `waqya_adsense_slots_enabled` = `1`
   - Wire `waqya_adsense_unit('SLOT_ID')` into `single.php` / sidebar and deploy theme
6. **Do not** turn on Auto ads sitewide while traffic is ~zero — empty inventory + AI scale looks like a thin content farm to reviewers.

## When to flip slots on

| Signal | Gate |
|--------|------|
| GSC impressions trending up for focus desks | Prefer |
| Analytics: non-trivial sessions/day for 14+ days | Prefer |
| AdSense “Ready to show ads” / approved | Required |
| Bluesky/Telegram still near-zero | Not a blocker for AdSense, but don’t expect social to fund RPM |

## Not doing yet (by design)

- In-article / sidebar `<ins class="adsbygoogle">` units
- Auto ads
- Multiple ad networks
