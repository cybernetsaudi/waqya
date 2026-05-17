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

The plugin uses `wp_mail()`. On Hostinger, install **WP Mail SMTP** (or Hostinger’s mail plugin) so confirmation and digest emails are reliable.

Test after setup:

```bash
wp cron event run waqya_send_weekly_digest
```

(Requires WP-CLI on server.)

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
