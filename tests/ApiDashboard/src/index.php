<?php

declare(strict_types=1);

require __DIR__ . '/ApiClient.php';
$config = require __DIR__ . '/config.php';

$client = new ApiClient($config['api_base'], $config['api_token']);
$statuses = [];
foreach (['web', 'database', 'queue'] as $service) {
    $statuses[$service] = $client->status($service)['state'] ?? 'unknown';
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Integration dashboard</title>
</head>
<body>
    <h1>Service status</h1>
    <ul>
        <?php foreach ($statuses as $service => $state): ?>
            <li><?= htmlspecialchars($service) ?>: <?= htmlspecialchars($state) ?></li>
        <?php endforeach; ?>
    </ul>

    <h2>Import a feed</h2>
    <form action="fetch.php" method="post">
        <input name="url" placeholder="https://feeds.example.com/latest.json" required>
        <button>Import</button>
    </form>

    <h2>Open a report</h2>
    <form action="view.php" method="get">
        <input name="view" placeholder="templates/home.php" required>
        <button>Open</button>
    </form>
</body>
</html>
