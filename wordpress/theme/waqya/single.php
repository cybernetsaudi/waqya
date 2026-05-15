<?php
/**
 * Single post
 *
 * @package Waqya
 */

get_header();
?>

<?php while (have_posts()) : the_post(); ?>
    <article <?php post_class('single-post'); ?>>
        <div class="single-post__header">
            <?php waqya_breadcrumbs(); ?>
            <div class="single-post__meta-top">
                <?php waqya_category_badge(); ?>
                <?php waqya_posted_on(); ?>
            </div>
            <h1 class="single-post__title"><?php the_title(); ?></h1>
            <?php if (has_excerpt()) : ?>
                <p class="single-post__dek"><?php echo esc_html(get_the_excerpt()); ?></p>
            <?php endif; ?>
        </div>

        <?php if (has_post_thumbnail()) : ?>
            <figure class="single-post__featured">
                <?php the_post_thumbnail('waqya-hero', ['class' => 'single-post__image']); ?>
                <?php
                $caption = get_the_post_thumbnail_caption();
                if ($caption) :
                    ?>
                    <figcaption class="single-post__caption"><?php echo esc_html($caption); ?></figcaption>
                <?php endif; ?>
            </figure>
        <?php endif; ?>

        <div class="single-post__content entry-content">
            <?php the_content(); ?>
        </div>

        <?php
        $tags = get_the_tags();
        if ($tags) :
            ?>
            <footer class="single-post__footer">
                <ul class="tag-list" aria-label="<?php esc_attr_e('Tags', 'waqya'); ?>">
                    <?php foreach ($tags as $tag) : ?>
                        <li class="tag-list__item">
                            <a class="tag-list__link" href="<?php echo esc_url(get_tag_link($tag)); ?>">
                                <?php echo esc_html($tag->name); ?>
                            </a>
                        </li>
                    <?php endforeach; ?>
                </ul>
            </footer>
        <?php endif; ?>
    </article>
<?php endwhile; ?>

<?php
get_footer();
