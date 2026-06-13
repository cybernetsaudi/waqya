<?php
/**
 * Trust page hero
 *
 * @package Waqya
 */

$config = waqya_trust_page_config();
if ($config === null) {
    return;
}

$slug = get_post_field('post_name', get_the_ID());
?>
<header class="trust-hero trust-hero--<?php echo esc_attr($slug); ?>">
    <p class="trust-hero__eyebrow"><?php echo esc_html($config['eyebrow'] ?? ''); ?></p>
    <h1 class="trust-hero__title"><?php waqya_the_title(); ?></h1>
    <?php if (! empty($config['dek'])) : ?>
        <p class="trust-hero__dek"><?php echo esc_html($config['dek']); ?></p>
    <?php endif; ?>
    <p class="trust-hero__brand">
        <?php echo esc_html(waqya_brand_full_name()); ?>
        <span aria-hidden="true">·</span>
        <?php echo esc_html(waqya_brand_tagline()); ?>
    </p>
</header>
