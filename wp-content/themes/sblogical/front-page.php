<?php
/**
 * Front page template.
 *
 * @package sblogical
 */

get_header();
?>
<section class="hero">
	<p class="hero__kicker"><?php esc_html_e('Digital Strategy + Marketing Execution', 'sblogical'); ?></p>
	<h1 class="hero__title"><?php bloginfo('name'); ?></h1>
	<p class="hero__lead">
		<?php
		$description = get_bloginfo('description');
		echo esc_html($description ? $description : __('Sblogical helps brands publish smarter content, grow authority, and turn traffic into outcomes.', 'sblogical'));
		?>
	</p>
	<div class="hero__actions">
		<a class="button button--primary" href="<?php echo esc_url(home_url('/blog')); ?>">
			<?php esc_html_e('Read the Blog', 'sblogical'); ?>
		</a>
		<a class="button button--ghost" href="<?php echo esc_url(home_url('/contact')); ?>">
			<?php esc_html_e('Book a Discovery Call', 'sblogical'); ?>
		</a>
	</div>
</section>

<section class="section">
	<h2 class="section__title"><?php esc_html_e('What Sblogical Focuses On', 'sblogical'); ?></h2>
	<p class="section__intro"><?php esc_html_e('A practical stack for sustainable growth.', 'sblogical'); ?></p>
	<div class="grid">
		<article class="card">
			<h3><?php esc_html_e('Content Systems', 'sblogical'); ?></h3>
			<p><?php esc_html_e('From keyword research to editorial ops, build repeatable publishing systems that compound over time.', 'sblogical'); ?></p>
		</article>
		<article class="card">
			<h3><?php esc_html_e('SEO Foundation', 'sblogical'); ?></h3>
			<p><?php esc_html_e('Technical cleanup, on-page alignment, and intent-driven architecture designed to earn consistent organic traffic.', 'sblogical'); ?></p>
		</article>
		<article class="card">
			<h3><?php esc_html_e('Performance Marketing', 'sblogical'); ?></h3>
			<p><?php esc_html_e('Campaign messaging and conversion-focused landing pages connected directly to business KPIs.', 'sblogical'); ?></p>
		</article>
	</div>
</section>

<section class="section">
	<h2 class="section__title"><?php esc_html_e('Latest Insights', 'sblogical'); ?></h2>
	<p class="section__intro"><?php esc_html_e('Recent posts from the Sblogical journal.', 'sblogical'); ?></p>
	<div class="post-list">
		<?php
		$sblogical_latest = new WP_Query(
			array(
				'post_type'           => 'post',
				'posts_per_page'      => 3,
				'ignore_sticky_posts' => true,
			)
		);

		if ($sblogical_latest->have_posts()) :
			while ($sblogical_latest->have_posts()) :
				$sblogical_latest->the_post();
				?>
				<article <?php post_class('post-card'); ?>>
					<p class="post-meta">
						<?php echo esc_html(get_the_date()); ?>
					</p>
					<h3><a href="<?php the_permalink(); ?>"><?php the_title(); ?></a></h3>
					<?php the_excerpt(); ?>
				</article>
				<?php
			endwhile;
			wp_reset_postdata();
		else :
			?>
			<article class="post-card">
				<h3><?php esc_html_e('No posts published yet.', 'sblogical'); ?></h3>
				<p><?php esc_html_e('Create your first post and it will appear here automatically.', 'sblogical'); ?></p>
			</article>
		<?php endif; ?>
	</div>
</section>
<?php
get_footer();
