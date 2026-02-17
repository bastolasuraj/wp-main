<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "This script must run in CLI mode.\n");
	exit(1);
}

$payloadRaw = stream_get_contents(STDIN);
if (! is_string($payloadRaw) || trim($payloadRaw) === '') {
	fwrite(STDERR, "Missing JSON payload on stdin.\n");
	exit(1);
}

$payload = json_decode($payloadRaw, true);
if (! is_array($payload)) {
	fwrite(STDERR, "Invalid JSON payload.\n");
	exit(1);
}

$required = array(
	'title',
	'slug',
	'excerpt',
	'content_html',
	'post_status',
	'topic_keywords',
	'candidate_profile',
	'seo',
	'sources',
	'category_name',
);
foreach ($required as $key) {
	if (! array_key_exists($key, $payload)) {
		fwrite(STDERR, "Missing required field: {$key}\n");
		exit(1);
	}
}

$root = dirname(__DIR__);
$wpLoad = $root . DIRECTORY_SEPARATOR . 'wp-load.php';
if (! file_exists($wpLoad)) {
	fwrite(STDERR, "wp-load.php not found at {$wpLoad}\n");
	exit(1);
}
require_once $wpLoad;

$title = sanitize_text_field((string) $payload['title']);
$slug = sanitize_title((string) $payload['slug']);
$excerpt = sanitize_textarea_field((string) $payload['excerpt']);
$content = wp_kses_post((string) $payload['content_html']);
$postStatus = sanitize_key((string) $payload['post_status']);
$seo = is_array($payload['seo']) ? $payload['seo'] : array();
$focusKeyphrase = sanitize_text_field((string) ($seo['focus_keyphrase'] ?? ''));
$metaTitle = sanitize_text_field((string) ($seo['meta_title'] ?? ''));
$metaDescription = sanitize_textarea_field((string) ($seo['meta_description'] ?? ''));
$candidate = is_array($payload['candidate_profile']) ? $payload['candidate_profile'] : array();
$candidateName = sanitize_text_field((string) ($candidate['candidate_name'] ?? ''));
$electionName = sanitize_text_field((string) ($candidate['election_name'] ?? ''));
$electionDate = sanitize_text_field((string) ($candidate['election_date'] ?? ''));
$candidateParty = sanitize_text_field((string) ($candidate['party'] ?? ''));
$candidateConstituency = sanitize_text_field((string) ($candidate['constituency'] ?? ''));
$candidatePosition = sanitize_text_field((string) ($candidate['current_position'] ?? ''));
$candidateBio = sanitize_textarea_field((string) ($candidate['short_bio'] ?? ''));
$candidateProfileUrl = esc_url_raw((string) ($candidate['profile_source_url'] ?? ''));
$candidateImageUrl = esc_url_raw((string) ($candidate['profile_image_url'] ?? ''));
$candidateImageSourceUrl = esc_url_raw((string) ($candidate['profile_image_source_url'] ?? ''));
$candidateImageCredit = sanitize_text_field((string) ($candidate['profile_image_credit'] ?? ''));
$categoryName = sanitize_text_field((string) $payload['category_name']);
if ($categoryName === '') {
	$categoryName = 'Nepal Election 2026';
}

if (! in_array($postStatus, array('publish', 'draft', 'pending', 'future'), true)) {
	fwrite(STDERR, "Unsupported post_status: {$postStatus}\n");
	exit(1);
}

global $wpdb;

$existingTitleId = (int) $wpdb->get_var(
	$wpdb->prepare(
		"SELECT ID
		FROM {$wpdb->posts}
		WHERE post_type = 'post'
		  AND post_title = %s
		  AND post_status <> 'trash'
		ORDER BY ID DESC
		LIMIT 1",
		$title
	)
);
if ($existingTitleId > 0) {
	echo wp_json_encode(
		array(
			'status' => 'skipped',
			'reason' => 'duplicate_title',
			'post_id' => $existingTitleId,
			'post_url' => get_permalink($existingTitleId),
		),
		JSON_UNESCAPED_SLASHES
	);
	exit(0);
}

$existingSlugId = (int) $wpdb->get_var(
	$wpdb->prepare(
		"SELECT ID
		FROM {$wpdb->posts}
		WHERE post_type = 'post'
		  AND post_name = %s
		  AND post_status <> 'trash'
		ORDER BY ID DESC
		LIMIT 1",
		$slug
	)
);
if ($existingSlugId > 0) {
	echo wp_json_encode(
		array(
			'status' => 'skipped',
			'reason' => 'duplicate_slug',
			'post_id' => $existingSlugId,
			'post_url' => get_permalink($existingSlugId),
		),
		JSON_UNESCAPED_SLASHES
	);
	exit(0);
}

$categoryId = (int) get_cat_ID($categoryName);
if ($categoryId <= 0) {
	$inserted = wp_insert_term($categoryName, 'category');
	if (! is_wp_error($inserted) && isset($inserted['term_id'])) {
		$categoryId = (int) $inserted['term_id'];
	}
}

$postarr = array(
	'post_type'      => 'post',
	'post_status'    => $postStatus,
	'post_title'     => $title,
	'post_name'      => $slug,
	'post_excerpt'   => $excerpt,
	'post_content'   => $content,
	'post_category'  => $categoryId > 0 ? array($categoryId) : array(),
	'tags_input'     => array_slice(
		array_values(
			array_filter(
				array_map(
					static fn ($tag) => sanitize_text_field((string) $tag),
					is_array($payload['topic_keywords']) ? $payload['topic_keywords'] : array()
				)
			)
		),
		0,
		10
	),
	'meta_input'     => array(
		'_sblogical_autopost' => 1,
		'_sblogical_sources_json' => wp_json_encode($payload['sources'], JSON_UNESCAPED_SLASHES),
		'_sblogical_candidate_profile_json' => wp_json_encode($candidate, JSON_UNESCAPED_SLASHES),
		'_sblogical_candidate_name' => $candidateName,
		'_sblogical_election_name' => $electionName,
		'_sblogical_election_date' => $electionDate,
		'_sblogical_candidate_party' => $candidateParty,
		'_sblogical_candidate_constituency' => $candidateConstituency,
		'_sblogical_candidate_position' => $candidatePosition,
		'_sblogical_candidate_bio' => $candidateBio,
		'_sblogical_candidate_profile_source_url' => $candidateProfileUrl,
		'_sblogical_candidate_image_url' => $candidateImageUrl,
		'_sblogical_candidate_image_source_url' => $candidateImageSourceUrl,
		'_sblogical_candidate_image_credit' => $candidateImageCredit,
		'_sblogical_focus_keyphrase' => $focusKeyphrase,
		'_sblogical_meta_title' => $metaTitle,
		'_sblogical_meta_description' => $metaDescription,
		'_yoast_wpseo_focuskw' => $focusKeyphrase,
		'_yoast_wpseo_title' => $metaTitle,
		'_yoast_wpseo_metadesc' => $metaDescription,
		'rank_math_focus_keyword' => $focusKeyphrase,
		'rank_math_title' => $metaTitle,
		'rank_math_description' => $metaDescription,
	),
	'comment_status' => 'closed',
);

$postId = wp_insert_post($postarr, true, false);
if (is_wp_error($postId)) {
	fwrite(STDERR, "wp_insert_post failed: " . $postId->get_error_message() . "\n");
	exit(1);
}

echo wp_json_encode(
	array(
		'status' => 'created',
		'post_id' => $postId,
		'post_url' => get_permalink($postId),
	),
	JSON_UNESCAPED_SLASHES
);
