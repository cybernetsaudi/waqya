<?php
/**
 * Time-period filters for category and archive listings.
 *
 * URL: ?when=today|week|month|year (omit or when=all for no restriction)
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Registered period slugs.
 *
 * @return array<string, string> slug => label
 */
function waqya_date_period_choices(): array
{
    return [
        'today' => __('Today', 'waqya'),
        'week'  => __('This week', 'waqya'),
        'month' => __('This month', 'waqya'),
        'year'  => __('This year', 'waqya'),
        'all'   => __('All time', 'waqya'),
    ];
}

/**
 * Active period slug, or empty when unrestricted.
 */
function waqya_get_date_period(): string
{
    static $period = null;

    if ($period !== null) {
        return $period;
    }

    $raw = isset($_GET['when']) ? sanitize_key((string) wp_unslash($_GET['when'])) : '';
    $choices = waqya_date_period_choices();

    if ($raw === '' || $raw === 'all' || ! isset($choices[$raw])) {
        $period = '';
        return $period;
    }

    $period = $raw;
    return $period;
}

/**
 * Whether the current view supports date filtering.
 */
function waqya_date_filter_supported(): bool
{
    return is_category() || is_tag() || is_search() || is_author() || is_date() || is_archive();
}

/**
 * Build date_query args for a period (site timezone).
 *
 * @return array<int, array<string, mixed>>
 */
function waqya_date_period_query(string $period): array
{
    if ($period === '' || $period === 'all') {
        return [];
    }

    $tz  = wp_timezone();
    $now = new DateTimeImmutable('now', $tz);

    switch ($period) {
        case 'today':
            $start = $now->setTime(0, 0, 0);
            return [
                [
                    'year'      => (int) $start->format('Y'),
                    'month'     => (int) $start->format('m'),
                    'day'       => (int) $start->format('d'),
                    'inclusive' => true,
                ],
            ];

        case 'week':
            $start_of_week = (int) get_option('start_of_week', 1);
            $dow           = (int) $now->format('w');
            $days_back     = ($dow - $start_of_week + 7) % 7;
            $start         = $now->modify("-{$days_back} days")->setTime(0, 0, 0);
            return [
                [
                    'after'     => $start->format('Y-m-d H:i:s'),
                    'inclusive' => true,
                    'column'    => 'post_date',
                ],
            ];

        case 'month':
            $start = $now->modify('first day of this month')->setTime(0, 0, 0);
            return [
                [
                    'after'     => $start->format('Y-m-d H:i:s'),
                    'inclusive' => true,
                    'column'    => 'post_date',
                ],
            ];

        case 'year':
            $start = $now->setDate((int) $now->format('Y'), 1, 1)->setTime(0, 0, 0);
            return [
                [
                    'after'     => $start->format('Y-m-d H:i:s'),
                    'inclusive' => true,
                    'column'    => 'post_date',
                ],
            ];

        default:
            return [];
    }
}

/**
 * Human-readable summary of the active filter.
 */
function waqya_date_period_summary(): string
{
    $period = waqya_get_date_period();
    if ($period === '') {
        return '';
    }

    $choices = waqya_date_period_choices();
    return $choices[$period] ?? '';
}

/**
 * Filter URL for the current archive, preserving path and other query args.
 */
function waqya_date_filter_url(string $period): string
{
    $base = '';
    if (is_category()) {
        $term = get_queried_object();
        $base = ($term instanceof WP_Term) ? get_category_link($term) : '';
    } elseif (is_tag()) {
        $term = get_queried_object();
        $base = ($term instanceof WP_Term) ? get_tag_link($term) : '';
    } elseif (is_search()) {
        $base = get_search_link(get_search_query(false));
    } elseif (is_author()) {
        $base = get_author_posts_url((int) get_queried_object_id());
    } else {
        $base = get_pagenum_link(1, false);
    }

    if ($base === '' || is_wp_error($base)) {
        $base = home_url(add_query_arg([], ''));
    }

    $url = remove_query_arg(['when', 'paged'], $base);

    if ($period !== '' && $period !== 'all') {
        $url = add_query_arg('when', $period, $url);
    }

    return $url;
}

/**
 * Query args to preserve in pagination.
 *
 * @return array<string, string>
 */
function waqya_date_filter_pagination_args(): array
{
    $period = waqya_get_date_period();
    if ($period === '') {
        return [];
    }

    return ['when' => $period];
}

/**
 * Register ?when= query var.
 *
 * @param string[] $vars
 * @return string[]
 */
function waqya_register_date_period_var(array $vars): array
{
    $vars[] = 'when';
    return $vars;
}
add_filter('query_vars', 'waqya_register_date_period_var');

/**
 * Apply date filter to main listing queries.
 */
function waqya_apply_date_period_to_query(WP_Query $query): void
{
    if (is_admin() || ! $query->is_main_query()) {
        return;
    }

    if (! $query->is_category() && ! $query->is_tag() && ! $query->is_search()
        && ! $query->is_author() && ! $query->is_date() && ! $query->is_archive()) {
        return;
    }

    $period = waqya_get_date_period();
    if ($period === '') {
        return;
    }

    $date_query = waqya_date_period_query($period);
    if ($date_query === []) {
        return;
    }

    $existing = $query->get('date_query');
    if (! is_array($existing)) {
        $existing = [];
    }

    $query->set('date_query', array_merge($existing, $date_query));
}
add_action('pre_get_posts', 'waqya_apply_date_period_to_query', 12);

/**
 * Render period filter pills.
 */
function waqya_render_date_filter(): void
{
    if (! waqya_date_filter_supported()) {
        return;
    }

    $active  = waqya_get_date_period();
    $current = $active !== '' ? $active : 'all';

    get_template_part('template-parts/archive/date', 'filter', [
        'choices' => waqya_date_period_choices(),
        'current' => $current,
    ]);
}
