<?php
/**
 * Homepage — why we are called Waqya
 *
 * @package Waqya
 */

$compact = (bool) get_query_var('waqya_brand_compact', false);
?>
<section class="brand-story<?php echo $compact ? ' brand-story--compact' : ''; ?>" aria-labelledby="brand-story-title">
    <div class="brand-story__inner">
        <div class="brand-story__intro">
            <p class="brand-story__eyebrow"><?php echo esc_html(waqya_brand_story_eyebrow()); ?></p>
            <h2 id="brand-story-title" class="brand-story__title">
                <span class="brand-story__name"><?php echo esc_html(waqya_site_name()); ?></span>
                <span class="brand-story__means" aria-hidden="true"><?php esc_html_e('means', 'waqya'); ?></span>
                <span class="brand-story__meaning"><?php echo esc_html(waqya_brand_meaning()); ?></span>
            </h2>
            <p class="brand-story__lead"><?php echo esc_html(waqya_brand_story_short()); ?></p>
        </div>
        <?php if ($compact) : ?>
            <details class="brand-story__more">
                <summary><?php esc_html_e('About the name', 'waqya'); ?></summary>
                <p class="brand-story__body"><?php echo esc_html(waqya_brand_story_long()); ?></p>
            </details>
        <?php else : ?>
            <p class="brand-story__body"><?php echo esc_html(waqya_brand_story_long()); ?></p>
        <?php endif; ?>
    </div>
</section>
