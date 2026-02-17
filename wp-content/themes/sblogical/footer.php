<?php
/**
 * Theme footer.
 *
 * @package sblogical
 */
?>
</main>
<footer class="site-footer container">
	<div class="footer-wrap">
		<p class="footer-copy">
			&copy; <?php echo esc_html(wp_date('Y')); ?> <?php bloginfo('name'); ?>.
			<?php esc_html_e('Built with clarity and consistency.', 'sblogical'); ?>
		</p>
		<nav aria-label="<?php esc_attr_e('Footer menu', 'sblogical'); ?>">
			<?php
			wp_nav_menu(
				array(
					'theme_location' => 'footer',
					'container'      => false,
					'menu_class'     => 'menu',
					'fallback_cb'    => false,
					'depth'          => 1,
				)
			);
			?>
		</nav>
	</div>
</footer>
<?php wp_footer(); ?>
</body>
</html>
