<?php
if (! defined('ABSPATH')) {
	exit;
}

function sblogical_setup(): void {
	add_theme_support('title-tag');
	add_theme_support('post-thumbnails');
	add_theme_support(
		'html5',
		array(
			'comment-form',
			'comment-list',
			'gallery',
			'caption',
			'search-form',
		)
	);
	add_theme_support(
		'custom-logo',
		array(
			'height'      => 120,
			'width'       => 320,
			'flex-height' => true,
			'flex-width'  => true,
		)
	);

	register_nav_menus(
		array(
			'primary' => __('Primary Menu', 'sblogical'),
			'footer'  => __('Footer Menu', 'sblogical'),
		)
	);
}
add_action('after_setup_theme', 'sblogical_setup');

function sblogical_assets(): void {
	wp_enqueue_style(
		'sblogical-style',
		get_stylesheet_uri(),
		array(),
		wp_get_theme()->get('Version')
	);
}
add_action('wp_enqueue_scripts', 'sblogical_assets');

function sblogical_menu_fallback(): void {
	echo '<ul class="menu">';
	wp_list_pages(
		array(
			'title_li' => '',
			'depth'    => 1,
		)
	);
	echo '</ul>';
}
