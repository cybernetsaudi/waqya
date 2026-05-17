<?php
/**
 * Subscribe modal (first visit + follow triggers).
 *
 * @package Waqya_Subscribers
 */

if (! defined('ABSPATH')) {
    exit;
}

$privacy = Waqya_Subscribers_Frontend::privacy_url();
$consent = Waqya_Subscribers_Frontend::consent_label();
?>
<div
    id="waqya-subscribe-modal"
    class="waqya-modal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="waqya-subscribe-title"
    hidden
>
    <div class="waqya-modal__backdrop" data-waqya-modal-close tabindex="-1"></div>
    <div class="waqya-modal__panel">
        <button type="button" class="waqya-modal__close" data-waqya-modal-close aria-label="<?php esc_attr_e('Close', 'waqya-subscribers'); ?>">
            <span aria-hidden="true">&times;</span>
        </button>
        <h2 id="waqya-subscribe-title" class="waqya-modal__title">
            <?php esc_html_e('Get the weekly digest', 'waqya-subscribers'); ?>
        </h2>
        <p class="waqya-modal__subtitle">
            <?php esc_html_e('Top stories and hot topics from Waqya — once a week. We only email after you confirm.', 'waqya-subscribers'); ?>
        </p>

        <form class="waqya-modal__form" data-waqya-subscribe-form novalidate>
            <input type="text" name="website" class="waqya-modal__honeypot" tabindex="-1" autocomplete="off" aria-hidden="true">

            <label class="waqya-modal__label" for="waqya-subscribe-email">
                <?php esc_html_e('Email address', 'waqya-subscribers'); ?>
            </label>
            <input
                id="waqya-subscribe-email"
                class="waqya-modal__input"
                type="email"
                name="email"
                required
                autocomplete="email"
                placeholder="you@example.com"
            >

            <p class="waqya-modal__section-note" data-waqya-section-note hidden></p>

            <label class="waqya-modal__consent">
                <input type="checkbox" name="consent_digest" value="1" required>
                <span>
                    <?php echo esc_html($consent); ?>
                    <a href="<?php echo esc_url($privacy); ?>" target="_blank" rel="noopener noreferrer">
                        <?php esc_html_e('Privacy Policy', 'waqya-subscribers'); ?>
                    </a>
                </span>
            </label>

            <input type="hidden" name="category_ids[]" value="" data-waqya-category-input>

            <p class="waqya-modal__message" data-waqya-form-message role="status" aria-live="polite"></p>

            <button type="submit" class="waqya-modal__submit">
                <?php esc_html_e('Subscribe', 'waqya-subscribers'); ?>
            </button>
        </form>
    </div>
</div>
