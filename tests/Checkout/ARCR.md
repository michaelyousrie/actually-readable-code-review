# Checkout

A Laravel checkout change, reviewed as a diff rather than a set of new files. The committed
baseline in `src/` is a correct single-coupon endpoint. `change.diff` rewrites it to stack
coupons and adds a bulk payment-capture job, planting one bug of every severity. It is the
showcase fixture: one review that uses all three score dots, a Blocked finding and an
overlapping fix at once.

Paths in the output are relative to `src/`.

## How to run

1. Copy `src/` into an empty folder and run `git init`, `git add -A`,
   `git commit -m baseline` there.
2. Apply the change and leave it uncommitted: `git apply /path/to/change.diff`. The working
   tree now has two modified files and a new untracked job.
3. Ask a fresh agent to review the uncommitted changes with ARCR.
4. Never tell the reviewer the expected findings. Compare its output with the table below.

## Expected

| Change under review | Expected finding |
|---|---|
| the order is loaded with `Order::findOrFail($request->input('order_id'))`, dropping the baseline's `$request->user()->orders()` scope | critical: any authenticated caller can mutate another user's order |
| each coupon subtracts a percentage of the original `subtotal`, not the running total | critical: stacked coupons drive the total below zero; fix subtracts from the running total |
| the loop dropped the baseline's `isRedeemable()` guard | expired or inactive coupons still discount; the fix adds the guard in the loop, on top of the running-total fix |
| `CapturePendingPayments` captures every pending order in one loop with no pacing | Blocked: the safe batch size needs the provider's per-minute limit, which is on the provider dashboard and not in the repo |
| a leftover `\Log::info('applyCoupons', $request->all())` line | low: debug instrumentation that also logs the full request body |

No other finding is expected to be critical. Anything else the reviewer reports is unplanted
and is judged on its own.

## Latest results: 2026-11-05

| Check | Result |
|---|---|
| All planted findings | PASS: all five found, checker OK |
| Blocked | PASS: the capture job is marked Blocked, needing the provider's per-minute limit |
| Overlap | PASS: the running-total fix is written on top of the redeemable-guard fix, numbered against the file after it |
| Scores | the IDOR came back 5/5 and the coupon math 4/5 (the reviewer's call); the debug log came back 2/5, not 1/5, because it logs the whole request body, so this run shows no white dot |
| Math | verified in Python: 60% and 50% off the original subtotal gives a total of -10; the running-total fix never goes below zero |

### Output

## Fix before merge
5 findings · top impact 5/5 · 3 files

---

### 1. 🔴 [5/5] Any caller can rewrite another user's order total
`app/Http/Controllers/CheckoutController.php:16`
**PROPOSED FIX:**
```diff
@@ app/Http/Controllers/CheckoutController.php:15 @@
 15 |
-   |         // 🟥 Problem: the ownership scope that HEAD had was dropped, so any caller can pass another user's order id and this endpoint rewrites that order's total.
-16 |         $order = Order::findOrFail($request->input('order_id'));
+   |         // 🟩 Fix: look the order up through the authenticated user's own orders, exactly as the code did before this change.
+16 |         $order = $request->user()->orders()->findOrFail($request->input('order_id'));
 17 |
 18 |         $order->total = $order->subtotal;
```
**Blast radius:**
- `routes/api.php:6` carries no auth middleware, so `$request->user()` is only populated if the api group adds one; I could not verify any is configured in this repo, and if the route is public the fix also needs `->middleware('auth:sanctum')` here.
- `app/Http/Controllers/CheckoutController.php:6` the `use App\Models\Order;` line this diff added is left unused once the direct `Order::findOrFail` call goes away.

---

### 2. 🔴 [4/5] Expired or inactive coupons are still accepted
`app/Http/Controllers/CheckoutController.php:20`
**PROPOSED FIX:**
```diff
@@ app/Http/Controllers/CheckoutController.php:20 @@
 20 |             $coupon = Coupon::where('code', $code)->first();
 21 |             if (! $coupon) {
 22 |                 continue;
 23 |             }
+   |             // 🟩 Fix: skip any coupon that is not redeemable; HEAD returned a 422 for these and this change dropped that guard, so expired or disabled codes now discount the order.
+24 |             if (! $coupon->isRedeemable()) {
+25 |                 continue;
+26 |             }
 27 |             $order->total -= $order->subtotal * $coupon->percent / 100;
 28 |         }
```
**Blast radius:**
- `app/Http/Controllers/CheckoutController.php:29` the response returns only the recomputed total, so a rejected code gives the caller no signal; decide whether a non-redeemable code should error rather than be skipped silently.
- `app/Models/Coupon.php:16` `isRedeemable()` treats a null `expires_at` as not redeemable, so any coupon with no expiry date will now be skipped; confirm that matches intent.
- `app/Http/Controllers/CheckoutController.php:19` no test covers an expired or inactive code; add one, since the repo has no test suite yet.

---

### 3. 🔴 [4/5] Stacked coupons drive the order total below zero
`app/Http/Controllers/CheckoutController.php:24`
**PROPOSED FIX (on top of fix 2):**
```diff
@@ app/Http/Controllers/CheckoutController.php:23 @@
 23 |             }
 24 |             if (! $coupon->isRedeemable()) {
 25 |                 continue;
 26 |             }
-   |             // 🟥 Problem: each coupon comes off the full subtotal, so codes summing over 100 percent make the total negative, and a code sent twice is applied twice.
-27 |             $order->total -= $order->subtotal * $coupon->percent / 100;
+   |             // 🟩 Fix: take each coupon off the running total, which falls toward zero and never past it.
+27 |             $order->total -= $order->total * $coupon->percent / 100;
 28 |         }
```
**Blast radius:**
- `app/Http/Controllers/CheckoutController.php:18` compounding changes the math: two 50 percent codes now leave 25 percent of subtotal instead of reaching zero, which differs from the additive intent of the original line.
- `app/Http/Controllers/CheckoutController.php:19` the same code can appear twice in `codes` and is applied twice; dedupe the array here if a code should count once.
- `app/Http/Controllers/CheckoutController.php:12` add a test that stacks codes past 100 percent and asserts the total never drops below zero; the repo has no tests.

---

### 4. 🔴 [4/5] Payment capture job can exceed the gateway rate limit and drop captures
`app/Jobs/CapturePendingPayments.php:24`
**Impact:** the job loads every `pending_capture` order and calls `capture()` in a tight loop with no pacing, so a backlog above the merchant's per-minute limit makes the gateway reject the overflow and those authorized payments are never captured; loading all pending orders at once can also exhaust memory on a large backlog. Nothing in the repo dispatches this job yet, so the loss lands once it is scheduled.
**Blocked:** the safe batch size or delay depends on each merchant's per-minute capture limit, which the code comment says lives on the provider dashboard and is not in this codebase. Ask the payments provider or read each merchant's plan for that limit before setting a throttle.

---

### 5. 🟡 [2/5] Leftover debug log writes the full request body on every call
`app/Http/Controllers/CheckoutController.php:14`
**PROPOSED FIX:**
```diff
@@ app/Http/Controllers/CheckoutController.php:13 @@
 13 |     {
-   |         // 🟥 Problem: this debug log writes the full request body to the log on every call and is leftover instrumentation that should not ship.
-14 |         \Log::info('applyCoupons', $request->all());
-15 |
 14 |         $order = Order::findOrFail($request->input('order_id'));
```
**Blast radius:**
- `app/Http/Controllers/CheckoutController.php:12` this is the method's only log line; if call auditing is wanted, add structured logging that omits the raw request body rather than this inline call.
