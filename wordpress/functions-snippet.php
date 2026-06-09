<?php
/**
 * Optional helper for WordPress theme functions.php.
 */

add_filter('rest_pre_insert_post', function ($prepared_post, $request) {
    if (isset($request['yoast_title'])) {
        update_post_meta($prepared_post->ID, '_yoast_wpseo_title', sanitize_text_field($request['yoast_title']));
    }
    if (isset($request['yoast_metadesc'])) {
        update_post_meta($prepared_post->ID, '_yoast_wpseo_metadesc', sanitize_text_field($request['yoast_metadesc']));
    }
    return $prepared_post;
}, 10, 2);
