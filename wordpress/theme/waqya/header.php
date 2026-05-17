<?php
/**
 * Header template
 *
 * @package Waqya
 */
?><!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
    <?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>

<a class="skip-link" href="#main-content"><?php esc_html_e('Skip to content', 'waqya'); ?></a>

<header class="site-header" role="banner">
    <div class="site-header__utility">
        <div class="site-header__utility-inner">
            <?php get_template_part('template-parts/brand/logo'); ?>
            <div class="site-header__actions">
                <button type="button" class="site-header__search-toggle" aria-expanded="false" aria-controls="site-search" data-search-toggle>
                    <span class="visually-hidden"><?php esc_html_e('Search', 'waqya'); ?></span>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3-3"/></svg>
                    <span class="site-header__search-label" aria-hidden="true"><?php esc_html_e('Search', 'waqya'); ?></span>
                </button>
                <button type="button" class="site-header__menu-toggle" aria-expanded="false" aria-controls="site-nav" data-menu-toggle>
                    <span class="visually-hidden"><?php esc_html_e('Sections', 'waqya'); ?></span>
                    <svg class="icon-menu" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
                    <svg class="icon-close" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
                </button>
            </div>
        </div>
    </div>

    <div class="site-brand-bar<?php echo is_front_page() ? ' site-brand-bar--home' : ''; ?>">
        <div class="site-brand-bar__inner<?php echo is_front_page() ? ' site-brand-bar__inner--split' : ''; ?>">
            <?php if (is_front_page()) : ?>
                <div class="site-brand-bar__primary">
                    <p class="site-brand-bar__meaning"><?php echo esc_html(waqya_brand_meaning()); ?></p>
                    <p class="site-brand-bar__name"><?php echo esc_html(waqya_site_name()); ?></p>
                    <p class="site-brand-bar__tagline"><?php echo esc_html(waqya_brand_story_short()); ?></p>
                </div>
                <aside class="site-brand-bar__about" aria-labelledby="site-brand-about-title">
                    <p id="site-brand-about-title" class="site-brand-bar__about-label"><?php esc_html_e('About the name', 'waqya'); ?></p>
                    <details class="site-brand-bar__about-details">
                        <summary class="site-brand-bar__about-summary"><?php esc_html_e('Read why we chose Waqya', 'waqya'); ?></summary>
                        <p class="site-brand-bar__about-body"><?php echo esc_html(waqya_brand_story_long()); ?></p>
                    </details>
                </aside>
            <?php else : ?>
                <p class="site-brand-bar__label">
                    <?php echo esc_html(waqya_section_label()); ?>
                    <span class="site-brand-bar__label-meaning"><?php echo esc_html(waqya_brand_meaning()); ?></span>
                </p>
            <?php endif; ?>
        </div>
    </div>

    <div id="site-search" class="site-search" hidden>
        <div class="site-search__inner">
            <?php get_search_form(); ?>
        </div>
    </div>

    <nav id="site-nav" class="site-nav-section" aria-label="<?php esc_attr_e('Sections', 'waqya'); ?>">
        <div class="site-nav-section__inner">
            <?php
            if (has_nav_menu('categories')) {
                wp_nav_menu([
                    'theme_location' => 'categories',
                    'container'      => false,
                    'menu_class'     => 'site-nav-section__list',
                    'depth'          => 1,
                ]);
            } else {
                get_template_part('template-parts/nav/menu', 'groups');
            }
            ?>
        </div>
    </nav>

    <?php if (! is_front_page()) : ?>
        <div class="site-context-bar">
            <div class="site-context-bar__inner">
                <?php waqya_breadcrumbs(); ?>
            </div>
        </div>
    <?php endif; ?>
</header>

<main id="main-content" class="site-main" role="main">
