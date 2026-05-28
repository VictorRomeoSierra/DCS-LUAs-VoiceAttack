<?php
/**
 * Phase 3 signed-URL endpoint. Streams a quarantined upload to the
 * GitHub Actions runner given a valid, unexpired token minted by
 * livery-pipeline-cron.py. Raw uploads never live in the web root or
 * the git repo; this is the only way the runner fetches them.
 *
 * Deploy to: ~/public_html/_internal/livery-blob.php on vrs.com.
 *
 * URL: https://victorromeosierra.com/_internal/livery-blob.php?token=<64hex>
 */

declare(strict_types=1);

// Never leak filesystem paths via default A2 PHP error pages.
ini_set('display_errors', '0');
ini_set('log_errors', '1');
ini_set('error_log', '/home/customdc/cron-state/php-internal-error.log');
set_time_limit(0); // large blobs (up to ~300 MB) over a slow link

const QUARANTINE  = '/home/customdc/quarantine';
const SIGNED_URLS = QUARANTINE . '/_signed-urls';

function deny(int $code, string $msg): void {
    http_response_code($code);
    header('Content-Type: text/plain');
    echo $msg . "\n";
    exit;
}

$token = $_GET['token'] ?? '';
// Token is 64 hex chars (secrets.token_hex(32)). Validate the FORMAT
// before using it in any path -- ?token=../../x would traverse otherwise.
if (!is_string($token) || !preg_match('/^[a-f0-9]{64}$/', $token)) {
    deny(400, 'bad token');
}

$tokenFile = SIGNED_URLS . '/' . $token . '.json';
if (!is_file($tokenFile)) {
    deny(404, 'unknown token');
}

$meta = json_decode((string)file_get_contents($tokenFile), true);
if (!is_array($meta) || !isset($meta['sha256'], $meta['expires'])) {
    deny(404, 'bad token record');
}
if ((int)$meta['expires'] < time()) {
    deny(403, 'token expired');
}

$sha = (string)$meta['sha256'];
// Validate the sha256 BEFORE building the quarantine path.
if (!preg_match('/^[a-f0-9]{64}$/', $sha)) {
    deny(500, 'bad sha in token');
}

$blob = QUARANTINE . '/' . $sha . '/original.zip';
if (!is_file($blob)) {
    deny(404, 'blob missing');
}

// Stream in chunks -- readfile() does not buffer the whole file in
// memory, but kill any output buffering first to be sure PHP-FPM
// doesn't accumulate a 280 MB blob and OOM on shared hosting.
while (ob_get_level() > 0) {
    ob_end_clean();
}
header('Content-Type: application/zip');
header('Content-Length: ' . filesize($blob));
header('Content-Disposition: attachment; filename="livery.zip"');
header('X-Content-Type-Options: nosniff');
readfile($blob);
exit;
