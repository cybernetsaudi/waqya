<?php
/**
 * Single slide in the Developing banner carousel
 *
 * @package Waqya
 */

$index  = (int) get_query_var('waqya_dev_slide_index', 0);
$active = (bool) get_query_var('waqya_dev_slide_active', false);
$slug   = waqya_post_category_slug();
?>
<article
    <?php post_class('developing-banner__slide' . ($active ? ' is-active' : '')); ?>
    data-slider-slide="<?php echo (int) $index; ?>"
    role="group"
    aria-roledescription="slide"
    aria-label="<?php echo esc_attr(sprintf(/* translators: %d: slide number */ __('Developing story %d', 'waqya'), $index + 1)); ?>"
    <?php echo $active ? '' : ' aria-hidden="true"'; ?>
>
    <a class="developing-banner__link" href="<?php the_permalink(); ?>">
        <div class="developing-banner__frame developing-banner__frame--<?php echo esc_attr($slug); ?>">
            <?php waqya_the_thumbnail('waqya-card', 'developing-banner__image'); ?>
            <span class="developing-banner__scrim" aria-hidden="true"></span>
            <div class="developing-banner__content">
                <span class="developing-banner__live"><?php esc_html_e('Live', 'waqya'); ?></span>
                <h3 class="developing-banner__headline"><?php waqya_the_title(); ?></h3>
                <p class="developing-banner__excerpt"><?php waqya_the_excerpt(16); ?></p>
                <?php waqya_render_dateline('developing'); ?>
            </div>
        </div>
    </a>
</article>
