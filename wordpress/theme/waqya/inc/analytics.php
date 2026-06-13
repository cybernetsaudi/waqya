<?php
/**
 * Analytics configuration — scripts load only after consent (see inc/consent.php).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Plausible domain is read by consent.js; set via wp option waqya_plausible_domain
 * or automation/setup_wordpress_mail.py (PLAUSIBLE_DOMAIN in .env).
 */
