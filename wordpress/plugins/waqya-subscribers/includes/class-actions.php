<?php
/**
 * Confirmation emails and token URL handlers.
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

final class Waqya_Subscribers_Actions
{
    public static function register(): void
    {
        add_action('template_redirect', [self::class, 'handle_token_links']);
    }

    public static function confirm_url(array $row): string
    {
        return add_query_arg(
            ['waqya_confirm' => $row['confirm_token']],
            home_url('/')
        );
    }

    public static function unsubscribe_url(array $row): string
    {
        return add_query_arg(
            ['waqya_unsubscribe' => $row['unsubscribe_token']],
            home_url('/')
        );
    }

    public static function send_confirmation_email(array $row): void
    {
        $email = $row['email'];
        $confirm = self::confirm_url($row);
        $site = get_bloginfo('name');

        $subject = sprintf(
            /* translators: %s: site name */
            __('Confirm your subscription to %s', 'waqya-subscribers'),
            $site
        );

        $body = sprintf(
            __("Hello,\n\nPlease confirm you want to receive the weekly Waqya digest at this email address.\n\nConfirm: %s\n\nIf you did not request this, ignore this email.\n\n— %s", 'waqya-subscribers'),
            $confirm,
            $site
        );

        $headers = ['Content-Type: text/plain; charset=UTF-8'];
        wp_mail($email, $subject, $body, $headers);
    }

    public static function handle_token_links(): void
    {
        if (isset($_GET['waqya_confirm'])) {
            $token = sanitize_text_field(wp_unslash((string) $_GET['waqya_confirm']));
            $result = Waqya_Subscribers_Service::confirm($token);
            self::render_message_page(
                $result['ok'] ? __('Subscription confirmed', 'waqya-subscribers') : __('Confirmation failed', 'waqya-subscribers'),
                (string) $result['message']
            );
            exit;
        }

        if (isset($_GET['waqya_unsubscribe'])) {
            $token = sanitize_text_field(wp_unslash((string) $_GET['waqya_unsubscribe']));
            $result = Waqya_Subscribers_Service::unsubscribe($token);
            self::render_message_page(
                __('Unsubscribed', 'waqya-subscribers'),
                (string) $result['message']
            );
            exit;
        }
    }

    private static function render_message_page(string $title, string $message): void
    {
        status_header(200);
        nocache_headers();
        ?><!DOCTYPE html>
        <html <?php language_attributes(); ?>>
        <head>
            <meta charset="<?php bloginfo('charset'); ?>">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title><?php echo esc_html($title); ?></title>
            <style>
                body { font-family: system-ui, sans-serif; max-width: 32rem; margin: 4rem auto; padding: 0 1rem; line-height: 1.5; }
                h1 { font-size: 1.5rem; }
                a { color: #b45309; }
            </style>
        </head>
        <body>
            <h1><?php echo esc_html($title); ?></h1>
            <p><?php echo esc_html($message); ?></p>
            <p><a href="<?php echo esc_url(home_url('/')); ?>"><?php esc_html_e('Back to Waqya', 'waqya-subscribers'); ?></a></p>
        </body>
        </html>
        <?php
    }
}
