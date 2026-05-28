<?php
/**
 * Phase 3 reject/quarantine webhook. scripts/scanner/reject.py POSTs
 * an HMAC-SHA256-signed verdict here when a scan fails; we write a
 * REJECTED.json next to the quarantined sample so staff/tooling can
 * list rejections. The raw upload stays in ~/quarantine/ as forensic
 * evidence.
 *
 * Deploy to: ~/public_html/_internal/livery-flag.php on vrs.com.
 *
 * Auth: X-VRS-Signature = hex(HMAC-SHA256(key, raw_body)), where key is
 * the shared secret in ~/.vrs-pipeline-secrets/webhook-key (must equal
 * the VRS_WEBHOOK_KEY repo secret reject.py signs with). A replay window
 * bounds stale/replayed posts.
 *
 * Payload (compact JSON, signed as exact bytes):
 *   {"sha256":"<hex>","verdict":"REJECT","reasons":[...],"ts":<unix>}
 */

declare(strict_types=1);

ini_set('display_errors', '0');
ini_set('log_errors', '1');
ini_set('error_log', '/home/customdc/cron-state/php-internal-error.log');

const QUARANTINE = '/home/customdc/quarantine';
const KEY_FILE   = '/home/customdc/.vrs-pipeline-secrets/webhook-key';
const MAX_SKEW   = 300; // seconds; reject.py stamps ts at send time

function deny(int $code, string $msg): void {
    http_response_code($code);
    header('Content-Type: text/plain');
    echo $msg . "\n";
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    deny(405, 'POST only');
}
if (!is_file(KEY_FILE)) {
    deny(500, 'server not configured');
}
$key = trim((string)file_get_contents(KEY_FILE));
if ($key === '') {
    deny(500, 'server not configured');
}

// HMAC over the EXACT received bytes -- not a re-serialized payload.
$body = (string)file_get_contents('php://input');
$sent = $_SERVER['HTTP_X_VRS_SIGNATURE'] ?? '';
$expected = hash_hmac('sha256', $body, $key);
if (!is_string($sent) || !hash_equals($expected, $sent)) {
    deny(401, 'bad signature');
}

$payload = json_decode($body, true);
if (!is_array($payload) || !isset($payload['sha256'], $payload['ts'], $payload['verdict'])) {
    deny(400, 'bad payload');
}

// Replay window.
if (abs(time() - (int)$payload['ts']) > MAX_SKEW) {
    deny(401, 'stale timestamp');
}

$sha = (string)$payload['sha256'];
if (!preg_match('/^[a-f0-9]{64}$/', $sha)) {
    deny(400, 'bad sha');
}

$qdir = QUARANTINE . '/' . $sha;
if (!is_dir($qdir)) {
    // Normally the cron created this when it quarantined the upload.
    // Create it anyway so a rejection is never silently dropped.
    @mkdir($qdir, 0700, true);
}

$record = [
    'sha256'      => $sha,
    'verdict'     => $payload['verdict'],
    'reasons'     => $payload['reasons'] ?? [],
    'sent_ts'     => (int)$payload['ts'],
    'received_at' => gmdate('Y-m-d\TH:i:s\Z'),
];
$ok = file_put_contents(
    $qdir . '/REJECTED.json',
    json_encode($record, JSON_PRETTY_PRINT) . "\n",
    LOCK_EX
);
if ($ok === false) {
    deny(500, 'write failed');
}

http_response_code(204);
