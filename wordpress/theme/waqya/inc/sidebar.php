<?php
/**
 * Sidebar rendering
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

if (! function_exists('waqya_sidebar_post_ids')) {
    /**
     * Post IDs reserved for the sidebar column.
     *
     * @param int[] $exclude
     * @return int[]
     */
    function waqya_sidebar_post_ids(array $exclude = []): array
    {
        $exclude = array_values(array_unique(array_filter(array_merge(
            waqya_excluded_post_ids(),
            array_map('intval', $exclude)
        ))));

        $query = new WP_Query([
            'post_type'           => 'post',
            'post_status'         => 'publish',
            'posts_per_page'      => 6,
            'post__not_in'        => $exclude,
            'fields'              => 'ids',
            'ignore_sticky_posts' => true,
        ]);

        return array_map('intval', $query->posts);
    }
}

if (! function_exists('waqya_render_sidebar')) {
    /**
     * Render the editorial sidebar (top stories + explore).
     *
     * @param int[]    $exclude Post IDs to skip.
     * @param int|null $current Current post ID when on a single article.
     */
    function waqya_render_sidebar(array $exclude = [], ?int $current = null): void
    {
        if ($current) {
            $exclude[] = $current;
        }

        $exclude = array_values(array_unique(array_filter(array_merge(
            waqya_excluded_post_ids(),
            array_map('intval', $exclude)
        ))));

        $top_stories = new WP_Query([
            'post_type'           => 'post',
            'post_status'         => 'publish',
            'posts_per_page'      => 5,
            'post__not_in'        => $exclude,
            'ignore_sticky_posts' => true,
        ]);

        $sidebar_ids = $exclude;
        if ($top_stories->have_posts()) {
            foreach ($top_stories->posts as $post) {
                $sidebar_ids[] = (int) (is_object($post) ? $post->ID : $post);
            }
        }

        $explore = new WP_Query([
            'post_type'           => 'post',
            'post_status'         => 'publish',
            'posts_per_page'      => 1,
            'post__not_in'        => $sidebar_ids,
            'ignore_sticky_posts' => true,
        ]);

        if (! $top_stories->have_posts() && ! $explore->have_posts()) {
            return;
        }

        echo '<aside class="editorial-sidebar" aria-label="' . esc_attr__('Related coverage', 'waqya') . '">';

        if ($top_stories->have_posts()) {
            echo '<section class="sidebar-panel">';
            echo '<h2 class="sidebar-panel__title">' . esc_html__('Top stories', 'waqya') . '</h2>';
            echo '<ol class="story-list">';
            while ($top_stories->have_posts()) {
                $top_stories->the_post();
                get_template_part('template-parts/content', 'story-list');
            }
            echo '</ol>';
            echo '</section>';
            wp_reset_postdata();
        }

        if ($explore->have_posts()) {
            echo '<section class="sidebar-panel sidebar-panel--explore">';
            echo '<h2 class="sidebar-panel__title">' . esc_html__('More to explore', 'waqya') . '</h2>';
            while ($explore->have_posts()) {
                $explore->the_post();
                get_template_part('template-parts/content', 'explore');
            }
            echo '</section>';
            wp_reset_postdata();
        }

        echo '</aside>';
    }
}

if (! function_exists('waqya_section_label')) {
    /**
     * Section label for the brand bar.
     */
    function waqya_section_label(): string
    {
        if (is_category()) {
            return single_cat_title('', false);
        }

        if (is_single()) {
            $categories = get_the_category();
            if (! empty($categories)) {
                return $categories[0]->name;
            }
        }

        if (is_search()) {
            return __('Search', 'waqya');
        }

        if (is_archive()) {
            return __('Archive', 'waqya');
        }

        if (is_front_page()) {
            return waqya_brand_meaning();
        }

        return __('Commentary', 'waqya');
    }
}
