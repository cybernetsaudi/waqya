<?php
/**
 * Archive template
 *
 * @package Waqya
 */

get_header();
?>

<div class="archive-layout">
    <header class="page-header">
        <?php waqya_breadcrumbs(); ?>
        <?php the_archive_title('<h1 class="page-header__title">', '</h1>'); ?>
        <?php the_archive_description('<p class="page-header__description">', '</p>'); ?>
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
