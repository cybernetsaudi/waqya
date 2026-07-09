<?php
/**
 * Social follow / auto-promote CTAs (Telegram, Bluesky).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Public Telegram channel URL for join CTAs.
 */
function waqya_telegram_channel_url(): string
{
    $url = (string) get_option('waqya_telegram_channel_url', 'https://t.me/waqya_news');
    $url = $url !== '' ? $url : 'https://t.me/waqya_news';

    return (string) apply_filters('waqya_telegram_channel_url', $url);
}

/**
 * Bluesky profile URL.
 */
function waqya_bluesky_profile_url(): string
{
    $url = (string) get_option('waqya_bluesky_url', 'https://bsky.app/profile/waqya.bsky.social');
    $url = $url !== '' ? $url : 'https://bsky.app/profile/waqya.bsky.social';

    return (string) apply_filters('waqya_bluesky_profile_url', $url);
}

/**
 * Compact follow strip (footer + article end).
 */
function waqya_render_follow_promo(string $context = 'footer'): void
{
    $tg  = waqya_telegram_channel_url();
    $bsky = waqya_bluesky_profile_url();
    $mod  = sanitize_html_class($context);
    ?>
    <aside class="follow-promo follow-promo--<?php echo esc_attr($mod); ?>" aria-label="<?php esc_attr_e('Follow Waqya', 'waqya'); ?>">
        <p class="follow-promo__eyebrow"><?php esc_html_e('Follow the newsroom', 'waqya'); ?></p>
        <p class="follow-promo__text">
            <?php esc_html_e('Get stories as they publish — no app store, no paywall.', 'waqya'); ?>
        </p>
        <div class="follow-promo__actions">
            <a class="follow-promo__btn follow-promo__btn--telegram" href="<?php echo esc_url($tg); ?>" rel="noopener noreferrer" target="_blank">
                <?php esc_html_e('Telegram', 'waqya'); ?>
            </a>
            <a class="follow-promo__btn follow-promo__btn--bluesky" href="<?php echo esc_url($bsky); ?>" rel="noopener noreferrer" target="_blank">
                <?php esc_html_e('Bluesky', 'waqya'); ?>
            </a>
        </div>
    </aside>
    <?php
}
