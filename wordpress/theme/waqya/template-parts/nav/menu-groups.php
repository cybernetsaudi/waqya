<?php
/**
 * Grouped section navigation (News Desk / Regions / Topics + formats)
 *
 * @package Waqya
 */

$groups = waqya_menu_groups();
if ($groups === []) {
    waqya_categories_nav_fallback_legacy();
    return;
}

$current_slug = '';
if (is_category()) {
    $term = get_queried_object();
    if ($term instanceof WP_Term) {
        $current_slug = $term->slug;
    }
}

$is_otr = is_tag('on-the-record') || (is_tax('post_tag') && get_query_var('tag') === 'on-the-record');
?>
<nav class="site-nav-groups" aria-label="<?php esc_attr_e('Sections', 'waqya'); ?>">
    <div class="site-nav-groups__formats">
        <a
            class="site-nav-groups__format-link<?php echo $is_otr ? ' is-current' : ''; ?>"
            href="<?php echo esc_url(waqya_on_the_record_url()); ?>"
            <?php echo $is_otr ? ' aria-current="page"' : ''; ?>
        >
            <?php esc_html_e('On The Record', 'waqya'); ?>
        </a>
    </div>

    <ul class="site-nav-groups__tabs" role="tablist">
        <?php foreach ($groups as $i => $group) : ?>
            <?php
            $group_id = (string) ($group['id'] ?? 'group-' . $i);
            $label    = (string) ($group['label'] ?? $group_id);
            $panel_id = 'nav-panel-' . $group_id;
            ?>
            <li class="site-nav-groups__tab" role="presentation">
                <button
                    type="button"
                    class="site-nav-groups__tab-btn<?php echo $i === 0 ? ' is-active' : ''; ?>"
                    role="tab"
                    id="tab-<?php echo esc_attr($group_id); ?>"
                    aria-selected="<?php echo $i === 0 ? 'true' : 'false'; ?>"
                    aria-controls="<?php echo esc_attr($panel_id); ?>"
                    data-nav-tab="<?php echo esc_attr($group_id); ?>"
                >
                    <?php echo esc_html($label); ?>
                </button>
            </li>
        <?php endforeach; ?>
    </ul>

    <div class="site-nav-groups__panels">
        <?php foreach ($groups as $i => $group) : ?>
            <?php
            $group_id = (string) ($group['id'] ?? 'group-' . $i);
            $label    = (string) ($group['label'] ?? $group_id);
            $panel_id = 'nav-panel-' . $group_id;
            $items    = $group['items'] ?? [];
            ?>
            <div
                class="site-nav-groups__panel<?php echo $i === 0 ? ' is-active' : ''; ?>"
                id="<?php echo esc_attr($panel_id); ?>"
                role="tabpanel"
                aria-labelledby="tab-<?php echo esc_attr($group_id); ?>"
                data-nav-panel="<?php echo esc_attr($group_id); ?>"
                <?php echo $i === 0 ? '' : ' hidden'; ?>
            >
                <p class="site-nav-groups__panel-label"><?php echo esc_html($label); ?></p>
                <ul class="site-nav-groups__links">
                    <?php foreach ($items as $key) : ?>
                        <?php
                        $meta       = waqya_primary_category((string) $key);
                        $slug       = $meta['slug'] ?? (string) $key;
                        $item_label = $meta['label'] ?? (string) $key;
                        $url        = waqya_category_url((string) $key);
                        $is_current = $current_slug === $slug;
                        ?>
                        <li class="site-nav-groups__item">
                            <a
                                class="site-nav-groups__link<?php echo $is_current ? ' is-current' : ''; ?>"
                                href="<?php echo esc_url($url); ?>"
                                <?php echo $is_current ? ' aria-current="page"' : ''; ?>
                            >
                                <?php echo esc_html($item_label); ?>
                            </a>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </div>
        <?php endforeach; ?>
    </div>
</nav>
