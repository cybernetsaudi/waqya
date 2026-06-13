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
        'orderby'        => 'modified',
        'order'          => 'DESC',
        'date_query'     => [
            [
                'after' => '48 hours ago',
            ],
        ],
        'tax_query'      => [
            [
                'taxonomy' => 'post_tag',
                'field'    => 'slug',
                'terms'    => ['breaking'],
            ],
        ],
    ]);
}

/**
 * Post IDs for On The Record (tag or automation meta).
 *
 * @param int[] $exclude
 * @return int[]
 */
function waqya_on_the_record_post_ids(array $exclude = [], int $limit = 5): array
{
    $exclude = array_map('intval', $exclude);
    $found   = [];

    $by_meta = get_posts([
        'post_type'              => 'post',
        'post_status'            => 'publish',
        'posts_per_page'         => $limit,
        'post__not_in'           => $exclude,
        'orderby'                => 'date',
        'order'                  => 'DESC',
        'fields'                 => 'ids',
        'no_found_rows'          => true,
        'update_post_meta_cache' => false,
        'meta_query'             => [
            [
                'key'   => '_waqya_format',
                'value' => 'on_the_record',
            ],
        ],
    ]);

    foreach ($by_meta as $id) {
        $found[(int) $id] = true;
    }

    $tag = get_term_by('slug', 'on-the-record', 'post_tag');
    if ($tag instanceof WP_Term) {
        $by_tag = get_posts([
            'post_type'              => 'post',
            'post_status'            => 'publish',
            'posts_per_page'         => $limit,
            'post__not_in'           => $exclude,
            'orderby'                => 'date',
            'order'                  => 'DESC',
            'fields'                 => 'ids',
            'no_found_rows'          => true,
            'tag_id'                 => (int) $tag->term_id,
        ]);
        foreach ($by_tag as $id) {
            $found[(int) $id] = true;
        }
    }

    $ids = array_keys($found);
    if ($ids === []) {
        return [];
    }

    $dated = [];
    foreach ($ids as $id) {
        $dated[$id] = (int) get_post_time('U', true, $id);
    }
    arsort($dated);

    return array_slice(array_keys($dated), 0, $limit);
}

/**
 * On The Record interview reviews.
 */
function waqya_on_the_record_query(array $exclude = []): WP_Query
{
    $ids = waqya_on_the_record_post_ids($exclude, 5);
    if ($ids === []) {
        return new WP_Query(['post__in' => [0]]);
    }

    return waqya_home_query([
        'post__in'       => $ids,
        'orderby'        => 'post__in',
        'posts_per_page' => count($ids),
    ]);
}

/**
 * Compact On The Record column for the homepage hero (25% width).
 *
 * @param int[] $exclude
 * @return int[]
 */
function waqya_render_on_the_record_rail(array $exclude): array
{
    $ids = waqya_on_the_record_post_ids($exclude, 4);
    if ($ids === []) {
        $q = new WP_Query(['post__in' => [0]]);
    } else {
        $q = waqya_home_query([
            'post__in'       => $ids,
            'orderby'        => 'post__in',
            'posts_per_page' => count($ids),
        ]);
    }

    $shown = [];
    $tag   = get_term_by('slug', 'on-the-record', 'post_tag');
    $archive_url = $tag instanceof WP_Term ? get_tag_link($tag) : home_url('/tag/on-the-record/');
    ?>
    <section class="otr-rail" aria-label="<?php esc_attr_e('On The Record', 'waqya'); ?>">
        <header class="otr-rail__header">
            <span class="otr-rail__kicker"><?php esc_html_e('Opinion', 'waqya'); ?></span>
            <h2 class="otr-rail__heading"><?php esc_html_e('On The Record', 'waqya'); ?></h2>
            <?php if ($q->have_posts()) : ?>
                <a class="otr-rail__more" href="<?php echo esc_url($archive_url); ?>">
                    <?php esc_html_e('All', 'waqya'); ?>
                </a>
            <?php endif; ?>
        </header>

        <?php if ($q->have_posts()) : ?>
            <ul class="otr-rail__list">
                <?php
                while ($q->have_posts()) {
                    $q->the_post();
                    $shown[] = (int) get_the_ID();
                    get_template_part('template-parts/home/on-the-record-rail', 'item');
                }
                ?>
            </ul>
        <?php else : ?>
            <p class="otr-rail__empty">
                <?php esc_html_e('Interview reviews appear here when leaders sit for major on-camera interviews.', 'waqya'); ?>
            </p>
        <?php endif; ?>
    </section>
    <?php
    wp_reset_postdata();

    return $shown;
}

/**
 * @param int[] $exclude
 * @return int[]
 */
function waqya_render_on_the_record_strip(array $exclude): array
{
    $q   = waqya_on_the_record_query($exclude);
    $ids = [];
    $tag = get_term_by('slug', 'on-the-record', 'post_tag');
    $archive_url = $tag instanceof WP_Term ? get_tag_link($tag) : home_url('/tag/on-the-record/');
    ?>
    <section class="home-section home-section--on-the-record" aria-label="<?php esc_attr_e('On The Record', 'waqya'); ?>">
        <header class="home-section__header home-section__header--otr">
            <div class="home-section__intro">
                <span class="home-section__kicker"><?php esc_html_e('Opinion', 'waqya'); ?></span>
                <h2 class="home-section__title"><?php esc_html_e('On The Record', 'waqya'); ?></h2>
                <p class="home-section__dek">
                    <?php esc_html_e('Interview reviews — contradiction checks, rhetoric, and what leaders actually said.', 'waqya'); ?>
                </p>
            </div>
            <?php if ($q->have_posts()) : ?>
                <a class="home-section__more" href="<?php echo esc_url($archive_url); ?>">
                    <?php esc_html_e('All reviews', 'waqya'); ?>
                </a>
            <?php endif; ?>
        </header>

        <?php if ($q->have_posts()) : ?>
            <div class="otr-strip">
                <div class="otr-strip__lead">
                    <?php
                    $q->the_post();
                    $ids[] = (int) get_the_ID();
                    get_template_part('template-parts/home/on-the-record', 'lead');
                    ?>
                </div>
                <?php if ($q->have_posts()) : ?>
                    <ul class="otr-list" aria-label="<?php esc_attr_e('More On The Record reviews', 'waqya'); ?>">
                        <?php
                        while ($q->have_posts()) {
                            $q->the_post();
                            $ids[] = (int) get_the_ID();
                            get_template_part('template-parts/home/on-the-record', 'item');
                        }
                        ?>
                    </ul>
                <?php endif; ?>
            </div>
        <?php else : ?>
            <p class="otr-empty">
                <?php esc_html_e('Leader interview reviews publish here when presidents and prime ministers sit for major on-camera interviews. The next pipeline run will fill this section when a story qualifies.', 'waqya'); ?>
            </p>
        <?php endif; ?>
    </section>
    <?php
    wp_reset_postdata();

    return $ids;
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

    $ids   = [];
    $total = (int) $q->post_count;
    $uid   = 'developing-banner-' . wp_unique_id();
    ?>
    <section class="home-section home-section--developing" aria-label="<?php esc_attr_e('Developing', 'waqya'); ?>">
        <header class="home-section__header">
            <h2 class="home-section__title"><?php esc_html_e('Developing', 'waqya'); ?></h2>
            <span class="home-section__badge"><?php esc_html_e('Breaking', 'waqya'); ?></span>
        </header>

        <div class="developing-strip">
            <div class="developing-strip__list">
                <ul class="developing-list">
                    <?php
                    while ($q->have_posts()) {
                        $q->the_post();
                        $ids[] = (int) get_the_ID();
                        ?>
                        <li class="developing-list__item">
                            <a class="developing-list__link" href="<?php the_permalink(); ?>">
                                <?php waqya_the_title(); ?>
                            </a>
                            <?php waqya_render_dateline('developing'); ?>
                        </li>
                        <?php
                    }
                    ?>
                </ul>
            </div>

            <?php if ($total > 0) : ?>
                <div
                    class="developing-banner"
                    data-post-slider
                    data-slider-interval="4500"
                    aria-roledescription="carousel"
                    aria-label="<?php esc_attr_e('Developing stories', 'waqya'); ?>"
                >
                    <div class="developing-banner__toolbar">
                        <span class="developing-banner__label"><?php esc_html_e('Now developing', 'waqya'); ?></span>
                        <?php if ($total > 1) : ?>
                            <div class="developing-banner__controls">
                                <button type="button" class="developing-banner__btn" data-slider-prev aria-controls="<?php echo esc_attr($uid); ?>" aria-label="<?php esc_attr_e('Previous developing story', 'waqya'); ?>">
                                    <span aria-hidden="true">&larr;</span>
                                </button>
                                <span class="developing-banner__counter" data-slider-counter aria-live="polite">
                                    <span data-slider-current>1</span>
                                    <span aria-hidden="true">/</span>
                                    <span data-slider-total><?php echo (int) $total; ?></span>
                                </span>
                                <button type="button" class="developing-banner__btn" data-slider-next aria-controls="<?php echo esc_attr($uid); ?>" aria-label="<?php esc_attr_e('Next developing story', 'waqya'); ?>">
                                    <span aria-hidden="true">&rarr;</span>
                                </button>
                            </div>
                        <?php endif; ?>
                    </div>

                    <div class="developing-banner__viewport" id="<?php echo esc_attr($uid); ?>">
                        <div class="developing-banner__track" data-slider-track>
                            <?php
                            $q->rewind_posts();
                            $index = 0;
                            while ($q->have_posts()) {
                                $q->the_post();
                                set_query_var('waqya_dev_slide_index', $index);
                                set_query_var('waqya_dev_slide_active', $index === 0);
                                get_template_part('template-parts/home/developing', 'slide');
                                $index++;
                            }
                            ?>
                        </div>
                    </div>

                    <?php if ($total > 1) : ?>
                        <div class="developing-banner__dots" data-slider-dots role="tablist" aria-label="<?php esc_attr_e('Choose developing story', 'waqya'); ?>">
                            <?php for ($i = 0; $i < $total; $i++) : ?>
                                <button
                                    type="button"
                                    class="developing-banner__dot<?php echo $i === 0 ? ' is-active' : ''; ?>"
                                    role="tab"
                                    data-slider-goto="<?php echo (int) $i; ?>"
                                    aria-label="<?php echo esc_attr(sprintf(/* translators: %d: slide number */ __('Developing story %d', 'waqya'), $i + 1)); ?>"
                                    aria-selected="<?php echo $i === 0 ? 'true' : 'false'; ?>"
                                ></button>
                            <?php endfor; ?>
                        </div>
                    <?php endif; ?>
                </div>
            <?php endif; ?>
        </div>
    </section>
    <?php
    wp_reset_postdata();

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
