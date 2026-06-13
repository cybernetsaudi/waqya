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
    <div class="home-page__hero home-hero-band">
        <div class="home-page__hero-main home-hero-band__main">
            <?php
            $slider_ids = waqya_render_post_slider([
                'posts_per_page'  => 5,
                'post__not_in'    => $exclude,
                'prefer_featured' => true,
                'title'           => __('Top stories', 'waqya'),
            ]);
            $used_ids = array_merge($used_ids, $slider_ids);

            if ($slider_ids === []) {
                get_template_part('template-parts/content', 'none');
            }
            ?>
        </div>
        <aside class="home-page__hero-otr home-hero-band__otr">
            <?php
            $otr_ids = waqya_render_on_the_record_rail(array_merge($exclude, $used_ids));
            $used_ids = array_merge($used_ids, $otr_ids);
            ?>
        </aside>
    </div>

    <div class="home-page__sections">
        <?php
        $developing = waqya_render_developing_strip(array_merge($exclude, $used_ids));
        $used_ids   = array_merge($used_ids, $developing);

        $today_ids = waqya_render_today_on_waqya(array_merge($exclude, $used_ids));
        $used_ids  = array_merge($used_ids, $today_ids);

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
