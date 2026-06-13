<?php
/**
 * Trust & policy pages — config, content, and layout helpers.
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
function waqya_trust_pages_registry(): array
{
    static $registry = null;

    if ($registry === null) {
        require_once WAQYA_DIR . '/inc/trust-pages-registry.php';
        $registry = waqya_trust_pages_registry_data();
    }

    return $registry;
}

/**
 * @return string[]
 */
function waqya_trust_page_slugs(): array
{
    return array_keys(waqya_trust_pages_registry());
}

function waqya_is_trust_page(?int $post_id = null): bool
{
    $post_id = $post_id ?? get_the_ID();
    if (! $post_id || get_post_type($post_id) !== 'page') {
        return false;
    }

    return in_array(get_post_field('post_name', $post_id), waqya_trust_page_slugs(), true);
}

/**
 * @return array<string, string>|null
 */
function waqya_trust_page_config(?int $post_id = null): ?array
{
    $post_id = $post_id ?? get_the_ID();
    if (! $post_id) {
        return null;
    }

    $slug = get_post_field('post_name', $post_id);
    $all  = waqya_trust_pages_registry();

    return $all[$slug] ?? null;
}

function waqya_trust_page_content_html(string $slug): string
{
    $path = WAQYA_DIR . '/content/trust-pages/' . $slug . '.html';
    if (! is_readable($path)) {
        return '';
    }

    $html = trim((string) file_get_contents($path));
    return $html;
}

/**
 * Other trust pages for cross-navigation (exclude current).
 *
 * @return array<int, array{slug: string, title: string, dek: string}>
 */
function waqya_trust_page_siblings(string $current_slug): array
{
    $out = [];
    foreach (waqya_trust_pages_registry() as $slug => $meta) {
        if ($slug === $current_slug) {
            continue;
        }
        $out[] = [
            'slug'  => $slug,
            'title' => $meta['title'] ?? $slug,
            'dek'   => $meta['dek'] ?? '',
        ];
    }
    return $out;
}
