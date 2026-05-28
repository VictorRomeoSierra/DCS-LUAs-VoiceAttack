<?php
/**
 * Phase 3 DB helper for livery-pipeline-cron.py.
 *
 * Keeps ProjectSend's MySQL credentials inside PHP (they live as
 * constants in ProjectSend's sys.config.php) so the Python cron never
 * needs a MySQL driver or the raw password. Emits JSON on stdout.
 *
 * Deploy to: ~/bin/livery-db-query.php on vrs.com (NOT web-accessible).
 *
 * Modes:
 *   php livery-db-query.php seed
 *     -> {"ts":"YYYY-MM-DD HH:MM:SS","id":N}  current max watermark
 *        (used to seed ~/cron-state on first run, no dispatch)
 *
 *   php livery-db-query.php query "<ts>" <id>
 *     -> [ {row}, ... ]  uploads strictly after (ts,id), local storage
 *        only, oldest first, joined to tbl_users for uploader email.
 *
 * Exit non-zero + JSON {"error":...} on failure so the cron can detect
 * and skip the tick rather than advancing the watermark.
 */

declare(strict_types=1);

$CONFIG = '/home/customdc/public_html/upload/includes/sys.config.php';

function fail(string $msg): void {
    fwrite(STDERR, $msg . "\n");
    echo json_encode(["error" => $msg]) . "\n";
    exit(1);
}

if (!is_file($CONFIG)) {
    fail("config not found: $CONFIG");
}
require $CONFIG;

$prefix = defined('TABLES_PREFIX') ? TABLES_PREFIX : 'tbl_';
$db = @new mysqli(DB_HOST, DB_USER, DB_PASSWORD, DB_NAME);
if ($db->connect_errno) {
    fail("db connect failed: " . $db->connect_error);
}
$db->set_charset('utf8mb4');

$mode = $argv[1] ?? '';

if ($mode === 'seed') {
    $res = $db->query(
        "SELECT DATE_FORMAT(MAX(timestamp), '%Y-%m-%d %H:%i:%s') AS ts,
                COALESCE(MAX(id), 0) AS id
         FROM {$prefix}files"
    );
    if (!$res) { fail("seed query failed: " . $db->error); }
    $row = $res->fetch_assoc();
    echo json_encode([
        "ts" => $row['ts'] ?? '1970-01-01 00:00:00',
        "id" => (int)($row['id'] ?? 0),
    ]) . "\n";
    exit(0);
}

if ($mode === 'query') {
    $ts = $argv[2] ?? '1970-01-01 00:00:00';
    $id = (int)($argv[3] ?? 0);

    $sql =
        "SELECT f.id, f.user_id, f.url, f.original_url, f.filename,
                f.size, f.storage_type,
                f.disk_folder_year, f.disk_folder_month,
                DATE_FORMAT(f.timestamp, '%Y-%m-%d %H:%i:%s') AS ts,
                u.email AS uploader_email, u.user AS uploader_user
         FROM {$prefix}files f
         LEFT JOIN {$prefix}users u ON u.id = f.user_id
         WHERE f.storage_type = 'local'
           AND ( f.timestamp > ? OR (f.timestamp = ? AND f.id > ?) )
         ORDER BY f.timestamp ASC, f.id ASC
         LIMIT 50";
    $stmt = $db->prepare($sql);
    if (!$stmt) { fail("prepare failed: " . $db->error); }
    $stmt->bind_param('ssi', $ts, $ts, $id);
    if (!$stmt->execute()) { fail("execute failed: " . $stmt->error); }
    $res = $stmt->get_result();

    $rows = [];
    while ($r = $res->fetch_assoc()) {
        $rows[] = [
            "id"                => (int)$r['id'],
            "user_id"           => (int)$r['user_id'],
            "url"               => $r['url'],
            "original_url"      => $r['original_url'],
            "filename"          => $r['filename'],
            "size"              => (int)$r['size'],
            "disk_folder_year"  => $r['disk_folder_year'] !== null ? (int)$r['disk_folder_year'] : null,
            "disk_folder_month" => $r['disk_folder_month'] !== null ? (int)$r['disk_folder_month'] : null,
            "ts"                => $r['ts'],
            "uploader_email"    => $r['uploader_email'],
            "uploader_user"     => $r['uploader_user'],
        ];
    }
    echo json_encode($rows) . "\n";
    exit(0);
}

fail("unknown mode: '$mode' (expected 'seed' or 'query')");
