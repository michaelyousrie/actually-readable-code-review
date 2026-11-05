## Applied 1 of 3 fixes
1 file edited · 1 skipped · 1 blocked · tests ran: 12 passed, 0 failed

---

### 1. 🔴 [4/5] Stacked coupons can push an order total below zero
**Edited:**
- `src/cart/applyDiscounts.ts`: applied as proposed.
**Still open:**
- `src/cart/summary.ts:40` still shows per-coupon savings from the original price.
- Orders already saved with a negative total are not repaired (`src/orders/OrderRepository.ts:88`).

---

### 2. 🟡 [3/5] Bulk sync can exceed the payment provider's rate limit and drop orders
**Blocked:** the provider publishes no per-minute limit; ask its support for the number.

---

### 3. ⚪ [1/5] New tool card has no icon
**Skipped:** `public/icons/export.svg` does not exist yet, and setting the path first would show a broken image (`src/ui/ToolGrid.vue:30`).
