<?php
/**
 * Compact On The Record list item (homepage).
 *
 * @package Waqya
 */
?>
<li class="otr-list__item">
    <a class="otr-list__link" href="<?php the_permalink(); ?>">
        <span class="otr-list__title"><?php waqya_the_title(); ?></span>
        <?php
        $tone = waqya_interview_tone_label();
        if ($tone !== '') :
            ?>
            <span class="otr-list__tone"><?php echo esc_html($tone); ?></span>
        <?php endif; ?>
        <?php waqya_render_dateline('developing'); ?>
    </a>
</li>
