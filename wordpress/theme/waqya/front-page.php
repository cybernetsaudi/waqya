<?php
/**
 * Homepage — hero slider, brand note, desk sections
 *
 * @package Waqya
 */

get_header();

$exclude  = waqya_excluded_post_ids();
$used_ids = [];
?>

<div class="home-page">
    <div class="home-page__hero">
        <?php
        $slider_ids = waqya_render_post_slider([
            'posts_per_page' => 5,
            'post__not_in'   => $exclude,
            'title'          => __('Top stories', 'waqya'),
        ]);
        $used_ids = array_merge($used_ids, $slider_ids);

        if ($slider_ids === []) {
            get_template_part('template-parts/content', 'none');
        }
        ?>
    </div>

    <div class="home-page__sections">
        <?php
        $pool = array_merge($exclude, $used_ids);
        foreach (waqya_menu_groups() as $group) {
            $group_id = (string) ($group['id'] ?? '');
            $label    = (string) ($group['label'] ?? $group_id);
            if ($group_id === '') {
                continue;
            }
            $shown    = waqya_render_home_menu_group($group_id, $label, $pool, 4);
            $used_ids = array_merge($used_ids, $shown);
            $pool     = array_merge($pool, $shown);
        }

        $latest = waqya_home_query([
            'posts_per_page' => 8,
            'post__not_in'   => array_unique(array_merge($exclude, $used_ids)),
        ]);

        if ($latest->have_posts()) :
            ?>
            <section class="home-section home-section--latest">
                <header class="home-section__header">
                    <h2 class="home-section__title"><?php esc_html_e('Latest analysis', 'waqya'); ?></h2>
                </header>
                <div class="home-section__grid">
                    <?php
                    while ($latest->have_posts()) {
                        $latest->the_post();
                        get_template_part('template-parts/content', 'card');
                    }
                    wp_reset_postdata();
                    ?>
                </div>
            </section>
        <?php endif; ?>
    </div>
</div>

<?php
get_footer();
