<?php
/**
 * Static page template
 *
 * @package Waqya
 */

get_header();

$is_trust = waqya_is_trust_page();
?>

<div class="page-shell<?php echo $is_trust ? ' page-shell--trust' : ''; ?>">
    <div class="editorial-layout<?php echo $is_trust ? ' editorial-layout--trust' : ' editorial-layout--page'; ?>">
        <div class="editorial-layout__primary">
            <?php
            while (have_posts()) :
                the_post();
                $slug = get_post_field('post_name', get_the_ID());
                ?>
                <article <?php post_class($is_trust ? 'static-page static-page--trust' : 'static-page'); ?>>
                    <?php if ($is_trust) : ?>
                        <?php get_template_part('template-parts/page/trust', 'hero'); ?>
                        <div class="static-page__content entry-content trust-body">
                            <?php the_content(); ?>
                        </div>
                        <footer class="trust-page-footer">
                            <p class="trust-page-footer__updated">
                                <?php
                                printf(
                                    /* translators: %s: last modified date */
                                    esc_html__('Last updated %s', 'waqya'),
                                    esc_html(get_the_modified_date())
                                );
                                ?>
                            </p>
                            <nav class="trust-page-footer__nav" aria-label="<?php esc_attr_e('Policies', 'waqya'); ?>">
                                <?php foreach (waqya_trust_page_slugs() as $trust_slug) : ?>
                                    <?php if ($trust_slug === $slug) {
                                        continue;
                                    } ?>
                                    <a href="<?php echo esc_url(home_url('/' . $trust_slug . '/')); ?>">
                                        <?php echo esc_html(waqya_trust_pages_registry()[$trust_slug]['title'] ?? $trust_slug); ?>
                                    </a>
                                <?php endforeach; ?>
                            </nav>
                        </footer>
                    <?php else : ?>
                        <header class="static-page__header">
                            <h1 class="static-page__title"><?php waqya_the_title(); ?></h1>
                        </header>
                        <div class="static-page__content entry-content">
                            <?php the_content(); ?>
                        </div>
                    <?php endif; ?>
                </article>
                <?php
            endwhile;
            ?>
        </div>

        <?php if ($is_trust) : ?>
            <?php get_template_part('template-parts/page/trust', 'rail'); ?>
        <?php endif; ?>
    </div>
</div>

<?php
get_footer();
