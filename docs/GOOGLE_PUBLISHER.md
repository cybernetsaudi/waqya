# Google News & Publisher Center

## On-site (theme)

| Asset | URL |
|-------|-----|
| News sitemap | `https://waqya.com/news-sitemap.xml` |
| Yoast sitemap | `https://waqya.com/sitemap_index.xml` |
| robots.txt | Lists both sitemaps |
| Trust pages | `/about/`, `/editorial-policy/`, `/corrections/`, `/contact/` |
| Organization schema | `publishingPrinciples`, `correctionsPolicy`, contact email |

After deploy, flush permalinks once: **Settings → Permalinks → Save** (or `wp rewrite flush` on the server).

---

## How to test Publisher Center verification

### 1. Pre-flight checks (do these first)

Run in a terminal or browser:

```bash
# News sitemap — must be HTTP 200 and valid XML (not an HTML 404 page)
curl -sI https://waqya.com/news-sitemap.xml | head -1
curl -s https://waqya.com/news-sitemap.xml | head -20

# Yoast index
curl -sI https://waqya.com/sitemap_index.xml | head -1

# robots.txt should mention news-sitemap
curl -s https://waqya.com/robots.txt
```

**Pass criteria**

- `news-sitemap.xml` → `HTTP/2 200` (or `HTTP/1.1 200`)
- Body starts with `<?xml` and contains `<news:news>` entries for recent posts (last 48h)
- `sitemap_index.xml` → 200
- `robots.txt` includes `Sitemap: https://waqya.com/news-sitemap.xml`

**Google Search Console (recommended)**

1. Open [Google Search Console](https://search.google.com/search-console)
2. Add property `https://waqya.com` if not already there
3. **Sitemaps** → submit `sitemap_index.xml` and `news-sitemap.xml`
4. Wait for “Success” status (can take hours)

### 2. Domain verification in Publisher Center

1. Open [Google Publisher Center](https://publishercenter.google.com/)
2. **Add publication** → name **Waqya**, URL `https://waqya.com`
3. Choose verification method:

| Method | Where to apply |
|--------|----------------|
| **DNS TXT** | Hostinger → Domains → waqya.com → DNS → add TXT record Google gives you |
| **HTML file** | Upload to site root via Hostinger File Manager or `public_html/` |
| **HTML meta tag** | Add to theme `<head>` temporarily if file upload is awkward |

4. Click **Verify** in Publisher Center
5. If it fails: wait 15–30 minutes for DNS propagation, then retry

**Tip:** If the site is already verified in Search Console for the same Google account, Publisher Center may inherit verification automatically.

### 3. Publication setup checklist

After verification:

- [ ] Primary language: **English**
- [ ] Country / coverage: as appropriate (e.g. global + UK/US/Middle East desks)
- [ ] Logo: square, ≥ 512×512, transparent or white background
- [ ] Contact email: `hello@waqya.com` (must receive mail — see SMTP test below)
- [ ] Sections: align with desks (Middle East, Technology, Crime & Justice, etc.)
- [ ] Sitemaps submitted: `sitemap_index.xml` **and** `news-sitemap.xml`
- [ ] Link trust pages in “About” / editorial fields where Publisher Center asks

### 4. Test email (SMTP)

WordPress sends from `hello@waqya.com` via Hostinger SMTP (`mail.omniconsa.com`).

On the server:

```bash
cd ~/domains/waqya.com/public_html
wp option get waqya_smtp_host    # expect mail.omniconsa.com
wp option get waqya_mail_from    # expect hello@waqya.com
wp eval 'var_dump(wp_mail("YOUR@EMAIL", "Waqya SMTP test", "If you got this, outbound mail works."));'
```

`bool(true)` = accepted by WordPress/PHPMailer. Check inbox + spam within a few minutes.

### 5. What Google reviews (timeline)

Publisher Center approval is **manual on Google’s side** — typically days to weeks. They look for:

- Consistent publishing (automation pipeline on schedule)
- Real editorial pages (About, Editorial Policy, Corrections)
- Original reporting angle, not thin duplicates
- No long gaps without new stories

---

## Cadence

Google News favours consistent publishing. Keep the automation pipeline on schedule and avoid long gaps without new stories.
