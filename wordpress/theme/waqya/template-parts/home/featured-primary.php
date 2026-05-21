<?php
/**
 * Homepage primary featured story
 *
 * @package Waqya
 */
?>
<article <?php post_class('home-featured'); ?>>
    <a class="home-featured__media" href="<?php the_permalink(); ?>" tabindex="-1" aria-hidden="true">
        <?php waqya_the_thumbnail('waqya-hero', 'home-featured__image'); ?>
    </a>
    <div class="home-featured__body">
        <?php waqya_category_badge(); ?>
        <h2 class="home-featured__title">
            <a href="<?php the_permalink(); ?>"><?php waqya_the_title(); ?></a>
        </h2>
        <p class="home-featured__excerpt"><?php waqya_the_excerpt(); ?></p>
        <p class="home-featured__meta">
            <time datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                <?php echo esc_html(waqya_time_ago()); ?>
            </time>
            <span aria-hidden="true">·</span>
            <?php echo esc_html(sprintf(
                _n('%d min read', '%d min read', waqya_reading_time(), 'waqya'),
                waqya_reading_time()
            )); ?>
        </p>
    </div>
</article>
