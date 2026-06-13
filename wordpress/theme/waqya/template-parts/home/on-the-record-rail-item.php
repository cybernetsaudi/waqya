<?php
/**
 * Compact On The Record item for hero sidebar.
 *
 * @package Waqya
 */
?>
<li class="otr-rail__item">
    <a class="otr-rail__link" href="<?php the_permalink(); ?>">
        <span class="otr-rail__item-title"><?php waqya_the_title(); ?></span>
        <?php
        $tone = waqya_interview_tone_label();
        if ($tone !== '') :
            ?>
            <span class="otr-rail__tone"><?php echo esc_html($tone); ?></span>
        <?php endif; ?>
        <?php waqya_render_dateline('inline'); ?>
    </a>
</li>
