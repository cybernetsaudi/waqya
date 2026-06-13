<?php
/**
 * Google News sitemap (recent articles, last 48 hours).
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

/**
 * Register /news-sitemap.xml rewrite.
 */
function waqya_news_sitemap_rewrite(): void
{
    add_rewrite_rule('^news-sitemap\.xml$', 'index.php?waqya_news_sitemap=1', 'top');
}
add_action('init', 'waqya_news_sitemap_rewrite');

/**
 * @param array<string, string> $vars
 * @return array<string, string>
 */
function waqya_news_sitemap_query_var(array $vars): array
{
    $vars[] = 'waqya_news_sitemap';
    return $vars;
}
add_filter('query_vars', 'waqya_news_sitemap_query_var');

function waqya_news_sitemap_requested(): bool
{
    if (get_query_var('waqya_news_sitemap')) {
        return true;
    }

    $uri = isset($_SERVER['REQUEST_URI']) ? (string) wp_unslash($_SERVER['REQUEST_URI']) : '';
    return (bool) preg_match('#/news-sitemap\.xml/?$#', $uri);
}

/**
 * News sitemap must not return HTTP 404 (Google rejects it).
 *
 * @param bool     $preempt
 * @param WP_Query $query
 */
function waqya_news_sitemap_pre_handle_404(bool $preempt, WP_Query $query): bool
{
    if (waqya_news_sitemap_requested()) {
        $query->is_404 = false;
        return true;
    }

    return $preempt;
}
add_filter('pre_handle_404', 'waqya_news_sitemap_pre_handle_404', 10, 2);

function waqya_news_sitemap_render(): void
{
    if (! waqya_news_sitemap_requested()) {
        return;
    }

    status_header(200);
    nocache_headers();

    $posts = get_posts([
        'post_type'      => 'post',
        'post_status'    => 'publish',
        'posts_per_page' => 100,
        'date_query'     => [
            ['after' => '2 days ago', 'inclusive' => true],
        ],
        'orderby'        => 'date',
        'order'          => 'DESC',
    ]);

    $site = waqya_site_name();
    $lang = str_replace('_', '-', get_bloginfo('language'));

    header('Content-Type: application/xml; charset=UTF-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n";
    ?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
<?php foreach ($posts as $post) : ?>
  <url>
    <loc><?php echo esc_url(get_permalink($post)); ?></loc>
    <news:news>
      <news:publication>
        <news:name><?php echo esc_html($site); ?></news:name>
        <news:language><?php echo esc_html($lang); ?></news:language>
      </news:publication>
      <news:publication_date><?php echo esc_html(get_post_time('c', true, $post)); ?></news:publication_date>
      <news:title><?php echo esc_html(get_the_title($post)); ?></news:title>
    </news:news>
  </url>
<?php endforeach; ?>
</urlset>
    <?php
    exit;
}
add_action('template_redirect', 'waqya_news_sitemap_render', 1);

/**
 * Advertise news sitemap in robots.txt.
 */
function waqya_news_sitemap_robots(string $output): string
{
    $output .= 'Sitemap: ' . esc_url(home_url('/news-sitemap.xml')) . "\n";
    return $output;
}
add_filter('robots_txt', 'waqya_news_sitemap_robots', 20);
