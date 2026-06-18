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
        $attrs = [
            'class'   => $class,
            'loading' => $size === 'waqya-hero' ? 'eager' : 'lazy',
        ];
        if ($size === 'waqya-hero') {
            $attrs['fetchpriority'] = 'high';
            $attrs['decoding']      = 'async';
        }
        if (str_contains($class, 'post-slider__image')) {
            $attrs['sizes'] = '100vw';
        }
        the_post_thumbnail($size, $attrs);
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
/**
 * Decode HTML entities (&#8217;, &amp;#8217;, etc.) for safe display.
 */
function waqya_decode_entities(string $text): string
{
    if ($text === '') {
        return '';
    }

    $out = $text;
    for ($i = 0; $i < 4; $i++) {
        $next = html_entity_decode($out, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        if ($next === $out) {
            break;
        }
        $out = $next;
    }

    return $out;
}

/**
 * Plain post title for templates (decoded, escaped).
 */
function waqya_the_title(?int $post_id = null): void
{
    $post_id = $post_id ?? get_the_ID();
    echo esc_html(waqya_decode_entities(get_the_title($post_id)));
}

/**
 * Plain excerpt for cards and deks (decoded, escaped).
 */
function waqya_the_excerpt(int $word_limit = 0, ?int $post_id = null): void
{
    $post_id = $post_id ?? get_the_ID();
    $text    = waqya_decode_entities(get_the_excerpt($post_id));
    if ($word_limit > 0) {
        $text = wp_trim_words($text, $word_limit);
    }
    echo esc_html($text);
}

/**
 * @param string[] $filters
 */
function waqya_register_entity_decode_filters(): void
{
    $filters = [
        'the_title',
        'get_the_title',
        'the_excerpt',
        'get_the_excerpt',
        'wp_trim_excerpt',
    ];
    foreach ($filters as $filter) {
        add_filter($filter, 'waqya_decode_entities', 99);
    }
}
add_action('init', 'waqya_register_entity_decode_filters');

/**
 * Desk label for article byline (from pipeline meta or category).
 */
function waqya_desk_byline_label(): string
{
    $label = get_post_meta(get_the_ID(), '_waqya_iptc_label', true);
    if (is_string($label) && $label !== '') {
        return $label;
    }

    $categories = get_the_category();
    if (! empty($categories)) {
        return $categories[0]->name;
    }

    return '';
}

function waqya_site_tagline(): string
{
    $tagline = get_bloginfo('description');
    if ($tagline !== '' && stripos($tagline, 'ai-powered') === false) {
        return $tagline;
    }

    return waqya_brand_tagline();
}

/**
 * Repair pipeline headings where a paragraph was merged into h2 (single newline).
 */
function waqya_fix_broken_headings(string $content): string
{
    if ($content === '' || stripos($content, '<h2') === false) {
        return $content;
    }

    return (string) preg_replace_callback(
        '#<h2([^>]*)>(.*?)</h2>#is',
        static function (array $matches): string {
            $attrs = $matches[1];
            $inner = $matches[2];
            if (! preg_match('#<br\s*/?>#i', $inner)) {
                return $matches[0];
            }

            $parts = preg_split('#<br\s*/?>#i', $inner, 2);
            $title = trim(wp_strip_all_tags($parts[0] ?? ''));
            $rest = trim(wp_strip_all_tags($parts[1] ?? ''));
            if ($title === '') {
                return $matches[0];
            }

            $out = '<h2' . $attrs . '>' . esc_html($title) . '</h2>';
            if ($rest !== '') {
                $out .= '<p>' . esc_html($rest) . '</p>';
            }
            return $out;
        },
        $content
    );
}
