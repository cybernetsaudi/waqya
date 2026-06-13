<?php
/**
 * Search results with desk shortcuts
 *
 * @package Waqya
 */

get_header();

$query = get_search_query();
$desks = waqya_primary_categories();
?>

<div class="page-shell">
    <div class="editorial-layout">
        <div class="editorial-layout__primary">
            <header class="page-header">
                <h1 class="page-header__title">
                    <?php
                    printf(
                        esc_html__('Results for “%s”', 'waqya'),
                        esc_html($query)
                    );
                    ?>
                </h1>
                <?php if ($query !== '') : ?>
                    <p class="page-header__dek">
                        <?php esc_html_e('Search headlines and analysis across all desks.', 'waqya'); ?>
                    </p>
                <?php endif; ?>
            </header>

            <?php if ($desks !== []) : ?>
                <nav class="search-desks" aria-label="<?php esc_attr_e('Browse by desk', 'waqya'); ?>">
                    <span class="search-desks__label"><?php esc_html_e('Or browse:', 'waqya'); ?></span>
                    <ul class="search-desks__list">
                        <?php foreach (array_slice($desks, 0, 12) as $key => $meta) : ?>
                            <?php
                            $url = waqya_category_url((string) $key);
                            if ($url === '') {
                                continue;
                            }
                            ?>
                            <li>
                                <a class="search-desks__link" href="<?php echo esc_url($url); ?>">
                                    <?php echo esc_html((string) ($meta['label'] ?? $key)); ?>
                                </a>
                            </li>
                        <?php endforeach; ?>
                    </ul>
                </nav>
            <?php endif; ?>

            <?php waqya_render_date_filter(); ?>

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
                <section class="empty-state">
                    <h2 class="empty-state__title"><?php esc_html_e('No matches', 'waqya'); ?></h2>
                    <p class="empty-state__text">
                        <?php esc_html_e('Try different keywords, pick a desk above, or browse the homepage.', 'waqya'); ?>
                    </p>
                    <?php get_search_form(); ?>
                    <p class="empty-state__actions">
                        <a class="button-link" href="<?php echo esc_url(home_url('/')); ?>">
                            <?php esc_html_e('Back to homepage', 'waqya'); ?>
                        </a>
                    </p>
                </section>
            <?php endif; ?>
        </div>
        <?php waqya_render_sidebar(); ?>
    </div>
</div>

<?php
get_footer();
