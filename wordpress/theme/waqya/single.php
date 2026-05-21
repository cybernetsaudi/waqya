<?php
/**
 * Single post
 *
 * @package Waqya
 */

get_header();
?>

<div class="page-shell">
    <div class="editorial-layout">
        <div class="editorial-layout__primary">
            <?php
            while (have_posts()) :
                the_post();
                ?>
                <article <?php post_class('single-post'); ?>>
                    <header class="single-post__header">
                        <?php waqya_render_category_follow(); ?>
                        <h1 class="single-post__title"><?php the_title(); ?></h1>
                        <?php if (has_excerpt()) : ?>
                            <p class="single-post__dek"><?php echo esc_html(get_the_excerpt()); ?></p>
                        <?php endif; ?>
                        <p class="single-post__byline">
                            <?php
                            $desk = waqya_desk_byline_label();
                            if ($desk !== '') {
                                echo '<span class="single-post__desk">' . esc_html($desk) . ' desk</span>';
                                echo '<span aria-hidden="true">·</span>';
                            }
                            ?>
                            <time datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                                <?php echo esc_html(waqya_time_ago()); ?>
                            </time>
                            <span aria-hidden="true">·</span>
                            <?php echo esc_html(sprintf(
                                _n('%d min read', '%d min read', waqya_reading_time(), 'waqya'),
                                waqya_reading_time()
                            )); ?>
                            <span aria-hidden="true">·</span>
                            <a href="<?php echo esc_url(home_url('/editorial-policy/')); ?>">
                                <?php esc_html_e('Editorial policy', 'waqya'); ?>
                            </a>
                        </p>
                    </header>

                    <figure class="single-post__featured">
                        <?php waqya_the_thumbnail('waqya-hero', 'single-post__image'); ?>
                        <?php
                        $caption = get_the_post_thumbnail_caption();
                        if ($caption) :
                            ?>
                            <figcaption class="single-post__caption"><?php echo esc_html($caption); ?></figcaption>
                        <?php elseif (has_excerpt()) : ?>
                            <figcaption class="single-post__caption"><?php echo esc_html(get_the_excerpt()); ?></figcaption>
                        <?php endif; ?>
                    </figure>

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
                <?php
                $current_id = get_the_ID();
            endwhile;
            ?>
        </div>

        <?php waqya_render_sidebar([], $current_id ?? null); ?>
    </div>
</div>

<?php
get_footer();
