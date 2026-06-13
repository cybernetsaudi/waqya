<?php
/**
 * Trust page sidebar — related policies + latest desk stories
 *
 * @package Waqya
 */

$slug = get_post_field('post_name', get_the_ID());
$siblings = waqya_trust_page_siblings($slug);

$latest = new WP_Query([
    'post_type'           => 'post',
    'post_status'         => 'publish',
    'posts_per_page'      => 4,
    'ignore_sticky_posts' => true,
    'no_found_rows'       => true,
]);
?>
<aside class="trust-rail" aria-label="<?php esc_attr_e('Related', 'waqya'); ?>">
    <section class="trust-rail__panel">
        <h2 class="trust-rail__title"><?php esc_html_e('Policies', 'waqya'); ?></h2>
        <ul class="trust-rail__links">
            <?php foreach ($siblings as $item) : ?>
                <li>
                    <a href="<?php echo esc_url(home_url('/' . $item['slug'] . '/')); ?>">
                        <span class="trust-rail__link-title"><?php echo esc_html($item['title']); ?></span>
                        <?php if ($item['dek'] !== '') : ?>
                            <span class="trust-rail__link-dek"><?php echo esc_html($item['dek']); ?></span>
                        <?php endif; ?>
                    </a>
                </li>
            <?php endforeach; ?>
        </ul>
    </section>

    <?php if ($latest->have_posts()) : ?>
        <section class="trust-rail__panel trust-rail__panel--stories">
            <h2 class="trust-rail__title"><?php esc_html_e('Latest analysis', 'waqya'); ?></h2>
            <ul class="trust-rail__stories">
                <?php
                while ($latest->have_posts()) {
                    $latest->the_post();
                    ?>
                    <li>
                        <a href="<?php the_permalink(); ?>">
                            <span class="trust-rail__story-title"><?php waqya_the_title(); ?></span>
                            <time datetime="<?php echo esc_attr(get_the_date(DATE_W3C)); ?>">
                                <?php echo esc_html(waqya_time_ago()); ?>
                            </time>
                        </a>
                    </li>
                    <?php
                }
                wp_reset_postdata();
                ?>
            </ul>
            <a class="trust-rail__all" href="<?php echo esc_url(home_url('/')); ?>">
                <?php esc_html_e('All stories', 'waqya'); ?> →
            </a>
        </section>
    <?php endif; ?>
</aside>
