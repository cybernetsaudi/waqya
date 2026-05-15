<?php
/**
 * Search results
 *
 * @package Waqya
 */

get_header();
?>

<div class="archive-layout">
    <header class="page-header">
        <?php waqya_breadcrumbs(); ?>
        <h1 class="page-header__title">
            <?php
            printf(
                /* translators: %s: search query */
                esc_html__('Results for “%s”', 'waqya'),
                esc_html(get_search_query())
            );
            ?>
        </h1>
    </header>

    <?php if (have_posts()) : ?>
        <div class="post-grid">
            <?php
            while (have_posts()) {
                the_post();
                get_template_part('template-parts/content', 'card');
            }
            ?>
        </div>
        <?php waqya_pagination(); ?>
    <?php else : ?>
        <section class="empty-state">
            <h2 class="empty-state__title"><?php esc_html_e('No matches', 'waqya'); ?></h2>
            <p class="empty-state__text"><?php esc_html_e('Try different keywords or browse by category.', 'waqya'); ?></p>
            <?php get_search_form(); ?>
        </section>
    <?php endif; ?>
</div>

<?php
get_footer();
