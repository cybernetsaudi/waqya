<?php
/**
 * Search form
 *
 * @package Waqya
 */
?>
<form role="search" method="get" class="search-form" action="<?php echo esc_url(home_url('/')); ?>">
    <label class="search-form__label" for="search-field"><?php esc_html_e('Search articles', 'waqya'); ?></label>
    <input
        type="search"
        id="search-field"
        class="search-form__input"
        placeholder="<?php esc_attr_e('Search headlines…', 'waqya'); ?>"
        value="<?php echo esc_attr(get_search_query()); ?>"
        name="s"
    />
    <button type="submit" class="search-form__submit"><?php esc_html_e('Search', 'waqya'); ?></button>
</form>
