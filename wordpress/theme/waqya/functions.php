<?php
/**
 * Waqya theme functions
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

define('WAQYA_VERSION', '1.2.0');
define('WAQYA_DIR', get_template_directory());
define('WAQYA_URI', get_template_directory_uri());

require_once WAQYA_DIR . '/inc/helpers.php';
require_once WAQYA_DIR . '/inc/template-tags.php';

/**
 * Theme setup.
 */
function waqya_setup(): void
{
    load_theme_textdomain('waqya', WAQYA_DIR . '/languages');

    add_theme_support('title-tag');
    add_theme_support('post-thumbnails');
    add_theme_support('html5', ['search-form', 'comment-form', 'comment-list', 'gallery', 'caption', 'style', 'script']);
    add_theme_support('responsive-embeds');
    add_theme_support('wp-block-styles');
    add_theme_support('align-wide');
    add_theme_support('editor-styles');
    add_editor_style('assets/css/editor.css');

    add_image_size('waqya-hero', 1200, 675, true);
    add_image_size('waqya-card', 640, 360, true);
    add_image_size('waqya-thumb', 400, 225, true);

    register_nav_menus([
        'primary'   => __('Primary Navigation', 'waqya'),
        'footer'    => __('Footer Navigation', 'waqya'),
        'categories' => __('Category Navigation', 'waqya'),
    ]);
}
add_action('after_setup_theme', 'waqya_setup');

/**
 * Content width for embeds.
 */
function waqya_content_width(): void
{
    $GLOBALS['content_width'] = 720;
}
add_action('after_setup_theme', 'waqya_content_width', 0);

/**
 * Register widget areas.
 */
function waqya_widgets_init(): void
{
    register_sidebar([
        'name'          => __('Sidebar', 'waqya'),
        'id'            => 'sidebar-1',
        'description'   => __('Appears on archive and single posts.', 'waqya'),
        'before_widget' => '<section id="%1$s" class="widget %2$s">',
        'after_widget'  => '</section>',
        'before_title'  => '<h2 class="widget__title">',
        'after_title'   => '</h2>',
    ]);
}
add_action('widgets_init', 'waqya_widgets_init');

/**
 * Enqueue scripts and styles.
 */
function waqya_scripts(): void
{
    wp_enqueue_style(
        'waqya-fonts',
        'https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Fraunces:ital,opsz,wght@0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,500&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400&display=swap',
        [],
        null
    );

    wp_enqueue_style('waqya-main', WAQYA_URI . '/assets/css/main.css', ['waqya-fonts'], WAQYA_VERSION);
    wp_enqueue_script('waqya-main', WAQYA_URI . '/assets/js/main.js', [], WAQYA_VERSION, true);

    if (! is_admin()) {
        wp_dequeue_style('wp-block-library');
        wp_dequeue_style('wp-block-library-theme');
        wp_dequeue_style('classic-theme-styles');
        wp_dequeue_style('global-styles');
        wp_dequeue_style('hostinger-reach-subscription-block');
        wp_dequeue_script('hostinger-reach-subscription-block-view');
    }
}
add_action('wp_enqueue_scripts', 'waqya_scripts', 100);

/**
 * Exclude default-category posts from main blog queries.
 */
function waqya_exclude_junk_from_queries(WP_Query $query): void
{
    if (is_admin() || ! $query->is_main_query()) {
        return;
    }

    if ($query->is_home() || $query->is_archive() || $query->is_search()) {
        $query->set('category__not_in', array_merge(
            (array) $query->get('category__not_in'),
            [(int) get_option('default_category')]
        ));
    }
}
add_action('pre_get_posts', 'waqya_exclude_junk_from_queries');

/**
 * Excerpt length for cards.
 */
function waqya_excerpt_length(int $length): int
{
    return 22;
}
add_filter('excerpt_length', 'waqya_excerpt_length');

/**
 * Excerpt suffix.
 */
function waqya_excerpt_more(string $more): string
{
    return '&hellip;';
}
add_filter('excerpt_more', 'waqya_excerpt_more');

/**
 * Style source attribution paragraphs from the automation pipeline.
 */
function waqya_style_source_attribution(string $content): string
{
    if (! is_singular('post')) {
        return $content;
    }

  // phpcs:ignore WordPress.WP.EnqueuedResources -- inline class only
    return preg_replace(
        '/<p><em>Source:\s*<a\s+/i',
        '<p class="source-attribution"><em>Source: <a ',
        $content,
        1
    ) ?? $content;
}
add_filter('the_content', 'waqya_style_source_attribution', 20);

/**
 * Default category menu fallback — mirrors automation/config.yaml.
 */
function waqya_categories_nav_fallback(): void
{
    $categories = [
        'technology' => __('Technology', 'waqya'),
        'world'      => __('World', 'waqya'),
        'science'    => __('Science', 'waqya'),
        'business'   => __('Business', 'waqya'),
        'opinion'    => __('Opinion', 'waqya'),
    ];

    echo '<ul class="nav-categories__list">';
    foreach ($categories as $slug => $label) {
        $term = get_category_by_slug($slug);
        $url  = $term ? get_category_link($term) : home_url('/category/' . $slug . '/');
        printf(
            '<li class="nav-categories__item"><a class="nav-categories__link" href="%s">%s</a></li>',
            esc_url($url),
            esc_html($label)
        );
    }
    echo '</ul>';
}
