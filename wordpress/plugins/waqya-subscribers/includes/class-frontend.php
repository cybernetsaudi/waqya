<?php
/**
 * Modal, assets, and follow button helpers.
 *
 * @package Waqya_Subscribers
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

final class Waqya_Subscribers_Frontend
{
    public static function register(): void
    {
        add_action('wp_enqueue_scripts', [self::class, 'assets']);
        add_action('wp_footer', [self::class, 'render_modal']);
    }

    public static function assets(): void
    {
        if (is_admin()) {
            return;
        }

        wp_enqueue_style(
            'waqya-subscribers',
            WAQYA_SUB_URI . 'assets/subscribe.css',
            [],
            WAQYA_SUB_VERSION
        );
        wp_enqueue_script(
            'waqya-subscribers',
            WAQYA_SUB_URI . 'assets/subscribe.js',
            [],
            WAQYA_SUB_VERSION,
            true
        );

        wp_localize_script('waqya-subscribers', 'waqyaSubscribe', [
            'restUrl'        => rest_url('waqya/v1/subscribe'),
            'nonce'          => wp_create_nonce('wp_rest'),
            'privacyUrl'     => self::privacy_url(),
            'consentText'    => self::consent_label(),
            'showAutoPrompt' => (bool) apply_filters('waqya_subscribers_show_auto_prompt', true),
            'i18n'        => [
                'follow'       => __('+ Follow', 'waqya-subscribers'),
                'following'    => __('Following', 'waqya-subscribers'),
                'title'        => __('Get the weekly digest', 'waqya-subscribers'),
                'subtitle'     => __('Top stories and hot topics from Waqya — once a week, no spam.', 'waqya-subscribers'),
                'email'        => __('Email address', 'waqya-subscribers'),
                'submit'       => __('Subscribe', 'waqya-subscribers'),
                'close'        => __('Close', 'waqya-subscribers'),
                'success'      => __('Check your email to confirm your subscription.', 'waqya-subscribers'),
                'error'        => __('Something went wrong. Please try again.', 'waqya-subscribers'),
                'followSection'=> __('Include stories from this section in my digest', 'waqya-subscribers'),
            ],
        ]);
    }

    public static function privacy_url(): string
    {
        $page = get_privacy_policy_url();
        return $page ?: home_url('/privacy-policy/');
    }

    public static function consent_label(): string
    {
        return __(
            'I agree to receive the weekly Waqya email digest. I can unsubscribe at any time. See the Privacy Policy.',
            'waqya-subscribers'
        );
    }

    public static function render_modal(): void
    {
        if (is_admin()) {
            return;
        }
        include WAQYA_SUB_DIR . 'templates/modal.php';
    }

    /**
     * Category badge row with +Follow (for single posts).
     */
    public static function category_follow_row(): void
    {
        $categories = get_the_category();
        if (empty($categories)) {
            return;
        }

        $cat = $categories[0];
        $slug = sanitize_html_class($cat->slug);
        ?>
        <div class="category-follow" data-category-follow>
            <a class="badge badge--<?php echo esc_attr($slug); ?>" href="<?php echo esc_url(get_category_link($cat)); ?>">
                <?php echo esc_html($cat->name); ?>
            </a>
            <button
                type="button"
                class="category-follow__btn"
                data-waqya-follow
                data-category-id="<?php echo (int) $cat->term_id; ?>"
                data-category-name="<?php echo esc_attr($cat->name); ?>"
                aria-haspopup="dialog"
            >
                <?php esc_html_e('+ Follow', 'waqya-subscribers'); ?>
            </button>
        </div>
        <?php
    }
}
