<?php

declare(strict_types=1);

$view = $_GET['view'] ?? 'templates/home.php';
include $view;
