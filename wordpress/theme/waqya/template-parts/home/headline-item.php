<?php
/**
 * Compact headline for homepage rail (with thumbnail)
 *
 * @package Waqya
 */
$categories = get_the_category();
$cat_name   = ! empty($categories) ? $categories[0]->name : __('News', 'waqya');
?>
<article <?php post_class('home-headline'); ?>>
    <a class="home-headline__link" href="<?php the_permalink(); ?>">
        <figure class="home-headline__media">
            <?php waqya_the_thumbnail('waqya-thumb', 'home-headline__image'); ?>
        </figure>
        <div class="home-headline__body">
            <span class="home-headline__category"><?php echo esc_html($cat_name); ?></span>
            <h3 class="home-headline__title"><?php the_title(); ?></h3>
            <time class="home-headline__time" datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                <?php echo esc_html(waqya_time_ago()); ?>
            </time>
        </div>
    </a>
</article>
