<?php
/**
 * Front page — editorial homepage
 *
 * @package Waqya
 */

get_header();

$exclude   = waqya_excluded_post_ids();
$shown_ids = [];

$lead = new WP_Query([
    'post_type'           => 'post',
    'post_status'         => 'publish',
    'posts_per_page'      => 1,
    'post__not_in'        => $exclude,
    'ignore_sticky_posts' => true,
]);

$grid_args = [
    'post_type'           => 'post',
    'post_status'         => 'publish',
    'posts_per_page'      => 6,
    'post__not_in'        => $exclude,
    'ignore_sticky_posts' => true,
];
?>

<div class="home-layout">
    <?php if ($lead->have_posts()) : ?>
        <section class="home-hero" aria-label="<?php esc_attr_e('Lead story', 'waqya'); ?>">
            <?php
            while ($lead->have_posts()) {
                $lead->the_post();
                $shown_ids[] = get_the_ID();
                get_template_part('template-parts/content', 'hero');
            }
            wp_reset_postdata();
            ?>
        </section>
    <?php endif; ?>

    <?php
    $grid_args['post__not_in'] = array_merge($exclude, $shown_ids);
    $grid = new WP_Query($grid_args);
    ?>

    <?php if ($grid->have_posts()) : ?>
        <section class="home-latest">
            <header class="section-header">
                <h2 class="section-header__title"><?php esc_html_e('Latest analysis', 'waqya'); ?></h2>
            </header>
            <div class="post-grid post-grid--count-<?php echo esc_attr((string) min($grid->post_count, 3)); ?>">
                <?php
                while ($grid->have_posts()) {
                    $grid->the_post();
                    get_template_part('template-parts/content', 'card');
                }
                wp_reset_postdata();
                ?>
            </div>
        </section>
    <?php elseif (empty($shown_ids)) : ?>
        <?php get_template_part('template-parts/content', 'none'); ?>
    <?php endif; ?>

    <?php
    $published = (int) wp_count_posts('post')->publish;
    $show_sections = $published >= 6;

    if ($show_sections) :
        $sections = [
            'technology' => __('Technology', 'waqya'),
            'world'      => __('World', 'waqya'),
            'science'    => __('Science', 'waqya'),
            'business'   => __('Business', 'waqya'),
            'opinion'    => __('Opinion', 'waqya'),
        ];

        foreach ($sections as $slug => $label) :
            $cat = get_category_by_slug($slug);
            if (! $cat) {
                continue;
            }

            $section_query = new WP_Query([
                'cat'            => $cat->term_id,
                'posts_per_page' => 3,
                'post_status'    => 'publish',
                'post__not_in'   => array_merge($exclude, $shown_ids),
            ]);

            if ($section_query->post_count < 2) {
                continue;
            }
            ?>
            <section class="home-section home-section--<?php echo esc_attr($slug); ?>">
                <header class="section-header">
                    <h2 class="section-header__title">
                        <a href="<?php echo esc_url(get_category_link($cat)); ?>"><?php echo esc_html($label); ?></a>
                    </h2>
                </header>
                <div class="post-grid post-grid--compact">
                    <?php
                    while ($section_query->have_posts()) {
                        $section_query->the_post();
                        get_template_part('template-parts/content', 'card');
                    }
                    wp_reset_postdata();
                    ?>
                </div>
            </section>
        <?php endforeach; ?>
    <?php endif; ?>
</div>

<?php
get_footer();
