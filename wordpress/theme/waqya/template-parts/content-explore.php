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
            <h3 class="explore-card__title"><?php the_title(); ?></h3>
            <time class="explore-card__time" datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                <?php echo esc_html(waqya_time_ago()); ?>
            </time>
        </div>
    </a>
</article>
