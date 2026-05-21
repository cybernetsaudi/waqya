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

/**
 * Posts tagged Breaking from the last 48 hours.
 */
function waqya_developing_query(array $exclude = []): WP_Query
{
    return waqya_home_query([
        'posts_per_page' => 5,
        'post__not_in'   => $exclude,
        'tag'            => 'breaking',
        'date_query'     => [
            [
                'after' => '48 hours ago',
            ],
        ],
    ]);
}

/**
 * Today's published commentary (last 24h).
 */
function waqya_today_query(array $exclude = []): WP_Query
{
    return waqya_home_query([
        'posts_per_page' => 6,
        'post__not_in'   => $exclude,
        'date_query'     => [
            [
                'after' => '24 hours ago',
            ],
        ],
    ]);
}

/**
 * @param int[] $exclude
 * @return int[]
 */
function waqya_render_developing_strip(array $exclude): array
{
    $q = waqya_developing_query($exclude);
    if (! $q->have_posts()) {
        return [];
    }

    $ids = [];
    ?>
    <section class="home-section home-section--developing" aria-label="<?php esc_attr_e('Developing', 'waqya'); ?>">
        <header class="home-section__header">
            <h2 class="home-section__title"><?php esc_html_e('Developing', 'waqya'); ?></h2>
            <span class="home-section__badge"><?php esc_html_e('Breaking', 'waqya'); ?></span>
        </header>
        <ul class="developing-list">
            <?php
            while ($q->have_posts()) {
                $q->the_post();
                $ids[] = (int) get_the_ID();
                ?>
                <li class="developing-list__item">
                    <a class="developing-list__link" href="<?php the_permalink(); ?>">
                        <?php the_title(); ?>
                    </a>
                    <time class="developing-list__time" datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                        <?php echo esc_html(waqya_time_ago()); ?>
                    </time>
                </li>
                <?php
            }
            wp_reset_postdata();
            ?>
        </ul>
    </section>
    <?php

    return $ids;
}

/**
 * @param int[] $exclude
 * @return int[]
 */
function waqya_render_today_on_waqya(array $exclude): array
{
    $q = waqya_today_query($exclude);
    if (! $q->have_posts()) {
        return [];
    }

    $ids = [];
    ?>
    <section class="home-section home-section--today">
        <header class="home-section__header">
            <h2 class="home-section__title"><?php esc_html_e('Today on Waqya', 'waqya'); ?></h2>
        </header>
        <div class="home-section__grid home-section__grid--compact">
            <?php
            while ($q->have_posts()) {
                $q->the_post();
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
