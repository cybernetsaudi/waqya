<?php
/**
 * Archive date-period filter
 *
 * @package Waqya
 *
 * @var array<string, string> $args
 */

$choices = $args['choices'] ?? waqya_date_period_choices();
$current = $args['current'] ?? 'all';
$summary = waqya_date_period_summary();
?>
<section class="date-filter" aria-label="<?php esc_attr_e('Filter by date', 'waqya'); ?>">
    <div class="date-filter__header">
        <span class="date-filter__label"><?php esc_html_e('When', 'waqya'); ?></span>
        <?php if ($summary !== '') : ?>
            <span class="date-filter__active"><?php echo esc_html($summary); ?></span>
        <?php endif; ?>
    </div>
    <ul class="date-filter__list" role="list">
        <?php foreach ($choices as $slug => $label) : ?>
            <?php
            $is_active = $slug === $current;
            $url       = waqya_date_filter_url($slug);
            ?>
            <li class="date-filter__item">
                <a
                    class="date-filter__pill<?php echo $is_active ? ' is-active' : ''; ?>"
                    href="<?php echo esc_url($url); ?>"
                    <?php echo $is_active ? ' aria-current="true"' : ''; ?>
                >
                    <?php echo esc_html($label); ?>
                </a>
            </li>
        <?php endforeach; ?>
    </ul>
</section>
