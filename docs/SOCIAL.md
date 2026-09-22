# Automated social distribution (free only)

Waqya posts **live** pipeline articles with **no human approval** and **no paid APIs**.

## Free stack (recommended)

| Channel | Cost | Status | Setup |
|---------|------|--------|-------|
| **Bluesky** | Free | **Paused** (`@waqya.bsky.social` has spam label) | Re-enable at 1 post/day after appeal |
| **Mastodon** | Free | Ready in code | Create account + access token (~5 min) |
| **Telegram channel** | Free | **Live, capped** (`t.me/waqya_news`, max 3/day) | Done |
| Weekly email digest | Free | Active on WordPress | Visitors subscribe themselves |
| **X / Twitter** | Paid write API | **Not used** | Skip |

Drafts held by the quality gate are never posted.

---

## 1. Bluesky — paused (spam risk)

Account `@waqya.bsky.social` carried a Bluesky **spam** label after high-volume posting into almost no audience. Auto-post is **off** (`social.bluesky.enabled: false`).

After you appeal / the label clears:

```yaml
social:
  bluesky:
    enabled: true
    max_posts_per_day: 1
```

Keep promo CTAs off (`bluesky_promo_every_n: 0`) until followers are real.

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

Telegram: [t.me/waqya_news](https://t.me/waqya_news) · channel id `@waqya_news`

Posts include a **Read on Waqya** button and a **Join channel** button. Every Nth article in a run also sends a short join CTA (`social.promote.telegram_join_every_n`).

---

## 4. Auto-promote (join links everywhere)

Telegram **cannot** force-add users. Growth is from repeating the invite:

| Surface | What happens |
|---------|----------------|
| Article end + site footer | Theme CTA (Telegram + Bluesky) — theme ≥ 1.9.8 |
| Weekly email digest | Footer line with `t.me/waqya_news` |
| Bluesky posts | Invite line every N posts (`bluesky_promo_every_n`) |
| Telegram channel posts | Inline buttons + occasional join promo |

```yaml
social:
  promote:
    telegram_url: "https://t.me/waqya_news"
    bluesky_url: "https://bsky.app/profile/waqya.bsky.social"
    bluesky_promo_every_n: 2
    telegram_join_every_n: 3
    digest_footer: true
```

WordPress options (optional overrides): `waqya_telegram_channel_url`, `waqya_bluesky_url`.

---

## Why not X?

X’s posting API requires a **paid** developer plan. We deliberately stay on free networks so distribution never depends on a bill.

---

## Idempotency

Posted IDs live in `automation/seen.db` (`social_posts`). Re-runs won’t double-post.

---

## Weekly digest (email)

Plugin **Waqya Subscribers** — Mondays 09:00. Free. See `docs/SUBSCRIBERS.md`.
