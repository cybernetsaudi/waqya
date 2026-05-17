<?php
/**
 * Load editorial taxonomy from config/categories.json
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * @return array<string, mixed>|null
 */
function waqya_categories_config(): ?array
{
    static $config = null;

    if ($config !== null) {
        return $config ?: null;
    }

    $path = WAQYA_DIR . '/config/categories.json';
    if (! is_readable($path)) {
        $config = [];
        return null;
    }

    $decoded = json_decode((string) file_get_contents($path), true);
    $config  = is_array($decoded) ? $decoded : [];

    return $config ?: null;
}

/**
 * @return array<int, array{id: string, label: string, items: string[]}>
 */
function waqya_menu_groups(): array
{
    $config = waqya_categories_config();
    if (! $config || empty($config['menu']) || ! is_array($config['menu'])) {
        return [];
    }

    return $config['menu'];
}

/**
 * @return array<string, array<string, mixed>>
 */
function waqya_primary_categories(): array
{
    $config = waqya_categories_config();
    if (! $config || empty($config['primary_categories']) || ! is_array($config['primary_categories'])) {
        return [];
    }

    return $config['primary_categories'];
}

/**
 * @return array<string, mixed>|null
 */
function waqya_primary_category(string $key): ?array
{
    $all = waqya_primary_categories();

    return $all[$key] ?? null;
}

/**
 * Category term IDs for a menu group (News Desk, Regions, Topics).
 *
 * @return int[]
 */
function waqya_menu_group_term_ids(string $group_id): array
{
    $ids = [];
    foreach (waqya_menu_groups() as $group) {
        if (($group['id'] ?? '') !== $group_id) {
            continue;
        }
        foreach ($group['items'] ?? [] as $key) {
            $meta = waqya_primary_category((string) $key);
            $slug = $meta['slug'] ?? (string) $key;
            $term = get_category_by_slug($slug);
            if ($term) {
                $ids[] = (int) $term->term_id;
            }
        }
        break;
    }

    return array_values(array_unique($ids));
}

/**
 * Archive URL for a primary category key or slug.
 */
function waqya_category_url(string $key_or_slug): string
{
    $meta = waqya_primary_category($key_or_slug);
    $slug = $meta['slug'] ?? $key_or_slug;
    $term = get_category_by_slug($slug);

    return $term ? get_category_link($term) : home_url('/category/' . $slug . '/');
}

/**
 * Label for current category from JSON when available.
 */
function waqya_category_label(WP_Term $term): string
{
    foreach (waqya_primary_categories() as $meta) {
        if (($meta['slug'] ?? '') === $term->slug) {
            return (string) ($meta['label'] ?? $term->name);
        }
    }

    return $term->name;
}

/**
 * Description for category archive from JSON.
 */
function waqya_category_description(WP_Term $term): string
{
    $native = term_description($term->term_id, 'category');
    if ($native !== '') {
        return $native;
    }

    foreach (waqya_primary_categories() as $meta) {
        if (($meta['slug'] ?? '') === $term->slug) {
            return (string) ($meta['description'] ?? '');
        }
    }

    return '';
}
