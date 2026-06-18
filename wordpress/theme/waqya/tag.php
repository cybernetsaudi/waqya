<?php
/**
 * Topic hub (tag archive at /topic/{slug}/)
 *
 * @package Waqya
 */

get_header();

$term = get_queried_object();
$min  = waqya_topic_min_posts_for_index();
$is_otr = $term instanceof WP_Term && $term->slug === 'on-the-record';
?>

<div class="page-shell topic-page<?php echo $is_otr ? ' topic-page--otr' : ''; ?>">
    <div class="editorial-layout editorial-layout--topic">
        <div class="editorial-layout__primary">
            <header class="page-header topic-page__header">
                <p class="page-header__eyebrow"><?php esc_html_e('Topic', 'waqya'); ?></p>
                <h1 class="page-header__title"><?php single_tag_title(); ?></h1>
                <?php if ($is_otr) : ?>
                    <p class="page-header__dek">
                        <?php esc_html_e('Interview reviews — contradiction checks, rhetoric, and what leaders actually said.', 'waqya'); ?>
                    </p>
                <?php elseif ($term instanceof WP_Term && $term->description) : ?>
                    <p class="page-header__dek"><?php echo esc_html(waqya_decode_entities($term->description)); ?></p>
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
                <?php if ($term instanceof WP_Term && (int) $term->count < $min && ! $is_otr) : ?>
                    <p class="page-header__note"><?php esc_html_e('This topic hub is still growing.', 'waqya'); ?></p>
                <?php endif; ?>
            </header>

            <?php if (have_posts()) : ?>
                <div class="story-feed__grid topic-page__grid">
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
