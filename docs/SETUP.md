# Waqya.com — Setup Guide

Complete step-by-step instructions to get your automated news site running.

---

## 1. Point Your Domain (Porkbun → Hostinger)

1. Log in to **Hostinger** → go to **hPanel** → **Hosting** → **Add Website**
2. Choose your WordPress hosting plan and enter `waqya.com` as the domain
3. Hostinger will give you **two nameservers**, e.g.:
   ```
   ns1.dns-parking.com
   ns2.dns-parking.com
   ```
4. Log in to **Porkbun** → go to **Domain Management** → click **waqya.com**
5. Under **Nameservers**, replace the defaults with the Hostinger nameservers
6. Save. DNS propagation takes 15 minutes to 48 hours (usually under 1 hour)

**Verify**: Run `dig waqya.com` or visit https://dnschecker.org — you should see it pointing to Hostinger's IP.

---

## 2. Install WordPress on Hostinger

1. In **hPanel** → **Websites** → click **Manage** on waqya.com
2. Go to **Auto Installer** → **WordPress**
3. Fill in:
   - **Admin username**: pick something (NOT `admin` — security)
   - **Admin password**: strong password — save it in a password manager
   - **Admin email**: your email
   - **Website title**: `Waqya`
4. Click **Install**
5. Once installed, visit `https://waqya.com/wp-admin` to confirm it works

---

## 3. Configure WordPress

### 3a. Install an SSL Certificate

Hostinger usually auto-provisions a free SSL certificate. If not:
1. hPanel → **SSL** → **Install SSL** for waqya.com
2. In WordPress: **Settings → General** → ensure both URLs start with `https://`

### 3b. Set Permalinks

1. **Settings → Permalinks** → choose **Post name** (`/%postname%/`)
2. Save — this gives you clean SEO-friendly URLs

### 3c. Install Recommended Plugins

Go to **Plugins → Add New** and install:

| Plugin | Purpose |
|---|---|
| **Yoast SEO** | SEO metadata, sitemaps, social previews |
| **WP Super Cache** or **LiteSpeed Cache** | Page caching (Hostinger uses LiteSpeed) |
| **Akismet** | Spam protection for comments |

### 3d. Choose a Theme

Go to **Appearance → Themes → Add New** and search for one of these:

1. **Astra** — the most popular free WordPress theme. Fast, lightweight, and has news/magazine starter templates. **Recommended.**
2. **GeneratePress** — performance-focused, clean design, great for content-heavy sites.
3. Or browse the "news" / "magazine" tags in the theme directory for something more editorial.

Pick **Astra** if unsure — it is the safest, fastest choice.

### 3e. Create an Application Password (for the REST API)

This is how the automation pipeline logs in to create drafts:

1. Go to **Users → Profile** (your admin account)
2. Scroll down to **Application Passwords**
3. Enter a name: `waqya-pipeline`
4. Click **Add New Application Password**
5. **COPY the password** — it is shown only once
6. This goes into your `.env` file as `WP_APP_PASSWORD`

### 3f. Create Categories

Go to **Posts → Categories** and create:
- Technology
- World
- Science
- Business
- Opinion

These must match the names in `automation/config.yaml`.

---

## 4. Get Your API Keys

### 4a. OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create a new key, name it `waqya`
3. Copy it → this is your `OPENAI_API_KEY`
4. Add a spending limit under **Settings → Billing → Usage limits** (recommended: $10/month hard cap)

### 4b. NewsAPI Key

1. Go to https://newsapi.org/register
2. Sign up for a free account
3. Your API key is on the dashboard → this is your `NEWSAPI_KEY`
4. Free tier: 100 requests/day (more than enough)

**Note**: NewsAPI free tier only works for development. For production, their "everything" endpoint requires a paid plan ($449/month — skip it). The RSS feeds alone are sufficient. Set `newsapi.enabled: false` in `config.yaml` if you want to rely on RSS only.

### 4c. Telegram Bot

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Follow prompts — give it a name like "Waqya Alerts"
4. Copy the **bot token** → this is your `TELEGRAM_BOT_TOKEN`
5. Start a chat with your new bot (search its username and tap Start)
6. To get your **chat ID**:
   - Send any message to the bot
   - Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for `"chat":{"id": 123456789}` — that number is your `TELEGRAM_CHAT_ID`

---

## 5. Set Up the GitHub Repository

1. Create a new **private** repository on GitHub (e.g., `waqya-automation`)
2. Push this codebase:
   ```bash
   cd /path/to/waqya
   git remote add origin git@github.com:YOUR_USERNAME/waqya-automation.git
   git branch -M main
   git push -u origin main
   ```

### 5a. Add Repository Secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret Name | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `NEWSAPI_KEY` | Your NewsAPI key |
| `WP_URL` | `https://waqya.com` |
| `WP_USER` | Your WordPress admin username |
| `WP_APP_PASSWORD` | The application password from step 3e |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

### 5b. Test the Pipeline

1. Go to **Actions** tab in your GitHub repo
2. Click **Waqya News Pipeline** in the left sidebar
3. Click **Run workflow** → **Run workflow**
4. Watch the logs — you should see:
   - News being gathered from RSS feeds
   - Articles being generated
   - Drafts appearing in your WordPress admin
   - A Telegram notification arriving on your phone

---

## 6. Local Development & Testing

To run the pipeline locally:

```bash
# Create a .env file from the template
cp .env.example .env
# Fill in your actual keys in .env

# Install dependencies
pip install -r automation/requirements.txt

# Test individual modules
cd automation
python gatherer.py    # Test news gathering
python generator.py   # Test article generation (uses a sample story)
python notifier.py    # Test Telegram notification
python pipeline.py    # Run the full pipeline
```

---

## 7. Going Live Checklist

- [ ] Domain pointing to Hostinger (DNS propagated)
- [ ] WordPress installed with SSL
- [ ] Permalinks set to "Post name"
- [ ] Yoast SEO installed and configured
- [ ] Caching plugin active
- [ ] Categories created (Technology, World, Science, Business, Opinion)
- [ ] Application password created
- [ ] All API keys obtained (OpenAI, NewsAPI, Telegram)
- [ ] GitHub repo created with all secrets configured
- [ ] Pipeline tested via manual workflow dispatch
- [ ] Telegram notification received
- [ ] First batch of drafts reviewed and published
- [ ] Apply for Google AdSense after 20-30 published articles

---

## Ongoing Maintenance

- **Review drafts daily** — the pipeline runs every 4 hours, so you'll have batches to review
- **Tune prompts** — if article quality isn't right, edit `automation/prompts/commentary.md`
- **Add/remove RSS feeds** — edit `automation/config.yaml`
- **Monitor costs** — check OpenAI usage dashboard weekly for the first month
- **Update WordPress** — keep plugins and themes updated (Hostinger can auto-update)
- **Check GitHub Actions** — if runs start failing, check the Actions tab for error logs
