<?php
/**
 * Waqya brand — name, meaning, and document titles
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * The meaning of Waqya in English.
 */
function waqya_brand_meaning(): string
{
    return __('The Incident', 'waqya');
}

/**
 * Full brand lockup for titles and meta: "Waqya — The Incident".
 */
function waqya_brand_full_name(): string
{
    return sprintf(
        /* translators: %1$s: brand name, %2$s: meaning */
        __('%1$s — %2$s', 'waqya'),
        waqya_site_name(),
        waqya_brand_meaning()
    );
}

/**
 * Primary site tagline (used when WordPress tagline is empty).
 */
function waqya_brand_tagline(): string
{
    return __('The incident is the story. We unpack what happened—and what it means next.', 'waqya');
}

/**
 * One-line naming story for masthead and footer.
 */
function waqya_brand_story_short(): string
{
    return __('Named for the moment the news breaks—Waqya means The Incident.', 'waqya');
}

/**
 * Homepage naming story (why Waqya).
 */
function waqya_brand_story_long(): string
{
    return __(
        'Every major story begins as an incident—a flash point where facts, stakes, and consequences collide. '
        . 'Waqya is named for that moment. In Arabic, waqya (وَقْعَة) means the incident: not the rumour, not the spin, but the event itself. '
        . 'We publish clear-eyed commentary on what happened, who it affects, and what comes next.',
        'waqya'
    );
}

/**
 * Eyebrow above the homepage story block.
 */
function waqya_brand_story_eyebrow(): string
{
    return __('Why Waqya?', 'waqya');
}

/**
 * @param array<string, string|null> $parts
 * @return array<string, string|null>
 */
function waqya_document_title_parts(array $parts): array
{
    $parts['site'] = waqya_brand_full_name();

    if (is_front_page() && is_home()) {
        $parts['title'] = waqya_brand_meaning();
    }

    return $parts;
}
add_filter('document_title_parts', 'waqya_document_title_parts');

/**
 * @param string $title
 */
function waqya_pre_get_document_title(string $title): string
{
    if (is_front_page()) {
        return waqya_brand_full_name() . ' | ' . waqya_brand_tagline();
    }

    return $title;
}
add_filter('pre_get_document_title', 'waqya_pre_get_document_title', 20);

/**
 * Open Graph / general meta description on front page.
 */
function waqya_brand_meta_description(): void
{
    if (! is_front_page()) {
        return;
    }

    $description = waqya_brand_story_short() . ' ' . waqya_brand_tagline();

    printf(
        '<meta name="description" content="%s" />' . "\n",
        esc_attr(wp_strip_all_tags($description))
    );
}
add_action('wp_head', 'waqya_brand_meta_description', 1);
