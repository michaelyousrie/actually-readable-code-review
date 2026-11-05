<?php

namespace App\Http\Controllers;

use App\Models\Coupon;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class CheckoutController extends Controller
{
    public function applyCoupon(Request $request): JsonResponse
    {
        $order = $request->user()->orders()->findOrFail($request->input('order_id'));

        $coupon = Coupon::where('code', $request->input('code'))->firstOrFail();
        abort_unless($coupon->isRedeemable(), 422, 'Coupon is not redeemable.');

        $order->total = $order->subtotal - ($order->subtotal * $coupon->percent / 100);
        $order->save();

        return response()->json(['total' => $order->total]);
    }
}
