<?php
/**
 * Lead story hero
 *
 * @package Waqya
 */
$slug = waqya_post_category_slug();
?>
<article <?php post_class('hero-card hero-card--' . esc_attr($slug)); ?>>
    <div class="hero-card__inner">
        <figure class="hero-card__media">
            <?php waqya_the_thumbnail('waqya-hero', 'hero-card__image'); ?>
        </figure>
        <div class="hero-card__body">
            <div class="hero-card__meta">
                <?php waqya_category_badge(); ?>
                <?php waqya_posted_on(); ?>
            </div>
            <h2 class="hero-card__title">
                <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
            </h2>
            <p class="hero-card__excerpt"><?php echo esc_html(get_the_excerpt()); ?></p>
            <a class="hero-card__cta" href="<?php the_permalink(); ?>">
                <?php esc_html_e('Read analysis', 'waqya'); ?>
            </a>
        </div>
    </div>
</article>
