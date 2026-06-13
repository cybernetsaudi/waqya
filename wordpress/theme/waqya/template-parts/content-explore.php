<?php
/**
 * Sidebar explore card
 *
 * @package Waqya
 */
?>
<article <?php post_class('explore-card'); ?>>
    <a class="explore-card__link" href="<?php the_permalink(); ?>">
        <figure class="explore-card__media">
            <?php waqya_the_thumbnail('waqya-thumb', 'explore-card__image'); ?>
        </figure>
        <div class="explore-card__body">
            <h3 class="explore-card__title"><?php waqya_the_title(); ?></h3>
            <?php waqya_render_dateline('inline'); ?>
        </div>
    </a>
</article>
