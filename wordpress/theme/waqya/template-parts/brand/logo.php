<?php
/**
 * Site logo with "The Incident" meaning line
 *
 * @package Waqya
 */
?>
<a class="site-logo" href="<?php echo esc_url(home_url('/')); ?>" rel="home" title="<?php echo esc_attr(waqya_brand_full_name()); ?>">
    <?php if (has_custom_logo()) : ?>
        <?php the_custom_logo(); ?>
        <span class="site-logo__lockup">
            <span class="site-logo__text"><?php echo esc_html(waqya_site_name()); ?></span>
            <span class="site-logo__meaning"><?php echo esc_html(waqya_brand_meaning()); ?></span>
        </span>
    <?php else : ?>
        <span class="site-logo__mark" aria-hidden="true">W</span>
        <span class="site-logo__lockup">
            <span class="site-logo__text"><?php echo esc_html(waqya_site_name()); ?></span>
            <span class="site-logo__meaning"><?php echo esc_html(waqya_brand_meaning()); ?></span>
        </span>
    <?php endif; ?>
</a>
