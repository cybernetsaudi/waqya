<?php
/**
 * Hero post slider
 *
 * @package Waqya
 */

$query = get_query_var('waqya_slider_query');
$title = get_query_var('waqya_slider_title', __('Top stories', 'waqya'));

if (! $query instanceof WP_Query || ! $query->have_posts()) {
    return;
}

$total = (int) $query->post_count;
$uid   = 'post-slider-' . wp_unique_id();
?>
<section class="post-slider" data-post-slider aria-roledescription="carousel" aria-label="<?php echo esc_attr((string) $title); ?>">
    <div class="post-slider__header">
        <h2 class="post-slider__title"><?php echo esc_html((string) $title); ?></h2>
        <div class="post-slider__controls">
            <button type="button" class="post-slider__btn" data-slider-prev aria-controls="<?php echo esc_attr($uid); ?>" aria-label="<?php esc_attr_e('Previous story', 'waqya'); ?>">
                <span aria-hidden="true">&larr;</span>
            </button>
            <span class="post-slider__counter" data-slider-counter aria-live="polite">
                <span data-slider-current>1</span>
                <span class="post-slider__counter-sep" aria-hidden="true">/</span>
                <span data-slider-total><?php echo (int) $total; ?></span>
            </span>
            <button type="button" class="post-slider__btn" data-slider-next aria-controls="<?php echo esc_attr($uid); ?>" aria-label="<?php esc_attr_e('Next story', 'waqya'); ?>">
                <span aria-hidden="true">&rarr;</span>
            </button>
        </div>
    </div>

    <div class="post-slider__viewport" id="<?php echo esc_attr($uid); ?>">
        <div class="post-slider__track" data-slider-track>
            <?php
            $index = 0;
            while ($query->have_posts()) :
                $query->the_post();
                set_query_var('waqya_slide_index', $index);
                set_query_var('waqya_slide_active', $index === 0);
                get_template_part('template-parts/slider/slide');
                $index++;
            endwhile;
            ?>
        </div>
    </div>

    <div class="post-slider__dots" data-slider-dots role="tablist" aria-label="<?php esc_attr_e('Choose story', 'waqya'); ?>">
        <?php for ($i = 0; $i < $total; $i++) : ?>
            <button
                type="button"
                class="post-slider__dot<?php echo $i === 0 ? ' is-active' : ''; ?>"
                role="tab"
                data-slider-goto="<?php echo (int) $i; ?>"
                aria-label="<?php echo esc_attr(sprintf(/* translators: %d: slide number */ __('Story %d', 'waqya'), $i + 1)); ?>"
                aria-selected="<?php echo $i === 0 ? 'true' : 'false'; ?>"
            ></button>
        <?php endfor; ?>
    </div>
</section>
