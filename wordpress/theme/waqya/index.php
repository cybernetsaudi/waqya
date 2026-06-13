<?php
/**
 * Fallback template — singular pages/posts, else archives.
 *
 * @package Waqya
 */

if (is_singular('page')) {
    require get_template_directory() . '/page.php';
    return;
}

if (is_singular()) {
    require get_template_directory() . '/single.php';
    return;
}

require get_template_directory() . '/archive.php';
