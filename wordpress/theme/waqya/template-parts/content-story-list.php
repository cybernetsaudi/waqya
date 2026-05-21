<?php
/**
 * Sidebar story list item
 *
 * @package Waqya
 */
?>
<li class="story-list__item">
    <a class="story-list__link" href="<?php the_permalink(); ?>">
        <h3 class="story-list__title"><?php waqya_the_title(); ?></h3>
        <time class="story-list__time" datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
            <?php echo esc_html(waqya_time_ago()); ?>
        </time>
    </a>
</li>
