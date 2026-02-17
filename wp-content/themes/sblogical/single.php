<?php
/**
 * Single post template.
 *
 * @package sblogical
 */

get_header();
?>
<?php if (have_posts()) : ?>
	<?php while (have_posts()) : the_post(); ?>
		<article <?php post_class('entry'); ?>>
			<p class="post-meta">
				<?php echo esc_html(get_the_date()); ?> · <?php the_author(); ?>
			</p>
			<h1><?php the_title(); ?></h1>
			<div class="entry-content">
				<?php the_content(); ?>
			</div>
		</article>
	<?php endwhile; ?>

	<div class="section">
		<?php the_post_navigation(); ?>
	</div>
<?php endif; ?>
<?php
get_footer();
