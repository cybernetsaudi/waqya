<?php
/**
 * Homepage helpers
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Run a scoped post query for homepage sections.
 *
 * @param array<string, mixed> $args
 */
function waqya_home_query(array $args): WP_Query
{
    $defaults = [
        'post_type'           => 'post',
        'post_status'         => 'publish',
        'ignore_sticky_posts' => true,
        'no_found_rows'       => true,
    ];

    return new WP_Query(array_merge($defaults, $args));
}

/**
 * Render one homepage strip for a menu group (News Desk, Regions, Topics).
 *
 * @param int[] $exclude
 * @return int[] Post IDs shown.
 */
function waqya_render_home_menu_group(string $group_id, string $label, array $exclude, int $count = 4): array
{
    $term_ids = waqya_menu_group_term_ids($group_id);
    if ($term_ids === []) {
        return [];
    }

    $section = waqya_home_query([
        'category__in'   => $term_ids,
        'posts_per_page' => $count,
        'post__not_in'   => $exclude,
    ]);

    if (! $section->have_posts()) {
        return [];
    }

    $ids = [];
    $slug = sanitize_html_class($group_id);
    ?>
    <section class="home-section home-section--group home-section--<?php echo esc_attr($slug); ?>">
        <header class="home-section__header">
            <h2 class="home-section__title"><?php echo esc_html($label); ?></h2>
        </header>
        <div class="home-section__grid">
            <?php
            while ($section->have_posts()) {
                $section->the_post();
                $ids[] = (int) get_the_ID();
                get_template_part('template-parts/content', 'card');
            }
            wp_reset_postdata();
            ?>
        </div>
    </section>
    <?php

    return $ids;
}
