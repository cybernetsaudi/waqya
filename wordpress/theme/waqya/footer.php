<?php
/**
 * Footer template
 *
 * @package Waqya
 */
?>
</main><!-- #main-content -->

<footer class="site-footer" role="contentinfo">
    <div class="site-footer__inner">
        <div class="site-footer__brand">
            <a class="site-footer__title" href="<?php echo esc_url(home_url('/')); ?>"><?php echo esc_html(waqya_site_name()); ?></a>
            <p class="site-footer__tagline"><?php echo esc_html(waqya_site_tagline()); ?></p>
        </div>

        <?php if (has_nav_menu('footer')) : ?>
            <nav class="site-footer__nav" aria-label="<?php esc_attr_e('Footer', 'waqya'); ?>">
                <?php
                wp_nav_menu([
                    'theme_location' => 'footer',
                    'container'      => false,
                    'menu_class'     => 'site-footer__links',
                    'depth'          => 1,
                ]);
                ?>
            </nav>
        <?php endif; ?>

        <p class="site-footer__copy">
            &copy; <?php echo esc_html((string) gmdate('Y')); ?>
            <a href="<?php echo esc_url(home_url('/')); ?>"><?php echo esc_html(waqya_site_name()); ?></a>.
            <?php esc_html_e('Independent news commentary.', 'waqya'); ?>
        </p>
    </div>
</footer>

<?php wp_footer(); ?>
</body>
</html>
