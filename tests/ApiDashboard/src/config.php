<?php

declare(strict_types=1);

return [
    'api_base' => getenv('STATUS_API_BASE') ?: 'https://status.example.com/api',
    'api_token' => getenv('STATUS_API_TOKEN'),
];
