# Automated social distribution

Waqya posts **live** pipeline articles to social networks with **no human approval step**.

## What runs automatically

| Channel | When | Human needed? |
|---------|------|----------------|
| **Bluesky** | After each pipeline publish (every ~4h) | Only once: create account + app password |
| **X (Twitter)** | Same, if enabled + API keys set | Once: developer app + keys (paid API) |
| **Weekly email digest** | Mondays 09:00 site time | Visitors subscribe themselves |

Drafts held by the quality gate are **never** posted.

---

## 1. Bluesky (recommended — do this first)

1. Create [@waqya.bsky.social](https://bsky.app) (or your handle).
2. **Settings → App Passwords → Add** → name it `waqya-pipeline`.
3. Copy the password (looks like `xxxx-xxxx-xxxx-xxxx`).
4. Add GitHub Secrets (repo → Settings → Secrets → Actions):

```
BLUESKY_HANDLE=waqya.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

5. Optionally add the same lines to local `.env` for testing.

Config (`automation/config.yaml`):

```yaml
social:
  enabled: true
  bluesky:
    enabled: true
```

No further clicks. Next pipeline run posts up to `max_posts_per_run` live articles.

---

## 2. X / Twitter (optional)

X’s API is **paid** for write access. If you have access:

1. [developer.x.com](https://developer.x.com) → create app with **Read and Write**.
2. Generate API Key, API Secret, Access Token, Access Token Secret.
3. GitHub Secrets:

```
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
```

4. In `automation/config.yaml`:

```yaml
social:
  x:
    enabled: true
```

Until keys exist, X stays off and the pipeline skips it quietly.

---

## 3. Weekly digest (already on WordPress)

Plugin **Waqya Subscribers** is active on production.

- Cron: `waqya_send_weekly_digest` (Mondays)
- SMTP: `hello@waqya.com` via Hostinger
- Visitors subscribe via site modal / + Follow

To finish mail deliverability if digests aren’t arriving, put the mailbox password in `.env` and run:

```bash
# .env
WP_SMTP_PASSWORD=your-mailbox-password

python automation/setup_wordpress_mail.py
python automation/test_wordpress_mail.py --send hello@waqya.com
```

---

## Idempotency

Posted article IDs are stored in `automation/seen.db` (`social_posts` table). Re-runs won’t double-post the same article to the same network.

---

## Test locally

```bash
cd automation
# With BLUESKY_* in .env:
python -c "
from social_poster import distribute_publish_results
from publisher import PublishResult
r = PublishResult(post_id=999999, edit_url='', title='Waqya social test', post_url='https://waqya.com/', status='publish', quality_score=90)
print(distribute_publish_results([r]))
"
```

Delete the test row from `seen.db` if you need to retry:

```sql
DELETE FROM social_posts WHERE post_id = 999999;
```
