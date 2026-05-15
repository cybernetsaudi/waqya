<?php
/**
 * Theme helpers
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Category slug for the current post (or default).
 */
function waqya_post_category_slug(): string
{
    $categories = get_the_category();
    if (empty($categories)) {
        return 'default';
    }

    $slug = $categories[0]->slug;
    if ($slug === 'uncategorized') {
        return 'default';
    }

    return $slug;
}

/**
 * IDs to exclude from editorial queries (uncategorized + optional list).
 *
 * @param int[] $extra
 * @return int[]
 */
function waqya_excluded_post_ids(array $extra = []): array
{
    $exclude = array_map('intval', $extra);
    $default = get_option('default_category');
    if ($default) {
        $junk = get_posts([
            'category'       => (int) $default,
            'posts_per_page' => 20,
            'fields'         => 'ids',
            'post_status'    => 'publish',
        ]);
        $exclude = array_merge($exclude, $junk);
    }

    return array_values(array_unique(array_filter($exclude)));
}

/**
 * Render featured image or a category-colored placeholder.
 */
function waqya_the_thumbnail(string $size = 'waqya-card', string $class = ''): void
{
    if (has_post_thumbnail()) {
        the_post_thumbnail($size, [
            'class'   => $class,
            'loading' => $size === 'waqya-hero' ? 'eager' : 'lazy',
        ]);
        return;
    }

    $slug  = waqya_post_category_slug();
    $title = get_the_title();
    $initial = $title !== '' ? mb_strtoupper(mb_substr($title, 0, 1)) : 'W';

    printf(
        '<div class="thumbnail-placeholder thumbnail-placeholder--%1$s %2$s" aria-hidden="true"><span class="thumbnail-placeholder__letter">%3$s</span></div>',
        esc_attr($slug),
        esc_attr($class),
        esc_html($initial)
    );
}

/**
 * Site display name for masthead/footer.
 */
function waqya_site_name(): string
{
    $name = get_bloginfo('name');
    if ($name === '' || stripos($name, 'waqya.com') !== false) {
        return 'Waqya';
    }

    return $name;
}

/**
 * Site tagline with sensible default.
 */
function waqya_site_tagline(): string
{
    $tagline = get_bloginfo('description');
    if ($tagline !== '') {
        return $tagline;
    }

    return __('Independent news commentary', 'waqya');
}
