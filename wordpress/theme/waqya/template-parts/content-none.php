<?php
/**
 * Empty state
 *
 * @package Waqya
 */
?>
<section class="empty-state">
    <h2 class="empty-state__title"><?php esc_html_e('Nothing published yet', 'waqya'); ?></h2>
    <p class="empty-state__text">
        <?php esc_html_e('New commentary will appear here once drafts are reviewed and published.', 'waqya'); ?>
    </p>
    <a class="button button--primary" href="<?php echo esc_url(home_url('/')); ?>">
        <?php esc_html_e('Back to homepage', 'waqya'); ?>
    </a>
</section>
