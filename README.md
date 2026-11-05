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
2 findings · top impact 4/5 · 3 files

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
