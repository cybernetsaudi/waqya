<?php
/**
 * Lead story — primary column feature (headline → image → caption → summary)
 *
 * @package Waqya
 */
?>
<article <?php post_class('lead-story'); ?>>
    <header class="lead-story__header">
        <?php waqya_category_badge(); ?>
        <h1 class="lead-story__title">
            <a href="<?php the_permalink(); ?>"><?php the_title(); ?></a>
        </h1>
    </header>

    <figure class="lead-story__figure">
        <a class="lead-story__image-link" href="<?php the_permalink(); ?>" tabindex="-1" aria-hidden="true">
            <?php waqya_the_thumbnail('waqya-hero', 'lead-story__image'); ?>
        </a>
        <?php if (has_excerpt()) : ?>
            <figcaption class="lead-story__caption"><?php echo esc_html(get_the_excerpt()); ?></figcaption>
        <?php endif; ?>
    </figure>

    <footer class="lead-story__footer">
        <p class="lead-story__meta">
            <time datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                <?php echo esc_html(waqya_time_ago()); ?>
            </time>
            <span class="lead-story__sep" aria-hidden="true">·</span>
            <span><?php echo esc_html(sprintf(
                /* translators: %d: minutes */
                _n('%d min read', '%d min read', waqya_reading_time(), 'waqya'),
                waqya_reading_time()
            )); ?></span>
        </p>
        <a class="lead-story__link" href="<?php the_permalink(); ?>">
            <?php esc_html_e('Read full analysis', 'waqya'); ?>
        </a>
    </footer>
</article>
