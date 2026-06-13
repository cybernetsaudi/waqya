<?php
/**
 * Topic hub (tag archive at /topic/{slug}/)
 *
 * @package Waqya
 */

get_header();

$term = get_queried_object();
$min  = waqya_topic_min_posts_for_index();
?>

<div class="page-shell">
    <div class="editorial-layout">
        <div class="editorial-layout__primary">
            <header class="page-header">
                <p class="page-header__eyebrow"><?php esc_html_e('Topic', 'waqya'); ?></p>
                <h1 class="page-header__title"><?php single_tag_title(); ?></h1>
                <?php if ($term instanceof WP_Term && $term->description) : ?>
                    <p class="page-header__dek"><?php echo esc_html($term->description); ?></p>
                <?php else : ?>
                    <p class="page-header__dek">
                        <?php
                        printf(
                            esc_html__('Stories tagged “%s” on Waqya.', 'waqya'),
                            esc_html(single_tag_title('', false))
                        );
                        ?>
                    </p>
                <?php endif; ?>
                <?php if ($term instanceof WP_Term && (int) $term->count < $min) : ?>
                    <p class="page-header__note"><?php esc_html_e('This topic hub is still growing.', 'waqya'); ?></p>
                <?php endif; ?>
            </header>

            <?php if (have_posts()) : ?>
                <div class="story-feed__grid">
                    <?php
                    while (have_posts()) {
                        the_post();
                        get_template_part('template-parts/content', 'card');
                    }
                    ?>
                </div>
                <?php waqya_pagination(); ?>
            <?php else : ?>
                <?php get_template_part('template-parts/content', 'none'); ?>
            <?php endif; ?>
        </div>
        <?php waqya_render_sidebar(); ?>
    </div>
</div>

<?php
get_footer();
