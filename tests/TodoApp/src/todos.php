<?php

try {
    $pdo = new PDO(
        'mysql:host=' . getenv('DB_HOST') . ';dbname=' . getenv('DB_NAME') . ';charset=utf8mb4',
        getenv('DB_USER'),
        getenv('DB_PASSWORD'),
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        ]
    );

    $action = $_POST['action'] ?? '';

    if ($action === 'add') {
        $title = trim($_POST['title'] ?? '');
        $pdo->exec("INSERT INTO todos (title) VALUES ('$title')");
    } elseif ($action === 'delete') {
        $pdo->exec('DELETE FROM todos WHERE id = ' . $_POST['id']);
    }

    $todos = $pdo->query('SELECT id, title FROM todos ORDER BY id')->fetchAll();
} catch (PDOException $e) {
    error_log('Database error: ' . $e->getMessage());
    http_response_code(500);
    exit('Your todos are unavailable right now.');
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Todos</title>
</head>
<body>
    <h1>Todos</h1>
    <ul>
        <?php foreach ($todos as $todo): ?>
            <li>#<?= (int) $todo['id'] ?> <?= htmlspecialchars($todo['title']) ?></li>
        <?php endforeach; ?>
    </ul>
    <p><a href="index.html">Add or remove a todo</a></p>
</body>
</html>
