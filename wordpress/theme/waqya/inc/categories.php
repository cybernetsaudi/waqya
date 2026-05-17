<?php
/**
 * Editorial category configuration and sync
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Primary editorial categories (matches automation/config.yaml + nav).
 *
 * @return array<string, string> slug => label
 */
function waqya_editorial_categories(): array
{
    return [
        'world'      => __('World', 'waqya'),
        'technology' => __('Technology', 'waqya'),
        'science'    => __('Science', 'waqya'),
        'business'   => __('Business', 'waqya'),
        'opinion'    => __('Opinion', 'waqya'),
    ];
}

/**
 * Map legacy / feed categories to editorial slugs.
 *
 * @return array<string, string>
 */
function waqya_legacy_category_map(): array
{
    return [
        'politics-government'         => 'world',
        'politics-and-government'     => 'world',
        'diplomacy'                   => 'world',
        'international-relations'     => 'world',
        'conflict-war-peace'          => 'world',
        'crime-law-justice'           => 'world',
        'disaster-emergency'          => 'world',
        'uk'                          => 'world',
        'united-states'               => 'world',
        'china'                       => 'world',
        'trump'                       => 'world',
        'economy-business'            => 'business',
        'economy-business-and-finance'=> 'business',
        'finance'                     => 'business',
        'science-technology'          => 'technology',
        'science-and-technology'      => 'technology',
        'technology'                  => 'technology',
        'tech'                        => 'technology',
        'health'                      => 'science',
        'public-health'               => 'science',
        'hantavirus'                  => 'science',
        'environment'                 => 'science',
        'lifestyle-leisure'           => 'opinion',
        'human-interest'              => 'opinion',
        'arts-culture-media'          => 'opinion',
        'sport'                       => 'opinion',
        'religion'                    => 'opinion',
        'society'                     => 'world',
        'education'                   => 'world',
        'labour'                      => 'business',
    ];
}

/**
 * Tag slugs that strongly indicate an editorial section.
 *
 * @return array<string, list<string>>
 */
function waqya_editorial_tag_signals(): array
{
    return [
        'technology' => [
            'technology', 'ai', 'artificial-intelligence', 'software', 'startup',
            'cybersecurity', 'semiconductor', 'nvidia', 'apple', 'google', 'microsoft',
            'gaming', 'video-games', 'game-development', 'retro-gaming', 'esports',
        ],
        'business'   => [
            'business', 'finance', 'economy', 'markets', 'stock-market', 'investment',
            'banking', 'trade', 'inflation', 'earnings',
        ],
        'science'    => [
            'science', 'health', 'medicine', 'climate', 'environment', 'research',
            'space', 'nasa', 'pandemic', 'public-health', 'hantavirus',
        ],
        'opinion'    => [
            'opinion', 'commentary', 'analysis', 'culture', 'lifestyle', 'sport',
        ],
    ];
}

/**
 * Resolve editorial slug for a post from categories and tags.
 */
function waqya_resolve_editorial_slug(WP_Post $post): string
{
    $editorial = array_keys(waqya_editorial_categories());
    $terms     = get_the_category($post->ID);

    $tag_slugs = wp_get_post_tags($post->ID, ['fields' => 'slugs']);
    if (is_array($tag_slugs) && $tag_slugs !== []) {
        foreach (waqya_editorial_tag_signals() as $section => $signals) {
            if (array_intersect($tag_slugs, $signals) !== []) {
                return $section;
            }
        }
    }

    $iptc_topic = get_post_meta($post->ID, '_waqya_iptc_topic', true);
    if (is_string($iptc_topic) && $iptc_topic !== '') {
        $iptc_map = [
            'science_technology'  => 'technology',
            'economy_business'    => 'business',
            'health'              => 'science',
            'environment'         => 'science',
            'politics_government' => 'world',
            'conflict_war_peace'  => 'world',
            'arts_culture_media'  => 'opinion',
            'lifestyle_leisure'   => 'opinion',
            'sport'               => 'opinion',
        ];
        if (isset($iptc_map[$iptc_topic])) {
            return $iptc_map[$iptc_topic];
        }
    }

    foreach ($terms as $term) {
        $map = waqya_legacy_category_map();
        if (isset($map[$term->slug])) {
            return $map[$term->slug];
        }
    }

    foreach ($terms as $term) {
        if (in_array($term->slug, $editorial, true)) {
            return $term->slug;
        }
    }

    return 'world';
}

/**
 * Ensure editorial categories exist; return slug => term_id.
 *
 * @return array<string, int>
 */
function waqya_ensure_editorial_categories(): array
{
    $ids = [];
    foreach (waqya_editorial_categories() as $slug => $label) {
        $term = get_category_by_slug($slug);
        if (! $term) {
            $created = wp_insert_term($label, 'category', ['slug' => $slug]);
            if (! is_wp_error($created)) {
                $ids[$slug] = (int) $created['term_id'];
            }
            continue;
        }
        $ids[$slug] = (int) $term->term_id;
    }
    return $ids;
}

/**
 * Assign every published post to exactly one editorial category.
 *
 * @return array{updated: int, total: int}
 */
function waqya_sync_posts_to_editorial_categories(): array
{
    $cat_ids = waqya_ensure_editorial_categories();
    $posts   = get_posts([
        'post_type'      => 'post',
        'post_status'    => 'publish',
        'posts_per_page' => -1,
        'fields'         => 'ids',
    ]);

    $updated = 0;
    foreach ($posts as $post_id) {
        $post = get_post($post_id);
        if (! $post instanceof WP_Post) {
            continue;
        }

        $slug    = waqya_resolve_editorial_slug($post);
        $term_id = $cat_ids[$slug] ?? $cat_ids['world'] ?? 0;
        if (! $term_id) {
            continue;
        }

        $result = wp_set_post_categories((int) $post_id, [$term_id], false);
        if (! is_wp_error($result)) {
            $updated++;
        }
    }

    return ['updated' => $updated, 'total' => count($posts)];
}

/**
 * Get category term for current archive.
 */
function waqya_queried_category(): ?WP_Term
{
    $term = get_queried_object();
    return ($term instanceof WP_Term && $term->taxonomy === 'category') ? $term : null;
}
