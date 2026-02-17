<?php
/**
 * Main template file.
 *
 * @package sblogical
 */

get_header();
?>
<section class="section">
	<?php if (is_home() && ! is_front_page()) : ?>
		<h1 class="section__title"><?php single_post_title(); ?></h1>
	<?php else : ?>
		<h1 class="section__title"><?php esc_html_e('Latest Posts', 'sblogical'); ?></h1>
	<?php endif; ?>
	<div class="post-list">
		<?php if (have_posts()) : ?>
			<?php while (have_posts()) : the_post(); ?>
				<article <?php post_class('post-card'); ?>>
					<p class="post-meta">
						<?php echo esc_html(get_the_date()); ?> · <?php the_category(', '); ?>
					</p>
					<h2><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h2>
					<?php the_excerpt(); ?>
				</article>
			<?php endwhile; ?>
		<?php else : ?>
			<article class="post-card">
				<h2><?php esc_html_e('Nothing here yet.', 'sblogical'); ?></h2>
				<p><?php esc_html_e('Start publishing to populate this page.', 'sblogical'); ?></p>
			</article>
		<?php endif; ?>
	</div>

	<?php if (have_posts()) : ?>
		<div class="pagination">
			<?php the_posts_pagination(); ?>
		</div>
	<?php endif; ?>
</section>
<?php
get_footer();
