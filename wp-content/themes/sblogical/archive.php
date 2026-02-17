<?php
/**
 * Archive template.
 *
 * @package sblogical
 */

get_header();
?>
<header class="archive-header">
	<h1 class="section__title"><?php the_archive_title(); ?></h1>
	<?php if (get_the_archive_description()) : ?>
		<p class="section__intro"><?php echo wp_kses_post(get_the_archive_description()); ?></p>
	<?php endif; ?>
</header>

<div class="post-list">
	<?php if (have_posts()) : ?>
		<?php while (have_posts()) : the_post(); ?>
			<article <?php post_class('post-card'); ?>>
				<p class="post-meta"><?php echo esc_html(get_the_date()); ?></p>
				<h2><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h2>
				<?php the_excerpt(); ?>
			</article>
		<?php endwhile; ?>
	<?php else : ?>
		<article class="post-card">
			<h2><?php esc_html_e('No matching posts found.', 'sblogical'); ?></h2>
		</article>
	<?php endif; ?>
</div>

<?php if (have_posts()) : ?>
	<div class="pagination">
		<?php the_posts_pagination(); ?>
	</div>
<?php endif; ?>
<?php
get_footer();
