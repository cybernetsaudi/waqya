<?php
/**
 * Google AdSense — site-wide script + ads.txt helper.
 *
 * Publisher: ca-pub-7582233404244373
 * Script loads for site verification; personalized ads follow Consent Mode
 * (see assets/js/consent.js → advertising preference).
 *
 * Ad *slots* stay off until traffic is measurable (Search Console / analytics
 * sessions). Toggle via option `waqya_adsense_slots_enabled` = true, or filter
 * `waqya_adsense_slots_enabled`. Do not ship empty units on a near-zero-traffic site.
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * AdSense client ID (ca-pub-…).
 */
function waqya_adsense_client(): string
{
    $client = (string) get_option('waqya_adsense_client', 'ca-pub-7582233404244373');
    $client = trim($client);

    return (string) apply_filters('waqya_adsense_client', $client);
}

/**
 * Whether AdSense is enabled.
 */
function waqya_adsense_enabled(): bool
{
    $enabled = (bool) get_option('waqya_adsense_enabled', true);
    if (waqya_adsense_client() === '') {
        return false;
    }

    return (bool) apply_filters('waqya_adsense_enabled', $enabled);
}

/**
 * Whether in-article / sidebar ad units may render.
 * Default false — verification script only until sessions exist.
 */
function waqya_adsense_slots_enabled(): bool
{
    $enabled = (bool) get_option('waqya_adsense_slots_enabled', false);

    return (bool) apply_filters('waqya_adsense_slots_enabled', $enabled);
}

/**
 * Output AdSense loader in <head> (required for Google site verification).
 * Personalized ads remain gated by Consent Mode until advertising consent.
 */
function waqya_adsense_head(): void
{
    if (is_admin() || ! waqya_adsense_enabled()) {
        return;
    }

    $client = waqya_adsense_client();
    printf(
        '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=%s" crossorigin="anonymous" data-no-optimize="1" data-cfasync="false"></script>' . "\n",
        esc_attr($client)
    );
}
add_action('wp_head', 'waqya_adsense_head', 20);

/**
 * Future ad unit helper — no-op until slots are explicitly enabled + slot IDs set.
 * Wire into single.php / sidebar only after measurable sessions.
 */
function waqya_adsense_unit(string $slot = '', string $format = 'auto'): void
{
    if (! waqya_adsense_enabled() || ! waqya_adsense_slots_enabled()) {
        return;
    }
    if ($slot === '') {
        return;
    }

    $client = waqya_adsense_client();
    printf(
        '<ins class="adsbygoogle" style="display:block" data-ad-client="%s" data-ad-slot="%s" data-ad-format="%s" data-full-width-responsive="true"></ins>' . "\n"
        . '<script>(adsbygoogle = window.adsbygoogle || []).push({});</script>' . "\n",
        esc_attr($client),
        esc_attr($slot),
        esc_attr($format)
    );
}

/**
 * Serve ads.txt at /ads.txt (IAB Authorized Digital Sellers).
 */
function waqya_ads_txt_rewrite(): void
{
    add_rewrite_rule('^ads\.txt$', 'index.php?waqya_ads_txt=1', 'top');
}
add_action('init', 'waqya_ads_txt_rewrite');

function waqya_ads_txt_query_var(array $vars): array
{
    $vars[] = 'waqya_ads_txt';

    return $vars;
}
add_filter('query_vars', 'waqya_ads_txt_query_var');

function waqya_serve_ads_txt(): void
{
    if ((int) get_query_var('waqya_ads_txt') !== 1) {
        return;
    }

    $pub = preg_replace('/^ca-/', '', waqya_adsense_client()) ?: 'pub-7582233404244373';
    $lines = [
        '# Waqya ads.txt',
        sprintf('google.com, %s, DIRECT, f08c47fec0942fa0', $pub),
    ];
    $body = implode("\n", $lines) . "\n";

    status_header(200);
    header('Content-Type: text/plain; charset=utf-8');
    header('X-Robots-Tag: noindex');
    echo $body;
    exit;
}
add_action('template_redirect', 'waqya_serve_ads_txt', 1);

/**
 * Flush rewrite rules once after theme update so /ads.txt works.
 */
function waqya_ads_txt_maybe_flush(): void
{
    $ver = get_option('waqya_ads_txt_rewrite_ver', '');
    if ($ver === '1.10.0') {
        return;
    }
    flush_rewrite_rules(false);
    update_option('waqya_ads_txt_rewrite_ver', '1.10.0', false);
}
add_action('after_switch_theme', 'waqya_ads_txt_maybe_flush');
add_action('init', 'waqya_ads_txt_maybe_flush', 99);
