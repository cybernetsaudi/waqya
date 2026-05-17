<?php
/**
 * Subscriber database table.
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

final class Waqya_Subscribers_DB
{
    public const TABLE = 'waqya_subscribers';

    public static function table_name(): string
    {
        global $wpdb;
        return $wpdb->prefix . self::TABLE;
    }

    public static function install(): void
    {
        self::create_table();
        Waqya_Subscribers_Digest::schedule();
        update_option('waqya_subscribers_db_version', '1.0.0');
    }

    public static function maybe_upgrade(): void
    {
        if (get_option('waqya_subscribers_db_version') !== '1.0.0') {
            self::create_table();
            update_option('waqya_subscribers_db_version', '1.0.0');
        }
    }

    private static function create_table(): void
    {
        global $wpdb;

        $table   = self::table_name();
        $charset = $wpdb->get_charset_collate();

        $sql = "CREATE TABLE {$table} (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
            email VARCHAR(190) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            consent_digest TINYINT(1) NOT NULL DEFAULT 0,
            consent_text VARCHAR(32) NOT NULL DEFAULT 'digest-v1',
            consented_at DATETIME NULL,
            confirm_token CHAR(64) NOT NULL,
            unsubscribe_token CHAR(64) NOT NULL,
            category_ids LONGTEXT NULL,
            created_at DATETIME NOT NULL,
            confirmed_at DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY email (email),
            KEY status (status)
        ) {$charset};";

        require_once ABSPATH . 'wp-admin/includes/upgrade.php';
        dbDelta($sql);
    }
}
