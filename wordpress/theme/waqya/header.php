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
    <div class="site-header__top">
        <div class="site-header__inner">
            <p class="site-header__date" aria-hidden="true"><?php echo esc_html(date_i18n(get_option('date_format'))); ?></p>
            <div class="site-header__brand">
                <?php if (has_custom_logo()) : ?>
                    <div class="site-header__logo"><?php the_custom_logo(); ?></div>
                <?php else : ?>
                    <a class="site-header__title" href="<?php echo esc_url(home_url('/')); ?>" rel="home">
                        <span class="site-header__title-text"><?php echo esc_html(waqya_site_name()); ?></span>
                        <span class="site-header__tagline"><?php echo esc_html(waqya_site_tagline()); ?></span>
                    </a>
                <?php endif; ?>
            </div>
            <div class="site-header__actions">
                <button type="button" class="site-header__search-toggle" aria-expanded="false" aria-controls="site-search" data-search-toggle>
                    <span class="visually-hidden"><?php esc_html_e('Open search', 'waqya'); ?></span>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3-3"/></svg>
                </button>
                <button type="button" class="site-header__menu-toggle" aria-expanded="false" aria-controls="site-nav" data-menu-toggle>
                    <span class="visually-hidden"><?php esc_html_e('Open menu', 'waqya'); ?></span>
                    <svg class="icon-menu" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>
                    <svg class="icon-close" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
                </button>
            </div>
        </div>
    </div>

    <div id="site-search" class="site-search" hidden>
        <div class="site-search__inner">
            <?php get_search_form(); ?>
        </div>
    </div>

    <nav id="site-nav" class="nav-categories" aria-label="<?php esc_attr_e('Categories', 'waqya'); ?>">
        <div class="nav-categories__inner">
            <?php
            wp_nav_menu([
                'theme_location' => 'categories',
                'container'      => false,
                'menu_class'     => 'nav-categories__list',
                'fallback_cb'    => 'waqya_categories_nav_fallback',
                'depth'          => 1,
            ]);
            ?>
        </div>
    </nav>
</header>

<main id="main-content" class="site-main" role="main">
