<?php
/**
 * Subscriber CRUD and tokens.
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

final class Waqya_Subscribers_Service
{
    public static function token(): string
    {
        return bin2hex(random_bytes(32));
    }

    /**
     * @return array<string, mixed>|null
     */
    public static function find_by_email(string $email): ?array
    {
        global $wpdb;
        $row = $wpdb->get_row(
            $wpdb->prepare(
                'SELECT * FROM ' . Waqya_Subscribers_DB::table_name() . ' WHERE email = %s LIMIT 1',
                sanitize_email($email)
            ),
            ARRAY_A
        );
        return $row ?: null;
    }

    /**
     * @return array<string, mixed>|null
     */
    public static function find_by_confirm_token(string $token): ?array
    {
        global $wpdb;
        $row = $wpdb->get_row(
            $wpdb->prepare(
                'SELECT * FROM ' . Waqya_Subscribers_DB::table_name() . ' WHERE confirm_token = %s LIMIT 1',
                $token
            ),
            ARRAY_A
        );
        return $row ?: null;
    }

    /**
     * @return array<string, mixed>|null
     */
    public static function find_by_unsubscribe_token(string $token): ?array
    {
        global $wpdb;
        $row = $wpdb->get_row(
            $wpdb->prepare(
                'SELECT * FROM ' . Waqya_Subscribers_DB::table_name() . ' WHERE unsubscribe_token = %s LIMIT 1',
                $token
            ),
            ARRAY_A
        );
        return $row ?: null;
    }

    /**
     * @param int[] $category_ids
     * @return array{ok: bool, message: string, status?: string}
     */
    public static function subscribe(
        string $email,
        bool $consent_digest,
        array $category_ids,
        string $consent_text
    ): array {
        $email = sanitize_email($email);
        if (! is_email($email)) {
            return ['ok' => false, 'message' => __('Please enter a valid email address.', 'waqya-subscribers')];
        }

        if (! $consent_digest) {
            return [
                'ok'      => false,
                'message' => __('You must agree to receive the weekly digest to subscribe.', 'waqya-subscribers'),
            ];
        }

        $category_ids = array_values(array_unique(array_filter(array_map('intval', $category_ids))));
        $cats_json    = wp_json_encode($category_ids);
        $now          = current_time('mysql');
        $existing     = self::find_by_email($email);

        if ($existing && $existing['status'] === 'confirmed') {
            self::merge_categories((int) $existing['id'], $category_ids);
            return [
                'ok'      => true,
                'message' => __('You are already subscribed. Section preferences updated.', 'waqya-subscribers'),
                'status'  => 'confirmed',
            ];
        }

        $confirm_token     = self::token();
        $unsubscribe_token = self::token();

        global $wpdb;
        $table = Waqya_Subscribers_DB::table_name();

        if ($existing) {
            $wpdb->update(
                $table,
                [
                    'status'            => 'pending',
                    'consent_digest'    => 1,
                    'consent_text'      => $consent_text,
                    'consented_at'      => $now,
                    'confirm_token'     => $confirm_token,
                    'unsubscribe_token' => $unsubscribe_token,
                    'category_ids'      => $cats_json,
                ],
                ['id' => (int) $existing['id']],
                ['%s', '%d', '%s', '%s', '%s', '%s', '%s'],
                ['%d']
            );
            $id = (int) $existing['id'];
        } else {
            $wpdb->insert(
                $table,
                [
                    'email'             => $email,
                    'status'            => 'pending',
                    'consent_digest'    => 1,
                    'consent_text'      => $consent_text,
                    'consented_at'      => $now,
                    'confirm_token'     => $confirm_token,
                    'unsubscribe_token' => $unsubscribe_token,
                    'category_ids'      => $cats_json,
                    'created_at'        => $now,
                ],
                ['%s', '%s', '%d', '%s', '%s', '%s', '%s', '%s', '%s']
            );
            $id = (int) $wpdb->insert_id;
        }

        $row = self::find_by_email($email);
        if ($row) {
            Waqya_Subscribers_Actions::send_confirmation_email($row);
        }

        return [
            'ok'      => true,
            'message' => __('Check your inbox to confirm your subscription (link expires in 48 hours).', 'waqya-subscribers'),
            'status'  => 'pending',
        ];
    }

    /**
     * @param int[] $category_ids
     */
    public static function merge_categories(int $id, array $category_ids): void
    {
        global $wpdb;
        $row = $wpdb->get_row(
            $wpdb->prepare('SELECT category_ids FROM ' . Waqya_Subscribers_DB::table_name() . ' WHERE id = %d', $id),
            ARRAY_A
        );
        $existing = [];
        if ($row && ! empty($row['category_ids'])) {
            $decoded = json_decode((string) $row['category_ids'], true);
            if (is_array($decoded)) {
                $existing = array_map('intval', $decoded);
            }
        }
        $merged = array_values(array_unique(array_merge($existing, $category_ids)));
        $wpdb->update(
            Waqya_Subscribers_DB::table_name(),
            ['category_ids' => wp_json_encode($merged)],
            ['id' => $id],
            ['%s'],
            ['%d']
        );
    }

    public static function confirm(string $token): array
    {
        $row = self::find_by_confirm_token($token);
        if (! $row) {
            return ['ok' => false, 'message' => __('This confirmation link is invalid or expired.', 'waqya-subscribers')];
        }

        if ($row['status'] === 'confirmed') {
            return ['ok' => true, 'message' => __('Your subscription is already confirmed.', 'waqya-subscribers')];
        }

        global $wpdb;
        $wpdb->update(
            Waqya_Subscribers_DB::table_name(),
            [
                'status'       => 'confirmed',
                'confirmed_at' => current_time('mysql'),
            ],
            ['id' => (int) $row['id']],
            ['%s', '%s'],
            ['%d']
        );

        return [
            'ok'      => true,
            'message' => __('You are subscribed to the Waqya weekly digest. Thank you.', 'waqya-subscribers'),
        ];
    }

    public static function unsubscribe(string $token): array
    {
        $row = self::find_by_unsubscribe_token($token);
        if (! $row) {
            return ['ok' => false, 'message' => __('Invalid unsubscribe link.', 'waqya-subscribers')];
        }

        global $wpdb;
        $wpdb->update(
            Waqya_Subscribers_DB::table_name(),
            ['status' => 'unsubscribed'],
            ['id' => (int) $row['id']],
            ['%s'],
            ['%d']
        );

        return [
            'ok'      => true,
            'message' => __('You have been unsubscribed from the weekly digest.', 'waqya-subscribers'),
        ];
    }

    /**
     * @return array<int, array<string, mixed>>
     */
    public static function confirmed_subscribers(): array
    {
        global $wpdb;
        return $wpdb->get_results(
            "SELECT * FROM " . Waqya_Subscribers_DB::table_name() . "
             WHERE status = 'confirmed' AND consent_digest = 1",
            ARRAY_A
        ) ?: [];
    }
}
