<?php
/**
 * Weekly digest email (confirmed subscribers only).
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

final class Waqya_Subscribers_Digest
{
    public const CRON_HOOK = 'waqya_send_weekly_digest';

    public static function register(): void
    {
        add_action(self::CRON_HOOK, [self::class, 'send_all']);
        add_action('init', [self::class, 'maybe_schedule']);
    }

    public static function schedule(): void
    {
        if (! wp_next_scheduled(self::CRON_HOOK)) {
            wp_schedule_event(self::next_monday_9am(), 'weekly', self::CRON_HOOK);
        }
    }

    public static function unschedule(): void
    {
        wp_clear_scheduled_hook(self::CRON_HOOK);
    }

    public static function maybe_schedule(): void
    {
        if (! wp_next_scheduled(self::CRON_HOOK)) {
            self::schedule();
        }
    }

    private static function next_monday_9am(): int
    {
        $tz = wp_timezone();
        $now = new DateTimeImmutable('now', $tz);
        $target = $now->modify('next monday')->setTime(9, 0, 0);
        if ($now >= $target) {
            $target = $target->modify('+1 week');
        }
        return $target->getTimestamp();
    }

    public static function send_all(): void
    {
        $subscribers = Waqya_Subscribers_Service::confirmed_subscribers();
        if ($subscribers === []) {
            return;
        }

        $content = self::build_digest_content();
        foreach ($subscribers as $row) {
            self::send_to_subscriber($row, $content);
        }
    }

    /**
     * @return array{headlines: WP_Post[], sections: array<int, WP_Post[]>, topics: string[]}
     */
    public static function build_digest_content(): array
    {
        $since = gmdate('Y-m-d H:i:s', strtotime('-7 days'));

        $headlines = get_posts([
            'post_type'      => 'post',
            'post_status'    => 'publish',
            'posts_per_page' => 6,
            'date_query'     => [
                ['after' => $since, 'inclusive' => true],
            ],
            'orderby'        => 'date',
            'order'          => 'DESC',
        ]);

        $topics = self::hot_topics($since);

        return [
            'headlines' => $headlines,
            'sections'  => [],
            'topics'    => $topics,
        ];
    }

    private static function hot_topics(string $since): array
    {
        $tags = get_terms([
            'taxonomy'   => 'post_tag',
            'orderby'    => 'count',
            'order'      => 'DESC',
            'number'     => 8,
            'hide_empty' => true,
        ]);

        if (is_wp_error($tags) || ! is_array($tags)) {
            return [];
        }

        return array_map(static fn ($t) => $t->name, $tags);
    }

    /**
     * @param array<string, mixed> $row
     * @param array{headlines: WP_Post[], sections: array<int, WP_Post[]>, topics: string[]} $content
     */
    public static function send_to_subscriber(array $row, array $content): void
    {
        $email = $row['email'];
        $cat_ids = [];
        if (! empty($row['category_ids'])) {
            $decoded = json_decode((string) $row['category_ids'], true);
            if (is_array($decoded)) {
                $cat_ids = array_map('intval', $decoded);
            }
        }

        $section_posts = [];
        foreach ($cat_ids as $cat_id) {
            $section_posts[$cat_id] = get_posts([
                'post_type'      => 'post',
                'post_status'    => 'publish',
                'posts_per_page' => 3,
                'cat'            => $cat_id,
                'date_query'     => [
                    ['after' => gmdate('Y-m-d H:i:s', strtotime('-7 days')), 'inclusive' => true],
                ],
            ]);
        }

        $site = get_bloginfo('name');
        $subject = sprintf(
            /* translators: %s: site name */
            __('Your weekly digest — %s', 'waqya-subscribers'),
            $site
        );

        $lines = [sprintf(__('Top stories from %s this week:', 'waqya-subscribers'), $site), ''];

        foreach ($content['headlines'] as $post) {
            $lines[] = '• ' . get_the_title($post);
            $lines[] = '  ' . get_permalink($post);
            $lines[] = '';
        }

        if ($cat_ids !== []) {
            $lines[] = __('From sections you follow:', 'waqya-subscribers');
            $lines[] = '';
            foreach ($cat_ids as $cat_id) {
                $term = get_category($cat_id);
                if (! $term) {
                    continue;
                }
                $posts = $section_posts[$cat_id] ?? [];
                if ($posts === []) {
                    continue;
                }
                $lines[] = $term->name . ':';
                foreach ($posts as $post) {
                    $lines[] = '  • ' . get_the_title($post);
                    $lines[] = '    ' . get_permalink($post);
                }
                $lines[] = '';
            }
        }

        if ($content['topics'] !== []) {
            $lines[] = __('Hot topics:', 'waqya-subscribers') . ' ' . implode(', ', $content['topics']);
            $lines[] = '';
        }

        $lines[] = __('Unsubscribe from this digest:', 'waqya-subscribers');
        $lines[] = Waqya_Subscribers_Actions::unsubscribe_url($row);

        $headers = ['Content-Type: text/plain; charset=UTF-8'];
        /** Allow Reply-To for compliance contact (optional). */
        $reply = apply_filters('waqya_subscribers_reply_to', get_option('admin_email'));
        if (is_email($reply)) {
            $headers[] = 'Reply-To: ' . $reply;
        }

        wp_mail($email, $subject, implode("\n", $lines), $headers);
    }
}
