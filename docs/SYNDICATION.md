# Syndication & RSS distribution

Automated backlinks to **waqya.com** without spam: canonical link shares and RSS aggregators.

---

## Flipboard — where to add RSS (step by step)

A **publisher profile alone is not enough**. RSS lives on each **magazine**.

### 1. Open the publisher hub

1. Go to [flipboard.com/publishers](https://flipboard.com/publishers)
2. Sign in with the account you created for Waqya

### 2. Create a magazine (required)

1. On your Flipboard profile, click **Create a new magazine** (or **+** → **New magazine**)
2. Set:
   - **Title:** e.g. `Waqya — Middle East`
   - **Description:** short line about the desk
   - **Visibility:** Public
3. Click **Create**

### 3. Add the RSS feed (this is the part that’s easy to miss)

After the magazine exists:

1. Open the magazine you just created
2. Click **Edit magazine** (pencil icon) or the **⋯** menu → **Edit**
3. Look for **Sources** or **RSS Feeds** (wording varies by UI version)
4. Paste the feed URL and click **Add** / **Submit**

If you only see “Flip” / manual curation, you’re on the reader view — go back to **your profile** → hover the magazine → **Edit**.

### 4. Waqya feed URLs (copy-paste)

**Use the main feed first** — it has enough items for Flipboard (≥30). Category feeds only work when that desk has **30+ published posts**.

| Magazine name | RSS URL | Notes |
|---------------|---------|--------|
| Waqya (all stories) | `https://waqya.com/feed/` | **Start here** |
| Middle East | `https://waqya.com/category/middle-east/feed/` | 150+ posts |
| South Asia | `https://waqya.com/category/south-asia/feed/` | check count |
| United Kingdom | `https://waqya.com/category/united-kingdom/feed/` | check count |
| United States | `https://waqya.com/category/united-states/feed/` | check count |
| Technology & AI | `https://waqya.com/category/technology-ai/feed/` | needs 30+ posts in desk |
| Fashion & Style | `https://waqya.com/category/fashion-style/feed/` | newer desk |

**Do not** use “Flip from URL” with an RSS link — that tool expects article pages. Use **Magazine → Edit → Sources / RSS Feeds** instead.

### Flipboard feed requirements

1. **At least 30 items** in the feed XML (Waqya serves 50 after theme 1.9.9)
2. **Full article body** in each item (not title-only)
3. **At least one image** per post, ideally ≥400px wide (featured image + `media:content`)

If submission fails, try `https://waqya.com/feed/` first, then desk feeds once approved.

### 5. Approval

Flipboard reviews feeds manually (often a few days). Feeds should include:

- Full article body (`content:encoded`) — Waqya RSS already has this
- Images in posts — Waqya includes featured images

### 6. Verify a feed in your browser

```bash
curl -sI https://waqya.com/category/middle-east/feed/ | head -1
# HTTP/2 200
```

---

## LinkedIn — company page link shares

Posts go to [linkedin.com/company/waqya](https://www.linkedin.com/company/waqya/) after each pipeline run (top 3 articles, score ≥ 78).

This is a **link card** (headline + teaser + thumbnail → waqya.com), not a full LinkedIn Article.

### One-time setup

1. **LinkedIn Developer app** — you created this (Client ID on file)
2. **Products** — enable **Community Management API** (and Sign In with LinkedIn if asked)
3. **Auth → Redirect URLs** — add:
   ```
   http://localhost:8765/linkedin/callback
   ```
4. **`.env`** (never commit):
   ```
   LINKEDIN_CLIENT_ID=your-client-id
   LINKEDIN_CLIENT_SECRET=your-client-secret
   ```
5. **Authorize** (must be logged in as a **company page admin**):
   ```bash
   cd automation
   python3 linkedin_auth.py
   ```
6. Copy the printed tokens into `.env` and **GitHub Secrets**:
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_REFRESH_TOKEN`
   - `LINKEDIN_ORGANIZATION_URN`
   - `LINKEDIN_ACCESS_TOKEN_EXPIRES_AT`
   - `LINKEDIN_CLIENT_ID`
   - `LINKEDIN_CLIENT_SECRET`

### Security

If a client secret was shared in chat or email, **rotate it** in the LinkedIn Developer portal and update Secrets.

---

## Medium (optional)

Medium stopped issuing new **Integration Tokens** in January 2025.

- If you have a legacy token → set `MEDIUM_INTEGRATION_TOKEN` and `syndication.medium.enabled: true`
- If not → use **Import story** on Medium (paste waqya.com URL); Medium usually sets canonical to your site

---

## Config (`automation/config.yaml`)

```yaml
syndication:
  enabled: true
  max_posts_per_run: 3
  min_quality_score: 78
  linkedin:
    enabled: true
    organization_vanity: waqya
```

---

## Idempotency

Posted article IDs are stored in `automation/seen.db` under network `linkedin`. Re-runs skip duplicates.
