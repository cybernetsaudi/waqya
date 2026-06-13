<?php
/**
 * Cookie consent UI and client-side analytics activation.
 *
 * @package Waqya
 */

declare(strict_types=1);

if (! defined('ABSPATH')) {
    exit;
}

function waqya_consent_privacy_url(): string
{
    $url = get_privacy_policy_url();
    return $url ?: home_url('/privacy-policy/');
}

function waqya_consent_cookie_url(): string
{
    return home_url('/privacy-policy/#cookies');
}

function waqya_plausible_domain(): string
{
    return (string) get_option('waqya_plausible_domain', '');
}

function waqya_consent_assets(): void
{
    if (is_admin()) {
        return;
    }

    wp_enqueue_style(
        'waqya-consent',
        WAQYA_URI . '/assets/css/consent.css',
        [],
        WAQYA_VERSION
    );
    wp_enqueue_script(
        'waqya-consent',
        WAQYA_URI . '/assets/js/consent.js',
        [],
        WAQYA_VERSION,
        true
    );
    wp_localize_script('waqya-consent', 'waqyaConsent', [
        'privacyUrl'  => waqya_consent_privacy_url(),
        'cookieUrl'   => waqya_consent_cookie_url(),
        'plausible'   => waqya_plausible_domain(),
        'storageKey'  => 'waqya_consent_v1',
        'strings'     => [
            'title'       => __('Privacy & cookies', 'waqya'),
            'intro'       => __('We use essential cookies to run the site. Analytics cookies help us understand readership — only if you agree.', 'waqya'),
            'accept'      => __('Accept analytics', 'waqya'),
            'reject'      => __('Reject non-essential', 'waqya'),
            'manage'      => __('Cookie settings', 'waqya'),
            'save'        => __('Save choices', 'waqya'),
            'analytics'   => __('Analytics (traffic & engagement)', 'waqya'),
            'necessary'   => __('Strictly necessary (always on)', 'waqya'),
        ],
    ]);
}
add_action('wp_enqueue_scripts', 'waqya_consent_assets', 5);

/**
 * Gate theme-injected Plausible tag (not enqueued via WP).
 */
function waqya_gate_plausible_in_head(): void
{
    if (is_admin()) {
        return;
    }
    $domain = waqya_plausible_domain();
    if ($domain === '') {
        return;
    }
    printf(
        '<script type="text/plain" data-waqya-consent="analytics" data-plausible-domain="%s" id="waqya-plausible-deferred"></script>' . "\n",
        esc_attr($domain)
    );
}
add_action('wp_head', 'waqya_gate_plausible_in_head', 98);

function waqya_render_consent_banner(): void
{
    if (is_admin()) {
        return;
    }
    ?>
    <div id="waqya-consent" class="waqya-consent" role="dialog" aria-labelledby="waqya-consent-title" aria-hidden="true" hidden>
        <div class="waqya-consent__panel">
            <h2 id="waqya-consent-title" class="waqya-consent__title"><?php esc_html_e('Privacy & cookies', 'waqya'); ?></h2>
            <p class="waqya-consent__intro">
                <?php esc_html_e('We use essential storage to run Waqya (e.g. dismissing this notice). Analytics helps us measure traffic and improve the site — only with your consent. See our Privacy Policy.', 'waqya'); ?>
            </p>
            <div class="waqya-consent__prefs" id="waqya-consent-prefs" hidden>
                <label class="waqya-consent__check waqya-consent__check--disabled">
                    <input type="checkbox" checked disabled>
                    <span><?php esc_html_e('Strictly necessary', 'waqya'); ?></span>
                </label>
                <label class="waqya-consent__check">
                    <input type="checkbox" name="analytics" id="waqya-consent-analytics">
                    <span><?php esc_html_e('Analytics (Google Analytics & Plausible)', 'waqya'); ?></span>
                </label>
            </div>
            <div class="waqya-consent__actions">
                <button type="button" class="waqya-consent__btn waqya-consent__btn--primary" data-waqya-consent="accept">
                    <?php esc_html_e('Accept analytics', 'waqya'); ?>
                </button>
                <button type="button" class="waqya-consent__btn" data-waqya-consent="reject">
                    <?php esc_html_e('Reject non-essential', 'waqya'); ?>
                </button>
                <button type="button" class="waqya-consent__btn waqya-consent__btn--ghost" data-waqya-consent="manage">
                    <?php esc_html_e('Cookie settings', 'waqya'); ?>
                </button>
                <button type="button" class="waqya-consent__btn waqya-consent__btn--primary" data-waqya-consent="save" hidden>
                    <?php esc_html_e('Save choices', 'waqya'); ?>
                </button>
            </div>
            <p class="waqya-consent__links">
                <a href="<?php echo esc_url(waqya_consent_privacy_url()); ?>"><?php esc_html_e('Privacy Policy', 'waqya'); ?></a>
                ·
                <a href="<?php echo esc_url(waqya_consent_cookie_url()); ?>"><?php esc_html_e('Cookie details', 'waqya'); ?></a>
            </p>
        </div>
    </div>
    <?php
}
add_action('wp_footer', 'waqya_render_consent_banner', 5);

/**
 * Footer link to reopen cookie settings.
 */
function waqya_footer_privacy_links(): void
{
    ?>
    <p class="site-footer__legal">
        <a href="<?php echo esc_url(waqya_consent_privacy_url()); ?>"><?php esc_html_e('Privacy Policy', 'waqya'); ?></a>
        <span aria-hidden="true">·</span>
        <button type="button" class="site-footer__cookie-btn" data-waqya-open-consent>
            <?php esc_html_e('Cookie settings', 'waqya'); ?>
        </button>
    </p>
    <?php
}
