<?php
/**
 * Trust page metadata (eyebrow, dek, titles).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * @return array<string, array<string, string>>
 */
function waqya_trust_pages_registry_data(): array
{
    return [
        'editorial-policy' => [
            'title'   => 'Editorial Policy',
            'eyebrow' => 'Standards',
            'dek'     => 'How Waqya gathers news, writes commentary, and decides what gets published.',
        ],
        'corrections' => [
            'title'   => 'Corrections',
            'eyebrow' => 'Accuracy',
            'dek'     => 'We fix factual errors quickly and transparently. Here is how to report one.',
        ],
        'about' => [
            'title'   => 'About Waqya',
            'eyebrow' => 'Who we are',
            'dek'     => 'Independent commentary on world news — clear, urgent, and built for readers who want the story behind the headline.',
        ],
        'contact' => [
            'title'   => 'Contact',
            'eyebrow' => 'Reach us',
            'dek'     => 'Corrections, partnerships, press inquiries, and reader feedback.',
        ],
        'privacy-policy' => [
            'title'   => 'Privacy Policy',
            'eyebrow' => 'Your data',
            'dek'     => 'How Waqya collects, uses, and protects personal information — including cookies, analytics, and email subscriptions.',
        ],
    ];
}
