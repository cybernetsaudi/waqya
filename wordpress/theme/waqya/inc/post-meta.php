<?php
/**
 * Post meta exposed to REST for automation.
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * @return list<string>
 */
function waqya_automation_meta_keys(): array
{
    return [
        '_waqya_format',
        '_waqya_interview_tone',
        '_waqya_is_breaking',
        '_waqya_developing',
        '_waqya_update_log',
        '_waqya_quality_score',
        '_waqya_primary_category',
        '_waqya_source_url',
        '_waqya_featured_home',
    ];
}

function waqya_register_automation_meta(): void
{
    foreach (waqya_automation_meta_keys() as $key) {
        register_post_meta(
            'post',
            $key,
            [
                'single'            => true,
                'type'              => 'string',
                'show_in_rest'      => true,
                'auth_callback'     => static function (): bool {
                    return current_user_can('edit_posts');
                },
            ]
        );
    }
}
add_action('init', 'waqya_register_automation_meta', 20);
