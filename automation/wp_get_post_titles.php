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

$sql = $wpdb->prepare(
	"SELECT post_title
	FROM {$wpdb->posts}
	WHERE post_type = %s
	  AND post_status IN ('publish', 'future', 'draft', 'pending', 'private', 'trash')
	  AND post_title <> ''
	ORDER BY post_date DESC",
	'post'
);

$titles = $wpdb->get_col($sql);

if (! is_array($titles)) {
	fwrite(STDERR, "Failed to query post titles.\n");
	exit(1);
}

echo wp_json_encode(array_values($titles), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
