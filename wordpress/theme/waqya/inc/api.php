<?php
/**
 * Public JSON feed for partners (B2B wire).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

function waqya_register_rest_routes(): void
{
    register_rest_route('waqya/v1', '/feed', [
        'methods'             => 'GET',
        'permission_callback' => '__return_true',
        'callback'            => static function (WP_REST_Request $request) {
            $per_page = min(50, max(1, (int) $request->get_param('per_page') ?: 20));
            $cat      = sanitize_title((string) $request->get_param('desk'));

            $args = [
                'post_type'      => 'post',
                'post_status'    => 'publish',
                'posts_per_page' => $per_page,
                'orderby'        => 'date',
                'order'          => 'DESC',
            ];
            if ($cat !== '') {
                $term = get_category_by_slug($cat);
                if ($term) {
                    $args['cat'] = (int) $term->term_id;
                }
            }

            $posts = get_posts($args);
            $items = [];
            foreach ($posts as $post) {
                $cats = get_the_category($post->ID);
                $desk = 'default';
                if (! empty($cats)) {
                    $desk = $cats[0]->slug;
                }
                $items[] = [
                    'id'          => $post->ID,
                    'title'       => get_the_title($post),
                    'url'         => get_permalink($post),
                    'excerpt'     => wp_strip_all_tags(get_the_excerpt($post)),
                    'published'   => get_post_time('c', true, $post),
                    'modified'    => get_post_modified_time('c', true, $post),
                    'desk'        => $desk,
                    'headline_ar' => (string) get_post_meta($post->ID, '_waqya_headline_ar', true),
                    'headline_ur' => (string) get_post_meta($post->ID, '_waqya_headline_ur', true),
                ];
            }

            return new WP_REST_Response([
                'site'  => waqya_site_name(),
                'url'   => home_url('/'),
                'items' => $items,
            ], 200);
        },
    ]);
}
add_action('rest_api_init', 'waqya_register_rest_routes');
