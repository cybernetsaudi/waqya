<?php
/**
 * Search results
 *
 * @package Waqya
 */

get_header();
?>

<div class="page-shell">
    <div class="editorial-layout">
        <div class="editorial-layout__primary">
            <header class="page-header">
                <h1 class="page-header__title">
                    <?php
                    printf(
                        esc_html__('Results for “%s”', 'waqya'),
                        esc_html(get_search_query())
                    );
                    ?>
                </h1>
            </header>

            <?php waqya_render_date_filter(); ?>

            <?php if (have_posts()) : ?>
                <div class="story-feed__grid">
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
        <?php waqya_render_sidebar(); ?>
    </div>
</div>

<?php
get_footer();
