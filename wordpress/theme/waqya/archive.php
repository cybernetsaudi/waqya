<?php
/**
 * Archive template
 *
 * @package Waqya
 */

get_header();
?>

<div class="page-shell">
    <div class="editorial-layout">
        <div class="editorial-layout__primary">
            <header class="page-header">
                <?php the_archive_title('<h1 class="page-header__title">', '</h1>'); ?>
                <?php the_archive_description('<p class="page-header__description">', '</p>'); ?>
                <?php
                global $wp_query;
                $found = isset($wp_query->found_posts) ? (int) $wp_query->found_posts : 0;
                $period_label = waqya_date_period_summary();
                if ($found > 0 || $period_label !== '') :
                    ?>
                    <p class="page-header__count">
                        <?php
                        if ($period_label !== '') {
                            printf(
                                esc_html(_n('%1$d story · %2$s', '%1$d stories · %2$s', $found, 'waqya')),
                                $found,
                                esc_html($period_label)
                            );
                        } else {
                            printf(
                                esc_html(_n('%d story', '%d stories', $found, 'waqya')),
                                $found
                            );
                        }
                        ?>
                    </p>
                <?php endif; ?>
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
                <?php get_template_part('template-parts/content', 'none'); ?>
            <?php endif; ?>
        </div>

        <?php waqya_render_sidebar(); ?>
    </div>
</div>

<?php
get_footer();
