<?php
/**
 * Post hero slider (homepage + category archives)
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * @param array<string, mixed> $args
 */
function waqya_slider_query(array $args): WP_Query
{
    $defaults = [
        'post_type'           => 'post',
        'post_status'         => 'publish',
        'posts_per_page'      => 5,
        'ignore_sticky_posts' => true,
        'no_found_rows'       => true,
    ];

    return new WP_Query(array_merge($defaults, $args));
}

/**
 * Cached slider query (one fetch per request per args).
 *
 * @param array<string, mixed> $args
 */
function waqya_get_slider_query(array $args): WP_Query
{
    static $cache = [];

    unset($args['echo'], $args['title']);
    $key = md5(wp_json_encode($args));

    if (! isset($cache[$key])) {
        $cache[$key] = waqya_slider_query($args);
    }

    return $cache[$key];
}

/**
 * Resolve category term ID from a main archive query.
 */
function waqya_category_id_from_query(WP_Query $query): int
{
    $cat_id = (int) $query->get('cat');
    if ($cat_id > 0) {
        return $cat_id;
    }

    $slug = $query->get('category_name');
    if (is_string($slug) && $slug !== '') {
        $term = get_category_by_slug($slug);
        if ($term) {
            return (int) $term->term_id;
        }
    }

    if (is_array($query->get('category__in'))) {
        $in = array_map('intval', (array) $query->get('category__in'));
        if (count($in) === 1) {
            return $in[0];
        }
    }

    return 0;
}

/**
 * Post IDs shown in the archive slider (exclude from main loop page 1).
 *
 * @return int[]
 */
function waqya_category_slider_exclude_ids(?WP_Query $for_query = null): array
{
    static $cache = [];

    if ($for_query instanceof WP_Query) {
        $cat_id = waqya_category_id_from_query($for_query);
        if ($cat_id <= 0) {
            return [];
        }
        if (isset($cache[$cat_id])) {
            return $cache[$cat_id];
        }
        $slider = waqya_get_slider_query([
            'cat'            => $cat_id,
            'posts_per_page' => 5,
        ]);
        $cache[$cat_id] = array_map('intval', wp_list_pluck($slider->posts, 'ID'));
        return $cache[$cat_id];
    }

    if (! is_category()) {
        return [];
    }

    global $wp_query;

    return waqya_category_slider_exclude_ids($wp_query);
}

/**
 * Render post slider; returns post IDs displayed.
 *
 * @param array<string, mixed> $args cat, category__in, posts_per_page, post__not_in, title, echo
 * @return int[]
 */
function waqya_render_post_slider(array $args): array
{
    $echo  = $args['echo'] ?? true;
    $title = $args['title'] ?? __('Top stories', 'waqya');
    unset($args['echo'], $args['title']);

    $query = waqya_get_slider_query($args);

    if (! $query->have_posts()) {
        return [];
    }

    $ids = wp_list_pluck($query->posts, 'ID');
    $ids = array_map('intval', $ids);

    if (! $echo) {
        return $ids;
    }

    $query->rewind_posts();

    set_query_var('waqya_slider_title', $title);
    set_query_var('waqya_slider_query', $query);

    get_template_part('template-parts/slider/post', 'slider');

    wp_reset_postdata();

    return $ids;
}

/**
 * Exclude slider posts from category archive main query (page 1).
 */
function waqya_exclude_slider_from_category_query(WP_Query $query): void
{
    if (is_admin() || ! $query->is_main_query() || ! $query->is_category() || $query->is_paged()) {
        return;
    }

    $exclude = waqya_category_slider_exclude_ids($query);
    if ($exclude === []) {
        return;
    }

    $not_in = array_filter(array_merge(
        (array) $query->get('post__not_in'),
        $exclude
    ));
    $query->set('post__not_in', $not_in);
    $query->set('posts_per_page', 12);
}
add_action('pre_get_posts', 'waqya_exclude_slider_from_category_query', 15);
