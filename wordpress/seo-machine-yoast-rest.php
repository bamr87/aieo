<?php
/**
 * Plugin Name: SEO Machine Yoast REST Fields
 * Description: Exposes Yoast fields for REST publishing.
 */

add_action('rest_api_init', function () {
    register_rest_field('post', 'yoast_title', array(
        'get_callback' => function ($post) {
            return get_post_meta($post['id'], '_yoast_wpseo_title', true);
        },
        'update_callback' => function ($value, $post) {
            update_post_meta($post->ID, '_yoast_wpseo_title', sanitize_text_field($value));
        },
    ));
    register_rest_field('post', 'yoast_metadesc', array(
        'get_callback' => function ($post) {
            return get_post_meta($post['id'], '_yoast_wpseo_metadesc', true);
        },
        'update_callback' => function ($value, $post) {
            update_post_meta($post->ID, '_yoast_wpseo_metadesc', sanitize_text_field($value));
        },
    ));
});
