<?php
/**
 * Plugin Name: Waqya Yoast REST sync
 * Description: Ensures Yoast SEO meta from REST/API updates is visible in the editor and indexables.
 */

declare(strict_types=1);

if (!defined('ABSPATH')) {
    exit;
}

/**
 * @return list<string>
 */
function waqya_yoast_meta_keys(): array
{
    return [
        '_yoast_wpseo_focuskw',
        '_yoast_wpseo_title',
        '_yoast_wpseo_metadesc',
    ];
}

function waqya_register_yoast_rest_meta(): void
{
    foreach (waqya_yoast_meta_keys() as $key) {
        if (metadata_exists('post', 0, $key)) {
            // Yoast may already register; register_post_meta is idempotent for same args.
        }
        register_post_meta(
            'post',
            $key,
            [
                'single'       => true,
                'type'         => 'string',
                'show_in_rest' => true,
                'auth_callback' => static function (): bool {
                    return current_user_can('edit_posts');
                },
            ]
        );
        register_post_meta(
            'page',
            $key,
            [
                'single'       => true,
                'type'         => 'string',
                'show_in_rest' => true,
                'auth_callback' => static function (): bool {
                    return current_user_can('edit_pages');
                },
            ]
        );
    }
}
add_action('init', 'waqya_register_yoast_rest_meta', 20);

/**
 * Rebuild Yoast indexables after automation writes meta via REST.
 *
 * @param WP_Post         $post
 * @param WP_REST_Request $request
 */
function waqya_yoast_after_rest_save($post, $request): void
{
    if (!defined('WPSEO_VERSION') || !($post instanceof WP_Post)) {
        return;
    }
    if (!$request instanceof WP_REST_Request) {
        return;
    }

    $meta = $request->get_param('meta');
    if (!is_array($meta)) {
        return;
    }

    $keys = waqya_yoast_meta_keys();
    if (!array_intersect(array_keys($meta), $keys)) {
        return;
    }

    clean_post_cache($post->ID);

    // Rebuild Yoast indexables when meta is written via REST (no deprecated APIs).
    if (function_exists('wpseo_get_service')) {
        try {
            $builder = wpseo_get_service('indexable-builder');
            if ($builder && method_exists($builder, 'build')) {
                $builder->build($post, ['author_id' => (int) $post->post_author]);
            }
        } catch (Throwable $e) {
            // Fall through to legacy hook.
        }
    }
    do_action('wpseo_save_post', $post->ID);
}
add_action('rest_after_insert_post', 'waqya_yoast_after_rest_save', 20, 2);
add_action('rest_after_insert_page', 'waqya_yoast_after_rest_save', 20, 2);
