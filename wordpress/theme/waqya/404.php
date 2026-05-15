<?php
/**
 * 404 template
 *
 * @package Waqya
 */

get_header();
?>

<div class="archive-layout">
    <section class="empty-state empty-state--404">
        <?php waqya_breadcrumbs(); ?>
        <h1 class="empty-state__title"><?php esc_html_e('Page not found', 'waqya'); ?></h1>
        <p class="empty-state__text">
            <?php esc_html_e('The page you requested may have moved or no longer exists.', 'waqya'); ?>
        </p>
        <a class="button button--primary" href="<?php echo esc_url(home_url('/')); ?>">
            <?php esc_html_e('Return home', 'waqya'); ?>
        </a>
    </section>
</div>

<?php
get_footer();
