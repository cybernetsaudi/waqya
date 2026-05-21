<?php
/**
 * Search & AI discoverability — canonicals, robots, redirects
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Legacy nav slugs → current primary categories (301 when empty).
 *
 * @return array<string, string>
 */
function waqya_legacy_category_redirects(): array
{
    return [
        'world'              => 'current-affairs',
        'technology'         => 'technology-ai',
        'business'           => 'business-economy',
        'opinion'            => 'entertainment-arts',
        'science-technology' => 'science',
        'politics-government' => 'current-affairs',
        'economy-business'   => 'business-economy',
    ];
}

/**
 * Remove duplicate meta description (Yoast/AIOSEO handle this).
 */
function waqya_seo_remove_duplicate_meta(): void
{
    remove_action('wp_head', 'waqya_brand_meta_description', 1);
}
add_action('after_setup_theme', 'waqya_seo_remove_duplicate_meta', 20);

/**
 * 301 redirect empty legacy category archives.
 */
function waqya_legacy_category_redirect(): void
{
    if (! is_category() || is_admin()) {
        return;
    }

    $term = get_queried_object();
    if (! $term instanceof WP_Term || (int) $term->count > 0) {
        return;
    }

    $map = waqya_legacy_category_redirects();
    if (! isset($map[$term->slug])) {
        return;
    }

    $target = waqya_category_url($map[$term->slug]);
    if ($target === '') {
        return;
    }

    wp_safe_redirect($target, 301);
    exit;
}
add_action('template_redirect', 'waqya_legacy_category_redirect', 1);

/**
 * Canonical for filtered archives → base archive (avoids duplicate indexing).
 */
function waqya_seo_canonical(string $canonical): string
{
    if (waqya_get_date_period() !== '' && waqya_date_filter_supported()) {
        return waqya_date_filter_url('all');
    }

    return $canonical;
}
add_filter('wpseo_canonical', 'waqya_seo_canonical');
add_filter('get_canonical_url', 'waqya_seo_canonical');

/**
 * Robots directives for low-value URLs.
 *
 * @param array<string, bool|string> $robots
 * @return array<string, bool|string>
 */
function waqya_seo_robots(array $robots): array
{
    if (is_search() || is_404()) {
        $robots['noindex']   = true;
        $robots['follow']   = true;
        $robots['nofollow'] = false;
    }

    if (waqya_get_date_period() !== '' && waqya_date_filter_supported()) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
    }

    if (is_paged() && (is_front_page() || is_home())) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
    }

    if (is_author() || is_date()) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
    }

    if (is_tag()) {
        $robots['noindex'] = true;
        $robots['follow']  = true;
    }

    return $robots;
}
add_filter('wp_robots', 'waqya_seo_robots', 20);

/**
 * NewsMediaOrganization + WebSite schema (complements Yoast per-post schema).
 */
function waqya_seo_site_schema(): void
{
    if (! is_front_page()) {
        return;
    }

    $site = waqya_site_name();
    $url  = home_url('/');
    $data = [
        '@context' => 'https://schema.org',
        '@graph'   => [
            [
                '@type'            => 'NewsMediaOrganization',
                '@id'              => $url . '#organization',
                'name'             => $site,
                'alternateName'    => waqya_brand_full_name(),
                'url'              => $url,
                'description'      => waqya_brand_tagline(),
                'slogan'           => waqya_brand_story_short(),
                'knowsAbout'       => ['news', 'current affairs', 'commentary', 'world news'],
                'publishingPrinciples' => $url,
            ],
            [
                '@type'           => 'WebSite',
                '@id'             => $url . '#website',
                'url'             => $url,
                'name'            => $site,
                'description'     => waqya_brand_tagline(),
                'publisher'       => ['@id' => $url . '#organization'],
                'inLanguage'      => get_bloginfo('language'),
                'potentialAction' => [
                    '@type'       => 'SearchAction',
                    'target'      => [
                        '@type'       => 'EntryPoint',
                        'urlTemplate' => home_url('/?s={search_term_string}'),
                    ],
                    'query-input' => 'required name=search_term_string',
                ],
            ],
        ],
    ];

    echo '<script type="application/ld+json">' . wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
}
add_action('wp_head', 'waqya_seo_site_schema', 5);

/**
 * Hint crawlers where llms.txt lives.
 */
function waqya_seo_llms_link(): void
{
    if (! is_front_page()) {
        return;
    }

    printf(
        '<link rel="alternate" type="text/plain" href="%s" title="LLMs documentation" />' . "\n",
        esc_url(home_url('/llms.txt'))
    );
}
add_action('wp_head', 'waqya_seo_llms_link', 3);
