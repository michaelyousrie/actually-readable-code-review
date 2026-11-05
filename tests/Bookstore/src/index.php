<?php

declare(strict_types=1);

$host = '127.0.0.1';
$database = 'bookshop';
$username = 'bookshop_app';
$password = 'Tr0ub4dor&3-fake';

try {
    $pdo = new PDO(
        "mysql:host={$host};dbname={$database};charset=utf8mb4",
        $username,
        $password,
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]
    );

    $books = $pdo->query('SELECT title, author FROM books ORDER BY title LIMIT 20')->fetchAll();
} catch (PDOException $e) {
    error_log('Database error: ' . $e->getMessage());
    http_response_code(500);
    exit('The bookshop is unavailable right now.');
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Bookshop</title>
    <!-- db debug: <?= $username ?> / <?= $password ?> -->
</head>
<body>
    <h1>Books</h1>
    <ul>
        <?php foreach ($books as $book): ?>
            <li><?= htmlspecialchars($book['title']) ?> by <?= htmlspecialchars($book['author']) ?></li>
        <?php endforeach; ?>
    </ul>
</body>
</html>
