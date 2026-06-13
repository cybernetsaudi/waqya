<?php
/**
 * Featured On The Record card (homepage lead).
 *
 * @package Waqya
 */
?>
<article <?php post_class('otr-lead'); ?>>
    <a class="otr-lead__link" href="<?php the_permalink(); ?>">
        <figure class="otr-lead__media">
            <?php waqya_the_thumbnail('waqya-hero', 'otr-lead__image'); ?>
        </figure>
        <div class="otr-lead__body">
            <span class="otr-lead__kicker"><?php esc_html_e('On The Record', 'waqya'); ?></span>
            <?php
            $tone = waqya_interview_tone_label();
            if ($tone !== '') :
                ?>
                <span class="otr-lead__tone"><?php echo esc_html($tone); ?></span>
            <?php endif; ?>
            <h3 class="otr-lead__title"><?php waqya_the_title(); ?></h3>
            <p class="otr-lead__excerpt"><?php waqya_the_excerpt(22); ?></p>
            <?php waqya_render_dateline('inline'); ?>
        </div>
    </a>
</article>
