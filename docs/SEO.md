# Waqya — Search & AI indexing

## GSC issues and fixes

| Search Console reason | Usually means | Our fix |
|----------------------|---------------|---------|
| Alternate page with proper canonical tag | Filtered/duplicate URL; Google uses canonical | **Intentional** for `?when=` date filters (canonical → clean archive). |
| Excluded by noindex | Page has `noindex` | **Intentional** for search, tags, author, date archives, blog page 2+. |
| Not found (404) | Dead URL | Legacy category **301 redirects**; remove bad links in Search Console. |
| Page with redirect | URL redirects elsewhere | Legacy slugs (`/category/world/` etc.) **301** to current desks. |

## One SEO plugin only

Use **Yoast SEO** (`wordpress-seo`) only. Do **not** run All in One SEO alongside it—duplicate canonicals and schema cause indexing errors.

```bash
wp plugin deactivate all-in-one-seo-pack
```

## Theme (`inc/seo.php`)

- 301 empty legacy categories → active desks
- `noindex` for search, tags, author, date archives, `?when=` filters, paginated homepage
- Canonical cleanup for date filters
- `NewsMediaOrganization` + `WebSite` JSON-LD on homepage
- Link to `llms.txt` for AI crawlers

## AI discoverability

Deploy to site root (already in repo):

- `https://waqya.com/llms.txt` — section map for LLMs
- `https://waqya.com/ai.txt` — short crawler hints

After deploy:

```bash
scp wordpress/site-assets/llms.txt user@host:~/domains/waqya.com/public_html/llms.txt
scp wordpress/site-assets/ai.txt user@host:~/domains/waqya.com/public_html/ai.txt
```

## Automation

`automation/seo.py` pings `sitemap_index.xml` (Yoast) after each publish. Enable IndexNow in `config.yaml` when `INDEXNOW_KEY` is on the site root.

## Post-publish checklist

1. `blog_public` = 1 (Settings → Reading → allow search engines)
2. Yoast → Settings → taxonomies: **index categories**, **noindex tags**
3. Submit sitemap in Google Search Console: `https://waqya.com/sitemap_index.xml`
4. Request indexing for homepage + top category URLs after major changes
