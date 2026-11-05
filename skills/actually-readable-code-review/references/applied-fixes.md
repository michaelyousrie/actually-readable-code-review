# Applied fixes

## When it runs

- Only when the developer asks, after a review. They can name findings ("apply 1 and 3") or
  ask for all of them.
- Apply from the review in this conversation. If it is no longer there, ask the developer to
  paste it. Never run the review again to recover it: a new run can find, word and number
  things differently.
- A PR that is not checked out locally cannot be applied. Say the branch must be checked out
  first. Never switch branches yourself.
- Never commit, push, open a PR or post to one. Changes stay in the working tree.

## What applying does

- Insert each chosen fix exactly as shown: its `-` lines come out and its `+` lines go in.
  Nothing else changes. No new review, no improvements, no extra edits, and none of the blast
  radius items.
- Leave out the diff's `Problem:` and `Fix:` comment lines. Keep them, as real comments above
  the lines they explain, only when the developer asks, for example "apply 1 with comments".
  Kept comments go in without the 🟥 and 🟩 squares.
- A diff's line numbers are where its lines sit in the file the review read. A fix applied
  earlier in the same run moves every line below it, so fix 3 can start at line 24 after
  fix 1 added three lines above its line 21. That shift is not drift. Find each fix by its `-`
  and context lines, not by its line numbers alone.
- If a file no longer matches the diff's `-` and context lines, do not adapt the fix. Skip it
  and say which line changed.
- A fix labeled `(on top of fix 1)` goes in only after fix 1. Asked for alone, it is skipped
  with that reason.
- A fix with an unmet **Needs:** is skipped when applying it early would make things worse,
  such as pointing at an image that does not exist yet.

## Tests

Run the tests that cover the edited files when the repo documents how (`AGENTS.md`,
`README`, package scripts). Report the result as it happened. Otherwise say why they were not
run.

## Output

The fence below only marks the template. Your output is never wrapped in a code fence.

```text
⚠️ <override line, same rule as the review>
## Applied <A> of <M> fixes
<F> files edited · <S> skipped · <B> blocked · tests ran: <X> passed, <Y> failed

---

### 1. <dot> [X/5] <same title as the review>
**Edited:**
- `<path>`: applied as proposed.
**Still open:**
- <one sentence with `file:line`>

---

### 2. <dot> [X/5] <title>
**Skipped:** <why>
```

- `<M>` is the number of findings in the review. Every one of them appears, with the review's
  number, title and order.
- Each finding has exactly one of **Edited:**, **Skipped:** or **Blocked:**.
- A finding the developer did not ask for reads `**Skipped:** not requested`.
- **Edited:** lists every file the fix's diff touches. Add "with comments" after "applied as
  proposed" when the developer kept them.
- `<F>` counts the distinct paths under every **Edited:**. Use "1 file" for one, and "fix"
  when `<M>` is 1.
- The tests part reads `tests ran: <X> passed, <Y> failed` or `tests not run: <why>`.
- No diffs. The review already shows the code that went in.
- **Still open** lists the blast radius items that still need work, such as a caller to
  update or a test to write, each with a `file:line` reference. It follows **Edited:** only.
- Separators, blank lines, labels and dashes follow `output-contract.md`.

## Example

This applies the three-finding example in `output-contract.md` after "apply 1".

<!-- example:start applied -->
## Applied 1 of 3 fixes
1 file edited · 2 skipped · 0 blocked · tests ran: 12 passed, 0 failed

---

### 1. 🔴 [4/5] Stacked coupons can push an order total below zero
**Edited:**
- `src/cart/applyDiscounts.ts`: applied as proposed.
**Still open:**
- `src/cart/summary.ts:40` still shows per-coupon savings from the original price.
- `tests/cart/applyDiscounts.test.ts:12` covers one coupon only; stacking needs its own case.

---

### 2. 🟡 [3/5] Bulk sync can exceed the payment provider's rate limit and drop orders
**Skipped:** not requested

---

### 3. ⚪ [1/5] New tool card has no icon
**Skipped:** not requested
<!-- example:end -->
