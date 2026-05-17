<?php
/**
 * Plugin Name: Waqya Subscribers
 * Description: GDPR-friendly weekly digest subscriptions and section follows (double opt-in).
 * Version: 1.0.0
 * Author: Waqya
 * Text Domain: waqya-subscribers
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

define('WAQYA_SUB_VERSION', '1.0.0');
define('WAQYA_SUB_DIR', plugin_dir_path(__FILE__));
define('WAQYA_SUB_URI', plugin_dir_url(__FILE__));
define('WAQYA_SUB_CONSENT_VERSION', 'digest-v1');

require_once WAQYA_SUB_DIR . 'includes/class-db.php';
require_once WAQYA_SUB_DIR . 'includes/class-subscriber-service.php';
require_once WAQYA_SUB_DIR . 'includes/class-rest.php';
require_once WAQYA_SUB_DIR . 'includes/class-actions.php';
require_once WAQYA_SUB_DIR . 'includes/class-digest.php';
require_once WAQYA_SUB_DIR . 'includes/class-frontend.php';

final class Waqya_Subscribers_Plugin
{
    public static function init(): void
    {
        register_activation_hook(__FILE__, [Waqya_Subscribers_DB::class, 'install']);
        register_deactivation_hook(__FILE__, [Waqya_Subscribers_Digest::class, 'unschedule']);

        add_action('plugins_loaded', [self::class, 'boot']);
    }

    public static function boot(): void
    {
        Waqya_Subscribers_DB::maybe_upgrade();
        Waqya_Subscribers_REST::register();
        Waqya_Subscribers_Actions::register();
        Waqya_Subscribers_Digest::register();
        Waqya_Subscribers_Frontend::register();
    }
}

Waqya_Subscribers_Plugin::init();
