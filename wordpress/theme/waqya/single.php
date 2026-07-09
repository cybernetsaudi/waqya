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
                    <?php waqya_render_developing_ribbon(); ?>
                    <header class="single-post__header">
                        <?php waqya_render_category_follow(); ?>
                        <?php if (waqya_is_on_the_record()) : ?>
                            <div class="single-post__format">
                                <span class="badge badge--on-the-record"><?php esc_html_e('On The Record', 'waqya'); ?></span>
                                <span class="single-post__format-note"><?php esc_html_e('Opinion · Interview review', 'waqya'); ?></span>
                                <?php
                                $tone_label = waqya_interview_tone_label();
                                if ($tone_label !== '') :
                                    ?>
                                    <span class="single-post__tone"><?php echo esc_html($tone_label); ?></span>
                                <?php endif; ?>
                            </div>
                        <?php endif; ?>
                        <h1 class="single-post__title"><?php waqya_the_title(); ?></h1>
                        <?php
                        $headline_ar = (string) get_post_meta(get_the_ID(), '_waqya_headline_ar', true);
                        $headline_ur = (string) get_post_meta(get_the_ID(), '_waqya_headline_ur', true);
                        if ($headline_ar !== '' || $headline_ur !== '') :
                            ?>
                            <div class="single-post__locales" lang="multi">
                                <?php if ($headline_ar !== '') : ?>
                                    <p class="single-post__locale" lang="ar" dir="rtl"><?php echo esc_html($headline_ar); ?></p>
                                <?php endif; ?>
                                <?php if ($headline_ur !== '') : ?>
                                    <p class="single-post__locale" lang="ur" dir="rtl"><?php echo esc_html($headline_ur); ?></p>
                                <?php endif; ?>
                            </div>
                        <?php endif; ?>
                        <?php if (has_excerpt()) : ?>
                            <p class="single-post__dek"><?php waqya_the_excerpt(); ?></p>
                        <?php endif; ?>
                        <div class="single-post__byline">
                            <?php
                            $desk = waqya_desk_byline_label();
                            if ($desk !== '') {
                                echo '<span class="single-post__desk">' . esc_html($desk) . ' desk</span>';
                            }
                            waqya_render_dateline('single');
                            ?>
                            <p class="single-post__byline-meta">
                                <?php echo esc_html(sprintf(
                                    _n('%d min read', '%d min read', waqya_reading_time(), 'waqya'),
                                    waqya_reading_time()
                                )); ?>
                                <span aria-hidden="true">·</span>
                                <a href="<?php echo esc_url(home_url('/editorial-policy/')); ?>">
                                    <?php esc_html_e('Editorial policy', 'waqya'); ?>
                                </a>
                            </p>
                        </div>
                    </header>

                    <figure class="single-post__featured">
                        <?php waqya_the_thumbnail('waqya-hero', 'single-post__image'); ?>
                        <?php
                        $caption = get_the_post_thumbnail_caption();
                        if ($caption) :
                            ?>
                            <figcaption class="single-post__caption"><?php echo esc_html($caption); ?></figcaption>
                        <?php elseif (has_excerpt()) : ?>
                            <figcaption class="single-post__caption"><?php waqya_the_excerpt(); ?></figcaption>
                        <?php endif; ?>
                    </figure>

                    <?php waqya_render_update_log(); ?>

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

                    <?php waqya_render_follow_promo('article'); ?>
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
