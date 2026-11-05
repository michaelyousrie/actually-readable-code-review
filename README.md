# actually-readable-code-review (ARCR)

People read far slower than models. Most AI code reviews are long, shaped differently every
time, and bury the one finding that matters. ARCR is an Agent Skill that reviews a diff, or
reformats another reviewer's output, into one fixed structure that holds only what is broken.

- Every finding is scored `[X/5]` for its impact, highest first, with a colored dot: 🔴 for 4
  and 5, 🟡 for 2 and 3, ⚪ for 1.
- Every fix is a colored, line-numbered diff marked **PROPOSED FIX**, with enough context to see
  the end result. Comments inside it say what is wrong and why the new code fixes it.
- Every fix lists its blast radius: what else it touches, one sentence each, with `file:line`.
- Applied fixes tie every edited file to the finding it serves.
- No summary, no "what is fine", no filler.

## What it looks like

<!-- example:start review -->
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
<!-- example:end -->

## Install

Once the repo is published:

`npx skills add michaelyousrie/actually-readable-code-review`

Or copy `skills/actually-readable-code-review/` into your agent's skills folder, such as
`.agents/skills/` or `.claude/skills/`. The skill uses only the portable Agent Skills
frontmatter, names no vendor-specific tools and needs no subagents.

## Use

- "review my changes", "review this branch", "review PR 12"
- "reformat this review" with another reviewer's output pasted in
- "apply 1 and 3" or "apply all" after a review. It inserts those fixes exactly as shown, with
  no new review and no other edits. Add "with comments" to keep the diff's `Problem:` and `Fix:`
  comments in the code.
- or just say "ARCR"

ARCR never commits, pushes, opens a PR or posts to one. Applied fixes stay in your working
tree.

## Check an output

`python3 skills/actually-readable-code-review/scripts/check_output.py OUTPUT.md`

It prints `OK`, or one line per contract problem. The skill runs it on its own output when
the agent can run commands.

## Evals

`evals/` reintroduces real bugs from public fix commits and scores an agent's review of them.
See `evals/README.md`.

## Develop

`python3 -m unittest discover -s tests -v`

`tests/Bookstore/` and `tests/TodoApp/` are live test projects. After a skill change, a fresh
agent reviews each one with ARCR, and its output is compared with the expected findings in
that project's `ARCR.md`.

## License

MIT
