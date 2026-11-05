<?php

declare(strict_types=1);

require __DIR__ . '/ApiClient.php';
$config = require __DIR__ . '/config.php';

$client = new ApiClient($config['api_base'], $config['api_token']);

$url = $_POST['url'] ?? '';
$body = $client->fetch($url);

header('Content-Type: text/plain');
echo $body;
