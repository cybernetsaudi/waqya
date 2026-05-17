<?php
/**
 * REST API for subscriptions.
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

final class Waqya_Subscribers_REST
{
    public static function register(): void
    {
        add_action('rest_api_init', [self::class, 'routes']);
    }

    public static function routes(): void
    {
        register_rest_route(
            'waqya/v1',
            '/subscribe',
            [
                'methods'             => 'POST',
                'callback'            => [self::class, 'subscribe'],
                'permission_callback' => [self::class, 'public_rate_limited'],
            ]
        );
    }

    public static function public_rate_limited(): bool
    {
        $ip = self::client_ip();
        $key = 'waqya_sub_rl_' . md5($ip);
        $count = (int) get_transient($key);
        if ($count >= 8) {
            return false;
        }
        set_transient($key, $count + 1, 15 * MINUTE_IN_SECONDS);
        return true;
    }

    private static function client_ip(): string
    {
        foreach (['HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR'] as $key) {
            if (! empty($_SERVER[$key])) {
                $ip = sanitize_text_field(wp_unslash((string) $_SERVER[$key]));
                if (str_contains($ip, ',')) {
                    $ip = trim(explode(',', $ip)[0]);
                }
                return $ip;
            }
        }
        return '0.0.0.0';
    }

    public static function subscribe(WP_REST_Request $request): WP_REST_Response
    {
        if (! wp_verify_nonce((string) $request->get_header('X-WP-Nonce'), 'wp_rest')) {
            return new WP_REST_Response(
                ['ok' => false, 'message' => __('Security check failed. Refresh the page and try again.', 'waqya-subscribers')],
                403
            );
        }

        // Honeypot — bots fill hidden field
        if ($request->get_param('website')) {
            return new WP_REST_Response(['ok' => true, 'message' => __('Thanks.', 'waqya-subscribers')], 200);
        }

        $email = (string) $request->get_param('email');
        $consent = (bool) $request->get_param('consent_digest');
        $categories = $request->get_param('category_ids');
        if (! is_array($categories)) {
            $categories = [];
        }

        $result = Waqya_Subscribers_Service::subscribe(
            $email,
            $consent,
            $categories,
            WAQYA_SUB_CONSENT_VERSION
        );

        return new WP_REST_Response($result, $result['ok'] ? 200 : 400);
    }
}
