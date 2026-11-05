<?php

declare(strict_types=1);

final class ApiClient
{
    public function __construct(
        private string $base,
        private ?string $token,
    ) {
    }

    /** Read one service's status from the monitoring API. */
    public function status(string $service): array
    {
        $ch = curl_init($this->base . '/status/' . rawurlencode($service));
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER => ['Authorization: Bearer ' . (string) $this->token],
            CURLOPT_TIMEOUT => 5,
        ]);
        $body = curl_exec($ch);
        curl_close($ch);

        return json_decode((string) ($body ?: '{}'), true) ?? [];
    }

    /** Import a feed the operator pastes into the dashboard. */
    public function fetch(string $url): string
    {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_FOLLOWLOCATION => true,
        ]);
        $body = curl_exec($ch);
        curl_close($ch);

        return (string) $body;
    }
}
