## Fix before merge
3 findings · top impact 4/5 · 5 files

---

### 1. 🔴 [4/5] Stacked coupons can push an order total below zero
`src/cart/applyDiscounts.ts:18`
**PROPOSED FIX:**
```diff
@@ src/cart/applyDiscounts.ts:17 @@
 17 |   for (const coupon of coupons) {
-   |     // 🟥 Problem: each coupon comes off the original price, so a 60% and a 50% coupon make the total negative.
-18 |     total -= price * coupon.percent / 100;
+   |     // 🟩 Fix: take each coupon off the running total, which can never drop below zero.
+18 |     total -= total * coupon.percent / 100;
 19 |   }
 20 |   return total;
```
**Blast radius:**
- `src/cart/summary.ts:40` shows per-coupon savings from the original price and must switch to the running total.
- `tests/cart/applyDiscounts.test.ts:12` covers one coupon only; stacking needs its own case.

---

### 2. 🟡 [3/5] Bulk sync can exceed the payment provider's rate limit and drop orders
`src/sync/pushOrders.ts:42`
**Impact:** all pending orders are sent in one burst, and the provider rejects requests over its per-minute limit without a retry.
**Blocked:** the provider names a per-minute limit but publishes no number, so no batch size can be set yet. Ask the provider's support for the limit.

---

### 3. ⚪ [1/5] New tool card has no icon
`src/ui/ToolCard.vue:12`
**Needs:** the icon file at `public/icons/export.svg`.
**PROPOSED FIX:**
```diff
@@ src/ui/ToolCard.vue:10 @@
 10 |   export: {
 11 |     label: 'Export',
+   |     // 🟩 Fix: the card showed an empty square where every other card shows its icon.
+12 |     icon: '/icons/export.svg',
 13 |   },
```
**Blast radius:**
- `src/ui/ToolGrid.vue:30` renders the icon in place of the empty square.
