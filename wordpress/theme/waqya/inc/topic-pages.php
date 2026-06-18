<?php
/**
 * Topic hub URLs — /topic/{tag-slug}/ (indexable when enough stories).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

function waqya_topic_rewrite(): void
{
    add_rewrite_rule('^topic/([^/]+)/?$', 'index.php?tag=$matches[1]', 'top');
    add_rewrite_rule('^topic/([^/]+)/page/([0-9]+)/?$', 'index.php?tag=$matches[1]&paged=$matches[2]', 'top');
}
add_action('init', 'waqya_topic_rewrite');

/**
 * @param string $link
 */
function waqya_topic_tag_link(string $link, int $term_id): string
{
    $term = get_tag($term_id);
    if (! $term instanceof WP_Term) {
        return $link;
    }

    return home_url('/topic/' . $term->slug . '/');
}
add_filter('tag_link', 'waqya_topic_tag_link', 10, 2);

/**
 * Minimum posts for a topic hub to be indexed.
 */
function waqya_topic_min_posts_for_index(): int
{
    return (int) apply_filters('waqya_topic_min_posts_for_index', 3);
}

/**
 * URL for the On The Record topic hub.
 */
function waqya_on_the_record_url(): string
{
    return home_url('/topic/on-the-record/');
}

/**
 * On The Record archives must match homepage (meta OR tag).
 */
function waqya_topic_pre_get_posts(WP_Query $query): void
{
    if (is_admin() || ! $query->is_main_query()) {
        return;
    }

    if (! $query->is_tax('post_tag')) {
        return;
    }

    $slug = $query->get('tag');
    if ($slug !== 'on-the-record') {
        return;
    }

    $ids = waqya_on_the_record_post_ids([], 100);
    if ($ids === []) {
        return;
    }

    $query->set('post__in', $ids);
    $query->set('orderby', 'post__in');
    $query->set('posts_per_page', 24);
}
add_action('pre_get_posts', 'waqya_topic_pre_get_posts');
