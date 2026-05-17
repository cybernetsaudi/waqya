<?php
/**
 * Single slider slide — full-bleed image with overlay copy
 *
 * @package Waqya
 */

$index  = (int) get_query_var('waqya_slide_index', 0);
$active = (bool) get_query_var('waqya_slide_active', false);
$slug   = waqya_post_category_slug();
?>
<article
    <?php post_class('post-slider__slide' . ($active ? ' is-active' : '')); ?>
    data-slider-slide="<?php echo (int) $index; ?>"
    role="group"
    aria-roledescription="slide"
    aria-label="<?php echo esc_attr(sprintf(/* translators: %1$d of slide */ __('Slide %1$d', 'waqya'), $index + 1)); ?>"
    <?php echo $active ? '' : ' aria-hidden="true"'; ?>
>
    <a class="post-slider__link" href="<?php the_permalink(); ?>">
        <div class="post-slider__frame post-slider__frame--<?php echo esc_attr($slug); ?>">
            <?php waqya_the_thumbnail('waqya-hero', 'post-slider__image'); ?>
            <span class="post-slider__scrim" aria-hidden="true"></span>
            <div class="post-slider__content">
                <?php waqya_category_badge(false); ?>
                <h3 class="post-slider__headline"><?php the_title(); ?></h3>
                <p class="post-slider__excerpt"><?php echo esc_html(wp_trim_words(get_the_excerpt(), 18)); ?></p>
                <p class="post-slider__meta">
                    <time datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                        <?php echo esc_html(waqya_time_ago()); ?>
                    </time>
                </p>
            </div>
        </div>
    </a>
</article>
