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
        $term = get_queried_object();
        $min  = waqya_topic_min_posts_for_index();
        if ($term instanceof WP_Term && (int) $term->count >= $min) {
            $robots['index']  = true;
            $robots['noindex'] = false;
        } else {
            $robots['noindex'] = true;
            $robots['follow']  = true;
        }
    }

    if (is_singular('post')) {
        $post = get_queried_object();
        if ($post instanceof WP_Post) {
            $age_days = (time() - (int) get_post_time('U', true, $post)) / DAY_IN_SECONDS;
            $mod_days = (time() - (int) get_post_modified_time('U', true, $post)) / DAY_IN_SECONDS;
            if ($age_days > 120 && $mod_days > 90 && ! has_tag('Breaking', $post)) {
                $robots['noindex'] = true;
                $robots['follow']  = true;
            }
        }
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
    $logo = get_site_icon_url(512) ?: '';
    $contact_email = (string) get_option('waqya_mail_from', 'hello@waqya.com');
    $org = [
        '@type'                => 'NewsMediaOrganization',
        '@id'                  => $url . '#organization',
        'name'                 => $site,
        'alternateName'        => waqya_brand_full_name(),
        'url'                  => $url,
        'description'          => waqya_brand_tagline(),
        'slogan'               => waqya_brand_story_short(),
        'knowsAbout'           => ['news', 'current affairs', 'commentary', 'world news'],
        'publishingPrinciples' => home_url('/editorial-policy/'),
        'ethicsPolicy'         => home_url('/editorial-policy/'),
        'correctionsPolicy'    => home_url('/corrections/'),
        'contactPoint'         => [
            '@type'       => 'ContactPoint',
            'contactType' => 'customer support',
            'email'       => $contact_email,
            'url'         => home_url('/contact/'),
        ],
    ];
    if ($logo !== '') {
        $org['logo'] = ['@type' => 'ImageObject', 'url' => $logo];
    }

    $data = [
        '@context' => 'https://schema.org',
        '@graph'   => [
            $org,
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

/**
 * NewsArticle schema on single posts.
 */
function waqya_seo_article_schema(): void
{
    if (! is_singular('post')) {
        return;
    }

    $post_id = get_the_ID();
    $url     = get_permalink();
    $image   = get_the_post_thumbnail_url(null, 'large');

    $author = [
        '@type' => 'Organization',
        'name'  => waqya_site_name(),
        'url'   => home_url('/about/'),
    ];

    $data = [
        '@context'         => 'https://schema.org',
        '@type'            => 'NewsArticle',
        'headline'         => wp_strip_all_tags(get_the_title()),
        'description'      => wp_strip_all_tags(get_the_excerpt()),
        'datePublished'    => get_the_date('c'),
        'dateModified'     => get_the_modified_date('c'),
        'mainEntityOfPage' => $url,
        'author'           => $author,
        'publisher'        => [
            '@type' => 'NewsMediaOrganization',
            'name'  => waqya_site_name(),
            'url'   => home_url('/'),
        ],
        'inLanguage'       => get_bloginfo('language'),
    ];
    if ($image) {
        $data['image'] = [$image];
    }

    $desk = waqya_desk_byline_label();
    if ($desk !== '') {
        $data['articleSection'] = $desk;
    }

    echo '<script type="application/ld+json">' . wp_json_encode($data, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE) . "</script>\n";
}
add_action('wp_head', 'waqya_seo_article_schema', 6);
