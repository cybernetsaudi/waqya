<?php
/**
 * Main template fallback
 *
 * @package Waqya
 */

get_header();
?>

<div class="archive-layout">
    <header class="page-header">
        <h1 class="page-header__title"><?php esc_html_e('Latest stories', 'waqya'); ?></h1>
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
        <?php get_template_part('template-parts/content', 'none'); ?>
    <?php endif; ?>
</div>

<?php
get_footer();
