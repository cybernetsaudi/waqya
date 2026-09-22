<?php
/**
 * RSS feeds tuned for aggregators (Flipboard, Feedly, etc.).
 *
 * Flipboard requires: full content, images ≥400px, and ≥30 items in the feed.
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/** Items per RSS/Atom feed (WordPress default is 10; Flipboard needs ≥30). */
function waqya_posts_per_rss(): int
{
    return (int) apply_filters('waqya_posts_per_rss', 50);
}

add_filter('pre_option_posts_per_rss', static function (): int {
    return waqya_posts_per_rss();
});

/**
 * MRSS namespace for featured images in feed readers.
 */
function waqya_rss2_namespaces(): void
{
    echo 'xmlns:media="http://search.yahoo.com/mrss/"' . "\n";
}
add_action('rss2_ns', 'waqya_rss2_namespaces');

/**
 * Prepend hero image + ensure full post body in feeds.
 */
function waqya_rss_enhance_content(string $content): string
{
    if (! is_feed() || ! in_the_loop()) {
        return $content;
    }

    $post_id = get_the_ID();
    if (! $post_id) {
        return $content;
    }

    $hero = '';
    if (has_post_thumbnail($post_id)) {
        $src = get_the_post_thumbnail_url($post_id, 'large');
        if (is_string($src) && $src !== '') {
            $alt = get_post_meta($post_id, '_wp_attachment_image_alt', true);
            $alt = is_string($alt) && $alt !== '' ? $alt : get_the_title($post_id);
            $hero = sprintf(
                '<figure class="rss-featured-image"><img src="%s" alt="%s" width="1200" /></figure>',
                esc_url($src),
                esc_attr($alt)
            );
        }
    }

    if ($hero !== '' && stripos($content, (string) $src) === false) {
        $content = $hero . $content;
    }

    return $content;
}
add_filter('the_content_feed', 'waqya_rss_enhance_content', 5);
add_filter('the_excerpt_rss', static function (string $excerpt): string {
    $full = get_the_content_feed('rss2');
    return $full !== '' ? $full : $excerpt;
}, 5);

/**
 * media:content + enclosure for featured image (Flipboard / podcast apps).
 */
function waqya_rss2_item_media(): void
{
    if (! has_post_thumbnail()) {
        return;
    }

    $post_id = get_the_ID();
    $meta    = wp_get_attachment_image_src(get_post_thumbnail_id($post_id), 'large');
    if (! is_array($meta) || empty($meta[0])) {
        return;
    }

    $url    = $meta[0];
    $width  = (int) ($meta[1] ?? 0);
    $height = (int) ($meta[2] ?? 0);
    $mime   = get_post_mime_type(get_post_thumbnail_id($post_id)) ?: 'image/jpeg';

  printf(
        '<media:content url="%s" type="%s" medium="image"%s%s />' . "\n",
        esc_url($url),
        esc_attr($mime),
        $width > 0 ? ' width="' . $width . '"' : '',
        $height > 0 ? ' height="' . $height . '"' : ''
    );

    printf(
        '<enclosure url="%s" length="0" type="%s" />' . "\n",
        esc_url($url),
        esc_attr($mime)
    );
}
add_action('rss2_item', 'waqya_rss2_item_media');

/**
 * Ping feed caches after publish so aggregators see new items quickly.
 */
function waqya_bump_feed_last_modified(int $post_id): void
{
    if (wp_is_post_revision($post_id) || wp_is_post_autosave($post_id)) {
        return;
    }
    if (get_post_status($post_id) !== 'publish') {
        return;
    }
    update_option('waqya_feed_last_built', (string) time());
}
add_action('save_post', 'waqya_bump_feed_last_modified', 20);
