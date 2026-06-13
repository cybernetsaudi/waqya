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
 * UTC unix timestamp for publish or modified (GMT storage).
 */
function waqya_post_gmt_time(string $which = 'publish', ?int $post_id = null): int
{
    $post_id = $post_id ?? get_the_ID();
    if ($which === 'modified') {
        return (int) get_post_modified_time('U', true, $post_id);
    }

    return (int) get_post_time('U', true, $post_id);
}

/**
 * Absolute datetime in GMT (newsroom style).
 */
function waqya_format_datetime_gmt(int $timestamp): string
{
    if ($timestamp <= 0) {
        return '';
    }

    return gmdate('j M Y · H:i', $timestamp) . ' GMT';
}

/**
 * Relative time from a GMT unix timestamp.
 */
function waqya_relative_from_gmt(int $timestamp): string
{
    if ($timestamp <= 0) {
        return '';
    }

    $diff = human_time_diff($timestamp, time());

    return sprintf(
        /* translators: %s: human time diff */
        __('%s ago', 'waqya'),
        $diff
    );
}

/**
 * Relative publish time (e.g. "2 hours ago").
 */
function waqya_time_ago(?int $post_id = null): string
{
    return waqya_relative_from_gmt(waqya_post_gmt_time('publish', $post_id));
}

/**
 * Whether modified time is meaningfully after publish.
 */
function waqya_post_was_updated(?int $post_id = null, int $threshold_seconds = 120): bool
{
    $post_id = $post_id ?? get_the_ID();
    $pub     = waqya_post_gmt_time('publish', $post_id);
    $mod     = waqya_post_gmt_time('modified', $post_id);

    return ($mod - $pub) > $threshold_seconds;
}

/**
 * Breaking / developing stories (live-style dateline).
 */
function waqya_is_developing_story(?int $post_id = null): bool
{
    $post_id = $post_id ?? get_the_ID();
    if (has_tag('Breaking', $post_id)) {
        return true;
    }

    if (get_post_meta($post_id, '_waqya_developing', true) === '1') {
        return true;
    }

    return get_post_meta($post_id, '_waqya_is_breaking', true) === '1';
}

/**
 * @return list<array{at: string, note: string}>
 */
function waqya_get_update_log(?int $post_id = null): array
{
    $post_id = $post_id ?? get_the_ID();
    $raw     = (string) get_post_meta($post_id, '_waqya_update_log', true);
    if ($raw === '') {
        return [];
    }

    $decoded = json_decode($raw, true);
    if (! is_array($decoded)) {
        return [];
    }

    $out = [];
    foreach ($decoded as $row) {
        if (! is_array($row)) {
            continue;
        }
        $at   = isset($row['at']) ? (string) $row['at'] : '';
        $note = isset($row['note']) ? (string) $row['note'] : '';
        if ($at !== '' && $note !== '') {
            $out[] = ['at' => $at, 'note' => $note];
        }
    }

    return $out;
}

/**
 * Developing story ribbon on singles.
 */
function waqya_render_developing_ribbon(?int $post_id = null): void
{
    $post_id = $post_id ?? get_the_ID();
    if (! waqya_is_developing_story($post_id)) {
        return;
    }

    echo '<div class="developing-ribbon" role="note">';
    echo '<span class="developing-ribbon__live" aria-hidden="true"></span>';
    echo '<span class="developing-ribbon__label">' . esc_html__('Developing story', 'waqya') . '</span>';
    if (waqya_post_was_updated($post_id)) {
        echo ' <span class="developing-ribbon__updated">';
        echo esc_html(
            sprintf(
                /* translators: %s: GMT datetime */
                __('Last updated %s', 'waqya'),
                waqya_format_datetime_gmt(waqya_post_gmt_time('modified', $post_id))
            )
        );
        echo '</span>';
    }
    echo '</div>';
}

/**
 * Chronological update log for developing posts.
 */
function waqya_render_update_log(?int $post_id = null): void
{
    $post_id = $post_id ?? get_the_ID();
    $log     = waqya_get_update_log($post_id);
    if ($log === [] || ! waqya_is_developing_story($post_id)) {
        return;
    }

    echo '<aside class="update-log" aria-label="' . esc_attr__('Story updates', 'waqya') . '">';
    echo '<h2 class="update-log__title">' . esc_html__('Updates', 'waqya') . '</h2>';
    echo '<ol class="update-log__list">';
    foreach (array_reverse($log) as $row) {
        $ts = strtotime($row['at'] . ' UTC');
        $when = $ts ? waqya_format_datetime_gmt($ts) : esc_html($row['at']);
        echo '<li class="update-log__item">';
        echo '<time class="update-log__time" datetime="' . esc_attr($row['at']) . '">';
        echo esc_html($when);
        echo '</time>';
        echo '<span class="update-log__note">' . esc_html($row['note']) . '</span>';
        echo '</li>';
    }
    echo '</ol>';
    echo '</aside>';
}

/**
 * On The Record interview review format.
 */
function waqya_is_on_the_record(?int $post_id = null): bool
{
    $post_id = $post_id ?? get_the_ID();

    return get_post_meta($post_id, '_waqya_format', true) === 'on_the_record'
        || has_tag('On The Record', $post_id);
}

/**
 * Human label for interview review tone meta.
 */
function waqya_interview_tone_label(?int $post_id = null): string
{
    $post_id = $post_id ?? get_the_ID();
    $tone    = sanitize_key((string) get_post_meta($post_id, '_waqya_interview_tone', true));
    $labels  = [
        'critical'      => __('Critical review', 'waqya'),
        'contradiction' => __('Contradiction watch', 'waqya'),
        'skeptical'     => __('Skeptical take', 'waqya'),
        'encouraging'   => __('Encouraging read', 'waqya'),
        'wry'           => __('Wry review', 'waqya'),
    ];

    return $labels[$tone] ?? '';
}

/**
 * Render visible publish / update timestamps (always GMT).
 *
 * @param string $context card|inline|single|developing
 */
function waqya_render_dateline(string $context = 'card', ?int $post_id = null): void
{
    $post_id   = $post_id ?? get_the_ID();
    $pub_ts    = waqya_post_gmt_time('publish', $post_id);
    $mod_ts    = waqya_post_gmt_time('modified', $post_id);
    $updated   = waqya_post_was_updated($post_id);
    $developing = waqya_is_developing_story($post_id);
    $show_ts   = ($developing && $updated) ? $mod_ts : $pub_ts;
    $absolute  = waqya_format_datetime_gmt($show_ts);
    $relative  = waqya_relative_from_gmt($show_ts);

    if ($absolute === '') {
        return;
    }

    $class = 'dateline dateline--' . sanitize_html_class($context);
    echo '<div class="' . esc_attr($class) . '">';

    if ($context === 'single') {
        echo '<p class="dateline__primary">';
        echo '<span class="dateline__label">' . esc_html__('Published', 'waqya') . '</span> ';
        echo '<time class="dateline__time" datetime="' . esc_attr(gmdate('c', $pub_ts)) . '">';
        echo esc_html(waqya_format_datetime_gmt($pub_ts));
        echo '</time>';
        if ($updated) {
            echo ' <span class="dateline__sep" aria-hidden="true">·</span> ';
            echo '<span class="dateline__label">' . esc_html__('Updated', 'waqya') . '</span> ';
            echo '<time class="dateline__time dateline__time--updated" datetime="' . esc_attr(gmdate('c', $mod_ts)) . '">';
            echo esc_html(waqya_format_datetime_gmt($mod_ts));
            echo '</time>';
        }
        echo '</p>';
        if ($relative !== '') {
            echo '<p class="dateline__relative">' . esc_html($relative) . '</p>';
        }
    } elseif ($context === 'developing') {
        $label = ($developing && $updated) ? __('Updated', 'waqya') : __('Published', 'waqya');
        echo '<time class="dateline__time dateline__time--developing" datetime="' . esc_attr(gmdate('c', $show_ts)) . '">';
        echo esc_html($label . ' ' . $absolute);
        if ($relative !== '') {
            echo ' <span class="dateline__relative">(' . esc_html($relative) . ')</span>';
        }
        echo '</time>';
    } else {
        echo '<time class="dateline__time" datetime="' . esc_attr(gmdate('c', $show_ts)) . '">';
        echo esc_html($absolute);
        echo '</time>';
        if ($relative !== '' && $context !== 'inline') {
            echo ' <span class="dateline__relative">' . esc_html($relative) . '</span>';
        }
    }

    echo '</div>';
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
 * Category badge + Follow on single posts (requires Waqya Subscribers plugin).
 */
function waqya_render_category_follow(): void
{
    if (class_exists('Waqya_Subscribers_Frontend')) {
        Waqya_Subscribers_Frontend::category_follow_row();
        return;
    }
    waqya_category_badge();
}

/**
 * Category badge for cards and singles.
 */
function waqya_category_badge(bool $link = true): void
{
    $categories = get_the_category();
    if (empty($categories)) {
        return;
    }

    $cat  = $categories[0];
    $slug = sanitize_html_class($cat->slug);
    $name = esc_html($cat->name);

    if ($link) {
        printf(
            '<a class="badge badge--%s" href="%s">%s</a>',
            esc_attr($slug),
            esc_url(get_category_link($cat)),
            $name
        );
        return;
    }

    printf('<span class="badge badge--%s">%s</span>', esc_attr($slug), $name);
}

/**
 * Breadcrumbs for single posts and archives.
 */
function waqya_breadcrumbs(): void
{
    echo '<nav class="breadcrumbs" aria-label="' . esc_attr__('Breadcrumb', 'waqya') . '">';
    echo '<ol class="breadcrumbs__list">';

    echo '<li class="breadcrumbs__item"><a href="' . esc_url(home_url('/')) . '">' . esc_html__('Home', 'waqya') . '</a></li>';

    if (is_category()) {
        echo '<li class="breadcrumbs__item" aria-current="page">' . esc_html(single_cat_title('', false)) . '</li>';
    } elseif (is_page()) {
        echo '<li class="breadcrumbs__item breadcrumbs__item--current" aria-current="page">' . esc_html(get_the_title()) . '</li>';
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
        'add_args'  => function_exists('waqya_date_filter_pagination_args')
            ? waqya_date_filter_pagination_args()
            : [],
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
