# Waqya subscribers & weekly digest

Privacy-first email subscriptions built into WordPress (plugin **Waqya Subscribers**).

## How it works

| Step | What happens |
|------|----------------|
| 1 | Visitor enters email and **checks the consent box** (not pre-ticked). |
| 2 | System stores status `pending` and sends a **confirmation email**. |
| 3 | User clicks the confirm link → status `confirmed`. |
| 4 | **Monday 9:00** (site timezone): WordPress cron sends the weekly digest. |
| 5 | Every email includes a one-click **unsubscribe** link. |

**+ Follow** on a post opens the same flow with that section pre-selected for digest highlights.

**First-visit popup** shows once; dismissed for 30 days via browser storage (no tracking cookie required).

## Install on Hostinger

1. Upload `wordpress/plugins/waqya-subscribers/` to `wp-content/plugins/waqya-subscribers/`
2. **Plugins → Activate “Waqya Subscribers”**
3. Ensure theme `single.php` uses `waqya_render_category_follow()` (included in repo)
4. Create a **Privacy Policy** page (Settings → Privacy) and link it — the form points to this URL

## Email delivery

The plugin uses `wp_mail()`. Outbound mail is sent through **hello@waqya.com** via the `waqya-smtp` must-use plugin (Hostinger SMTP).

### Where to put the mailbox password

Add these lines to your local **`.env`** file (repo root — same file as `WP_URL` and `OPENAI_API_KEY`). **Never commit `.env` to git.**

```env
WP_SMTP_PASSWORD=your-hello@waqya.com-password
WP_SMTP_USER=hello@waqya.com
WP_SMTP_FROM=hello@waqya.com
```

Optional: `PLAUSIBLE_DOMAIN=waqya.com` for analytics.

Then apply to the live server:

```bash
export SSHPASS='your-hostinger-ssh-password'
python automation/setup_wordpress_mail.py
```

This uploads `wordpress/mu-plugins/waqya-smtp.php`, stores SMTP settings in WordPress options, and sets `admin_email` to hello@waqya.com.

**Do not paste the mailbox password in chat** — only in `.env` on your machine.

### Deliverability (Yahoo, Gmail, etc.)

Outbound mail is sent from your SMTP host’s IP. If Yahoo or others reject with **553 TSS09** or “permanently deferred”, the provider is blocking that **sending IP** — not your domain name. Fixes:

1. Ask your mail host (e.g. omniconsa) to resolve IP reputation or request delisting via [Yahoo Postmaster](https://postmaster.yahooinc.com/).
2. Or point SMTP at your domain host’s relay (e.g. Hostinger `smtp.hostinger.com` for `hello@waqya.com`) if that IP has better reputation.
3. Keep WordPress **Settings → General → Administration Email** and your admin user email as `hello@waqya.com` so system notices do not go to a personal Yahoo inbox.

Test after setup:

```bash
python automation/test_wordpress_mail.py --send hello@waqya.com
```

Or on the server:

```bash
wp cron event run waqya_send_weekly_digest
wp option get waqya_mail_log --format=json
```

(Requires WP-CLI on server.)

### Troubleshooting: wp_mail true but nothing in inbox

WordPress only reports whether the SMTP server **accepted** the message. A successful send looks like:

```
235 Authentication successful
250 2.0.0 Ok: queued as XXXXX
wp_mail result: true
```

If you see that but `hello@waqya.com` stays empty, the problem is **after** the queue — on the mail host, not in PHP:

| Check | Where |
|-------|--------|
| Webmail login | omniconsa panel / webmail for `hello@waqya.com` |
| Spam / junk folder | Same webmail |
| Mailbox quota full | omniconsa admin |
| Inbound delivery logs | omniconsa — search queue id e.g. `9EED4500B89` |
| Wrong webmail host | MX is `mail.omniconsa.com` — not Hostinger hPanel mail unless you migrated |

**DNS:** `waqya.com` MX → `mail.omniconsa.com`. **SPF is currently missing** — Yahoo often silently drops or spams mail without it. Ask omniconsa for your SPF TXT record, or add at your DNS host:

```txt
v=spf1 mx a:mail.omniconsa.com ~all
```

**Yahoo inbox:** Check **Spam** and **Bulk** folders. Add `hello@waqya.com` to contacts. Search for subject `Your weekly digest - Waqya`.

**Switch relay:** If omniconsa outbound IP is blocklisted, point `.env` at Hostinger instead (`SMTP_HOST=smtp.hostinger.com`), then run `python automation/setup_wordpress_mail.py`.

## Data stored (minimal)

| Field | Purpose |
|-------|---------|
| Email | Send digest only |
| Status | `pending` / `confirmed` / `unsubscribed` |
| Consent version + timestamp | Proof of opt-in |
| Category IDs (JSON) | Sections user follows |
| Confirm / unsubscribe tokens | Secure links (random, not guessable) |

We do **not** store passwords, payment data, or sell lists. No newsletter without confirmed opt-in.

## GDPR / UK GDPR checklist

- [ ] Privacy Policy mentions email, purpose (weekly digest), retention, and contact
- [ ] Consent checkbox is **unchecked by default**
- [ ] Double opt-in enabled (built in)
- [ ] Unsubscribe in every email (built in)
- [ ] Export/erase requests: use **Tools → Export Personal Data** / **Erase** (email is the identifier)

## Optional: disable auto popup

Visitors can close the modal; it won’t show again for 30 days. To disable entirely, set in theme `functions.php`:

```php
add_filter('waqya_subscribers_show_auto_prompt', '__return_false');
```

## Files

- Plugin: `wordpress/plugins/waqya-subscribers/`
- Theme hook: `waqya_render_category_follow()` in `inc/template-tags.php`
