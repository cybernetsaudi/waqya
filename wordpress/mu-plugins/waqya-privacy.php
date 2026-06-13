<?php
/**
 * Privacy & consent — gate analytics scripts until visitor opts in (GDPR / UK GDPR / CCPA-ready).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Google Consent Mode v2 defaults (must run before Site Kit / gtag).
 */
function waqya_consent_mode_defaults(): void
{
    if (is_admin()) {
        return;
    }
    ?>
<script id="waqya-consent-defaults" data-no-optimize="1" data-cfasync="false">
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
gtag('consent', 'default', {
  ad_storage: 'denied',
  ad_user_data: 'denied',
  ad_personalization: 'denied',
  analytics_storage: 'denied',
  functionality_storage: 'granted',
  security_storage: 'granted',
  wait_for_update: 500
});
</script>
    <?php
}
add_action('wp_head', 'waqya_consent_mode_defaults', 0);

/**
 * Defer analytics script execution until theme consent.js activates them.
 *
 * @param string $tag
 * @return string
 */
function waqya_gate_analytics_script_tag(string $tag): string
{
    if (is_admin() || strpos($tag, '<script') === false) {
        return $tag;
    }

    $blocked = [
        'googletagmanager.com',
        'google-analytics.com',
        'plausible.io',
        'google_gtagjs',
        'monsterinsights',
    ];

    $lower = strtolower($tag);
    foreach ($blocked as $needle) {
        if (strpos($lower, $needle) !== false) {
            if (strpos($tag, 'data-waqya-consent') !== false) {
                return $tag;
            }
            $tag = preg_replace('/\ssrc=/i', ' data-src=', $tag, 1);
            if (strpos($tag, 'type=') === false) {
                $tag = str_replace('<script', '<script type="text/plain" data-waqya-consent="analytics"', $tag);
            } else {
                $tag = preg_replace('/type=["\'][^"\']*["\']/i', 'type="text/plain" data-waqya-consent="analytics"', $tag, 1);
            }
            break;
        }
    }

    return $tag;
}
add_filter('script_loader_tag', 'waqya_gate_analytics_script_tag', 20, 1);

/**
 * Gate inline gtag bootstrap from Site Kit.
 */
function waqya_gate_inline_script(string $tag, string $handle, string $src): string
{
    if ($handle === 'google_gtagjs-js-after' || strpos($handle, 'gtag') !== false) {
        return waqya_gate_analytics_script_tag($tag);
    }
    return $tag;
}
add_filter('script_loader_tag', 'waqya_gate_inline_script', 21, 3);
