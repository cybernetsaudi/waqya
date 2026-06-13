<?php
/**
 * Hostinger SMTP for wp_mail() — credentials from WP options (set via automation/setup_wordpress_mail.py).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Configure PHPMailer when SMTP options are present.
 *
 * @param PHPMailer\PHPMailer\PHPMailer $phpmailer
 */
function waqya_smtp_configure($phpmailer): void
{
    $user = (string) get_option('waqya_smtp_user', '');
    $pass = (string) get_option('waqya_smtp_pass', '');
    if ($user === '' || $pass === '') {
        return;
    }

    $host = (string) get_option('waqya_smtp_host', 'smtp.hostinger.com');
    $port = (int) get_option('waqya_smtp_port', 465);
    $secure = (string) get_option('waqya_smtp_secure', 'ssl');

    $phpmailer->isSMTP();
    $phpmailer->Host       = $host;
    $phpmailer->SMTPAuth   = true;
    $phpmailer->Port       = $port;
    $phpmailer->Username   = $user;
    $phpmailer->Password   = $pass;
    $phpmailer->SMTPSecure = $secure;
    $phpmailer->From       = (string) get_option('waqya_mail_from', $user);
    $phpmailer->FromName   = (string) get_option('waqya_mail_from_name', 'Waqya');
}
add_action('phpmailer_init', 'waqya_smtp_configure');

/**
 * Default From for all site mail (digests, confirmations).
 */
function waqya_mail_from(): string
{
    $from = (string) get_option('waqya_mail_from', '');
    if ($from !== '' && is_email($from)) {
        return $from;
    }

    $user = (string) get_option('waqya_smtp_user', '');
    if ($user !== '' && is_email($user)) {
        return $user;
    }

    return 'hello@waqya.com';
}
add_filter('wp_mail_from', static fn () => waqya_mail_from());

function waqya_mail_from_name(): string
{
    return (string) get_option('waqya_mail_from_name', 'Waqya');
}
add_filter('wp_mail_from_name', static fn () => waqya_mail_from_name());

add_filter('waqya_subscribers_reply_to', static fn () => waqya_mail_from());

/**
 * Ring buffer of recent send attempts (inspect with `wp option get waqya_mail_log --format=json`).
 *
 * @param array<string, mixed> $entry
 */
function waqya_mail_log_append(array $entry): void
{
    $log = get_option('waqya_mail_log', []);
    if (! is_array($log)) {
        $log = [];
    }

    array_unshift($log, array_merge(['at' => gmdate('c')], $entry));
    update_option('waqya_mail_log', array_slice($log, 0, 25), false);
}

/**
 * @param array<string, mixed> $mail_data
 */
function waqya_mail_log_succeeded(array $mail_data): void
{
    $to = $mail_data['to'] ?? '';
    if (is_array($to)) {
        $to = implode(', ', $to);
    }

    waqya_mail_log_append([
        'status'  => 'sent',
        'to'      => (string) $to,
        'subject' => (string) ($mail_data['subject'] ?? ''),
    ]);
}
add_action('wp_mail_succeeded', 'waqya_mail_log_succeeded');

/**
 * @param WP_Error $error
 */
function waqya_mail_log_failed(WP_Error $error): void
{
    $data = $error->get_error_data('wp_mail_failed');
    $to   = '';
    $subj = '';
    if (is_array($data)) {
        $to   = is_array($data['to'] ?? '') ? implode(', ', $data['to']) : (string) ($data['to'] ?? '');
        $subj = (string) ($data['subject'] ?? '');
    }

    $message = $error->get_error_message();
    error_log('Waqya wp_mail failed: ' . $message);

    waqya_mail_log_append([
        'status'  => 'failed',
        'to'      => $to,
        'subject' => $subj,
        'error'   => $message,
    ]);
}
add_action('wp_mail_failed', 'waqya_mail_log_failed');
