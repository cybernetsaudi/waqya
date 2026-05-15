<?php
/**
 * Template tags
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Estimated reading time in minutes.
 */
function waqya_reading_time(?int $post_id = null): int
{
    $post_id = $post_id ?? get_the_ID();
    $content = get_post_field('post_content', $post_id);
    $words   = str_word_count(wp_strip_all_tags((string) $content));

    return max(1, (int) ceil($words / 220));
}

/**
 * Post meta line: date and reading time.
 */
function waqya_posted_on(): void
{
    $time = sprintf(
        /* translators: %s: post date */
        esc_html__('Published %s', 'waqya'),
        '<time datetime="' . esc_attr(get_the_date(DATE_W3C)) . '">' . esc_html(get_the_date()) . '</time>'
    );

    $reading = sprintf(
        /* translators: %d: number of minutes */
        esc_html(_n('%d min read', '%d min read', waqya_reading_time(), 'waqya')),
        waqya_reading_time()
    );

    echo '<div class="entry-meta">';
    echo '<span class="entry-meta__date">' . $time . '</span>';
    echo '<span class="entry-meta__sep" aria-hidden="true">·</span>';
    echo '<span class="entry-meta__reading">' . esc_html($reading) . '</span>';
    echo '</div>';
}

/**
 * Category badge for cards and singles.
 */
function waqya_category_badge(): void
{
    $categories = get_the_category();
    if (empty($categories)) {
        return;
    }

    $cat  = $categories[0];
    $slug = sanitize_html_class($cat->slug);

    printf(
        '<a class="badge badge--%s" href="%s">%s</a>',
        esc_attr($slug),
        esc_url(get_category_link($cat)),
        esc_html($cat->name)
    );
}

/**
 * Breadcrumbs for single posts and archives.
 */
function waqya_breadcrumbs(): void
{
    if (is_front_page()) {
        return;
    }

    echo '<nav class="breadcrumbs" aria-label="' . esc_attr__('Breadcrumb', 'waqya') . '">';
    echo '<ol class="breadcrumbs__list">';

    echo '<li class="breadcrumbs__item"><a href="' . esc_url(home_url('/')) . '">' . esc_html__('Home', 'waqya') . '</a></li>';

    if (is_category()) {
        echo '<li class="breadcrumbs__item" aria-current="page">' . esc_html(single_cat_title('', false)) . '</li>';
    } elseif (is_single()) {
        $categories = get_the_category();
        if (! empty($categories)) {
            $cat = $categories[0];
            echo '<li class="breadcrumbs__item"><a href="' . esc_url(get_category_link($cat)) . '">' . esc_html($cat->name) . '</a></li>';
        }
        echo '<li class="breadcrumbs__item breadcrumbs__item--current" aria-current="page">' . esc_html(get_the_title()) . '</li>';
    } elseif (is_search()) {
        echo '<li class="breadcrumbs__item" aria-current="page">' . esc_html__('Search', 'waqya') . '</li>';
    } elseif (is_404()) {
        echo '<li class="breadcrumbs__item" aria-current="page">' . esc_html__('Page not found', 'waqya') . '</li>';
    }

    echo '</ol>';
    echo '</nav>';
}

/**
 * Pagination markup.
 */
function waqya_pagination(): void
{
    global $wp_query;

    if ($wp_query->max_num_pages <= 1) {
        return;
    }

    $links = paginate_links([
        'type'      => 'array',
        'prev_text' => esc_html__('Previous', 'waqya'),
        'next_text' => esc_html__('Next', 'waqya'),
    ]);

    if (empty($links)) {
        return;
    }

    echo '<nav class="pagination" aria-label="' . esc_attr__('Posts navigation', 'waqya') . '"><ul class="pagination__list">';
    foreach ($links as $link) {
        $class = strpos($link, 'current') !== false ? 'pagination__item pagination__item--current' : 'pagination__item';
        echo '<li class="' . esc_attr($class) . '">' . $link . '</li>';
    }
    echo '</ul></nav>';
}
