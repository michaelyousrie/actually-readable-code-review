<?php

namespace App\Services;

interface PaymentGateway
{
    /** Capture a previously authorized payment. */
    public function capture(string $paymentIntent): void;
}
