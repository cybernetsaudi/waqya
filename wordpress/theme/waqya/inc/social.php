<?php
/**
 * Open Graph and Twitter Card tags for articles.
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

function waqya_social_meta(): void
{
    if (! is_singular('post')) {
        return;
    }

    $title = wp_strip_all_tags(get_the_title());
    $desc  = has_excerpt() ? get_the_excerpt() : wp_trim_words(get_the_content(), 35);
    $desc  = wp_strip_all_tags($desc);
    $url   = get_permalink();
    $image = get_the_post_thumbnail_url(null, 'large') ?: '';
    $desk  = waqya_desk_byline_label();
    $pub   = get_post_time('c', true);
    $mod   = get_post_modified_time('c', true);

    $tags = [
        'og:type'                 => 'article',
        'og:title'                => $title,
        'og:description'          => $desc,
        'og:url'                  => $url,
        'og:site_name'            => waqya_site_name(),
        'article:published_time'  => $pub,
        'article:modified_time'   => $mod,
        'twitter:card'            => $image !== '' ? 'summary_large_image' : 'summary',
        'twitter:title'           => $title,
        'twitter:description'     => $desc,
    ];
    if ($desk !== '') {
        $tags['article:section'] = $desk;
        $tags['twitter:label1'] = __('Desk', 'waqya');
        $tags['twitter:data1']  = $desk;
    }
    $gmt_label = waqya_format_datetime_gmt((int) get_post_time('U', true));
    if ($gmt_label !== '') {
        $tags['twitter:label2'] = __('Published (GMT)', 'waqya');
        $tags['twitter:data2']  = $gmt_label;
    }
    if ($image !== '') {
        $tags['og:image'] = $image;
        $tags['twitter:image'] = $image;
    }

    foreach ($tags as $property => $content) {
        if ($content === '') {
            continue;
        }
        $attr = str_starts_with($property, 'twitter:') ? 'name' : 'property';
        printf(
            '<meta %s="%s" content="%s" />' . "\n",
            esc_attr($attr),
            esc_attr($property),
            esc_attr($content)
        );
    }
}
add_action('wp_head', 'waqya_social_meta', 4);
