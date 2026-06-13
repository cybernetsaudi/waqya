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
        <?php waqya_render_dateline('inline'); ?>
    </a>
</li>
