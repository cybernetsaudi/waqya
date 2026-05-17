<?php
/**
 * Article card
 *
 * @package Waqya
 */
$slug = waqya_post_category_slug();
?>
<article <?php post_class('post-card post-card--' . esc_attr($slug)); ?>>
    <figure class="post-card__media">
        <a href="<?php the_permalink(); ?>" tabindex="-1" aria-hidden="true">
            <?php waqya_the_thumbnail('waqya-card', 'post-card__image'); ?>
        </a>
    </figure>
    <div class="post-card__body">
        <div class="post-card__meta">
            <?php waqya_category_badge(); ?>
        </div>
        <h3 class="post-card__title">
            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
        </h3>
        <p class="post-card__excerpt"><?php echo esc_html(get_the_excerpt()); ?></p>
        <time class="post-card__date" datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
            <?php echo esc_html(waqya_time_ago()); ?>
        </time>
    </div>
</article>
