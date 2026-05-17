<?php
/**
 * Category archive — slider + grid
 *
 * @package Waqya
 */

get_header();

$term = waqya_queried_category();
if (! $term) {
    locate_template('archive.php', true);
    return;
}

$slug  = $term->slug;
$label = waqya_category_label($term);
$desc  = waqya_category_description($term);
?>

<div class="page-shell category-page category-page--<?php echo esc_attr($slug); ?>">
    <header class="category-page__header">
        <p class="category-page__eyebrow"><?php esc_html_e('Section', 'waqya'); ?></p>
        <h1 class="category-page__title"><?php echo esc_html($label); ?></h1>
        <?php if ($desc !== '') : ?>
            <div class="category-page__description"><?php echo wp_kses_post(wpautop($desc)); ?></div>
        <?php else : ?>
            <p class="category-page__description">
                <?php
                printf(
                    /* translators: %s: category name */
                    esc_html__('Analysis and commentary on %s from Waqya — The Incident.', 'waqya'),
                    esc_html(strtolower($label))
                );
                ?>
            </p>
        <?php endif; ?>
        <p class="category-page__count">
            <?php
            printf(
                /* translators: %d: number of posts */
                esc_html(_n('%d story', '%d stories', (int) $term->count, 'waqya')),
                (int) $term->count
            );
            ?>
        </p>
    </header>

    <div class="category-page__hero">
        <?php
        waqya_render_post_slider([
            'cat'            => (int) $term->term_id,
            'posts_per_page' => 5,
            'title'          => sprintf(
                /* translators: %s: category name */
                __('Latest in %s', 'waqya'),
                $label
            ),
        ]);
        ?>
    </div>

    <?php if (have_posts()) : ?>
        <section class="category-page__grid-wrap">
            <h2 class="category-page__grid-title"><?php esc_html_e('All stories', 'waqya'); ?></h2>
            <div class="category-page__grid">
                <?php
                while (have_posts()) {
                    the_post();
                    get_template_part('template-parts/content', 'card');
                }
                ?>
            </div>
        </section>
        <?php waqya_pagination(); ?>
    <?php else : ?>
        <section class="category-page__empty">
            <?php get_template_part('template-parts/content', 'none'); ?>
            <p class="category-page__empty-hint">
                <?php
                if (waqya_get_date_period() !== '') {
                    esc_html_e('No stories in this section for the selected period. Try a wider date range.', 'waqya');
                } else {
                    esc_html_e('New stories in this section will appear here after they are published.', 'waqya');
                }
                ?>
            </p>
        </section>
    <?php endif; ?>
</div>

<?php
get_footer();
