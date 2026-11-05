<?php

use App\Http\Controllers\CheckoutController;
use Illuminate\Support\Facades\Route;

Route::post('/checkout/coupon', [CheckoutController::class, 'applyCoupon']);
