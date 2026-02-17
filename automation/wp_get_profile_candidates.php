<?php
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
	fwrite(STDERR, "This script must run in CLI mode.\n");
	exit(1);
}

$root = dirname(__DIR__);
$wpLoad = $root . DIRECTORY_SEPARATOR . 'wp-load.php';

if (! file_exists($wpLoad)) {
	fwrite(STDERR, "wp-load.php not found at {$wpLoad}\n");
	exit(1);
}

require_once $wpLoad;

global $wpdb;

$candidates = $wpdb->get_col(
	"SELECT DISTINCT pm.meta_value
	FROM {$wpdb->postmeta} pm
	INNER JOIN {$wpdb->posts} p ON p.ID = pm.post_id
	WHERE pm.meta_key = '_sblogical_candidate_name'
	  AND pm.meta_value <> ''
	  AND p.post_type = 'post'
	  AND p.post_status IN ('publish', 'future', 'draft', 'pending', 'private', 'trash')
	ORDER BY pm.meta_value ASC"
);

if (! is_array($candidates)) {
	fwrite(STDERR, "Failed to query candidate names.\n");
	exit(1);
}

echo wp_json_encode(array_values($candidates), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
