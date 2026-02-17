<?php
/**
 * Theme header.
 *
 * @package sblogical
 */
?>
<!doctype html>
<html <?php language_attributes(); ?>>
<head>
	<meta charset="<?php bloginfo('charset'); ?>">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<?php wp_head(); ?>
</head>
<body <?php body_class(); ?>>
<?php wp_body_open(); ?>
<header class="site-header">
	<div class="container top-bar">
		<div class="brand">
			<?php if (has_custom_logo()) : ?>
				<?php the_custom_logo(); ?>
			<?php endif; ?>
			<a class="brand__name" href="<?php echo esc_url(home_url('/')); ?>">
				<?php bloginfo('name'); ?>
			</a>
			<?php if (get_bloginfo('description')) : ?>
				<p class="brand__tagline"><?php bloginfo('description'); ?></p>
			<?php endif; ?>
		</div>
		<nav class="primary-nav" aria-label="<?php esc_attr_e('Primary menu', 'sblogical'); ?>">
			<?php
			wp_nav_menu(
				array(
					'theme_location' => 'primary',
					'container'      => false,
					'menu_class'     => 'menu',
					'fallback_cb'    => 'sblogical_menu_fallback',
				)
			);
			?>
		</nav>
		<a class="button button--ghost" href="<?php echo esc_url(home_url('/contact')); ?>">
			<?php esc_html_e('Start a Project', 'sblogical'); ?>
		</a>
	</div>
</header>
<main class="site-main container">
