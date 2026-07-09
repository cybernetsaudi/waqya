# Automated social distribution (free only)

Waqya posts **live** pipeline articles with **no human approval** and **no paid APIs**.

## Free stack (recommended)

| Channel | Cost | Status | Setup |
|---------|------|--------|-------|
| **Bluesky** | Free | **Live** (`@waqya.bsky.social`) | Done |
| **Mastodon** | Free | Ready in code | Create account + access token (~5 min) |
| **Telegram channel** | Free | Ready in code | Create public channel + add bot as admin |
| Weekly email digest | Free | Active on WordPress | Visitors subscribe themselves |
| **X / Twitter** | Paid write API | **Not used** | Skip |

Drafts held by the quality gate are never posted.

---

## 1. Bluesky — already configured

Posts after every successful pipeline publish.

Profile: [bsky.app/profile/waqya.bsky.social](https://bsky.app/profile/waqya.bsky.social)

---

## 2. Mastodon (optional, free)

1. Create an account on any instance, e.g. [mastodon.social](https://mastodon.social) or a news-friendly server.
2. **Preferences → Development → New application**
   - Name: `waqya-pipeline`
   - Scopes: `write:statuses` (and `read` if asked)
3. Copy the **access token**.
4. GitHub Secrets:

```
MASTODON_BASE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=your-token
```

5. In `automation/config.yaml`:

```yaml
social:
  mastodon:
    enabled: true
```

---

## 3. Telegram public channel (optional, free)

You already have a Telegram bot for private run alerts. For **public reach**:

1. In Telegram: create a **channel** (e.g. “Waqya”).
2. Add your bot as **administrator** (post messages).
3. Get the channel id:
   - Public username: `@waqya_news`, or
   - Forward a channel post to `@userinfobot` for the numeric `-100…` id
4. GitHub Secret:

```
TELEGRAM_CHANNEL_ID=@waqya_news
```

(Keep existing `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` for private pipeline alerts.)

5. In `automation/config.yaml`:

```yaml
social:
  telegram_channel:
    enabled: true
```

---

## Why not X?

X’s posting API requires a **paid** developer plan. We deliberately stay on free networks so distribution never depends on a bill.

---

## Idempotency

Posted IDs live in `automation/seen.db` (`social_posts`). Re-runs won’t double-post.

---

## Weekly digest (email)

Plugin **Waqya Subscribers** — Mondays 09:00. Free. See `docs/SUBSCRIBERS.md`.
