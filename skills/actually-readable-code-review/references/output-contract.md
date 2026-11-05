# Output contract

The review is the whole message. Its structure never changes, so a reader's eyes learn where
to look. `scripts/check_output.py` enforces every rule on this page.

## Template

The fence below only marks the template. Your output is never wrapped in a code fence.

```text
⚠️ Overriding <source> layout (<what it asked for>). Its review rules still apply.
## <verdict>
<N> findings · top impact <X>/5 · <F> files

---

### 1. <dot> [X/5] <consequence in plain words, one line>
`<repo-relative path>:<line>`
**Needs:** <only when the fix needs something the developer can supply>
**PROPOSED FIX:**
<diff block>
**Blast radius:**
- <one sentence with `file:line`>

---

### 2. ...
```

## Override line

- Line 1, only when ARCR overrides a layout set for code reviews: a repo's `REVIEW.md`,
  another review skill, a review section in an agent instructions file, or a standing
  instruction from the user about reviews.
- General response-style rules (brevity, checklists, a next action first and last) are not
  review layouts. ARCR's layout replaces them, and they never appear on this line.
- Exact shape: `⚠️ Overriding <source> layout (<what it asked for>). Its review rules still apply.`
- Several sources go in one line, joined with "and", and the line ends "Their review rules
  still apply.": `⚠️ Overriding REVIEW.md and AGENTS.md layout (...). Their review rules still apply.`
- `<what it asked for>` names the overridden layout in a few words, such as
  "summary paragraph, verdict last".
- No override, no line.

## Header

- **Verdict:** `## Fix before merge` when any finding scores 3 or higher, blocked findings
  included. Otherwise `## Safe to merge`.
- **Stats line:** `<N> findings · top impact <X>/5 · <F> files`. Use "1 finding" and
  "1 file" for one. `<X>` is the highest score. `<F>` counts the files in the reviewed diff.
- **Zero findings:** `## Safe to merge` and `0 findings · <F> files`, and nothing else.
- In reformat mode the stats line ends with ` · from <source>: <K> confirmed, <D> dropped`
  (see `reformat-mode.md`).

## Finding fields, in this order

1. `### <n>. <dot> [X/5] <title>`. The dot colors the score: 🔴 for 4 and 5, 🟡 for 2 and 3,
   ⚪ for 1. Numbers run from 1. The title states the consequence, not the
   code construct: "Stacked coupons can push an order total below zero", not "Wrong
   variable in loop".
2. `` `path:line` `` of the defect, repo-relative, alone on its line.
3. `**Impact:** ` only in a blocked finding, which has no diff to carry the problem: one or two
   sentences on what goes wrong, for whom, and how much. Every other finding explains the
   problem in its diff's comment lines.
4. `**Needs:** ` only when the fix needs something the developer can supply, such as an image
   file. The fix is still valid once it exists.
5. `**Blocked:** ` replaces the label, the diff and the blast radius when the fix depends on
   a fact nobody on the team has, such as an unpublished provider limit. Say what is missing
   and who can supply it. A blocked finding is still reported and still counts toward the
   verdict.
6. `**PROPOSED FIX:**` alone on the line above the diff, so nobody mistakes the diff for code
   already in the file. When this fix changes lines that a higher-ranked finding's fix also
   changes, write the diff on top of that fix and say so: `**PROPOSED FIX (on top of fix 1):**`.
   Every diff then shows a correct end result, and applying the fixes in order works.
7. **Diff:** a top-level ```` ```diff ```` block where every line is numbered: its sign (`-`,
   `+` or a space), its line number, then ` | ` and the code, as in `+18 |     return total;`.
   A `-` line keeps its number in the file now. Context and `+` lines take their number in the
   file after the fix, so the numbers read straight down the end result. A diff built on
   another fix is numbered as the file stands after that fix. Pad the numbers so every `|`
   lines up. Hunk headers are `@@ <file>:<line> @@`, naming the first line's number, never
   git's `@@ -12,6 +12,7 @@`; hunks for one file go top to bottom. Include enough unchanged
   context lines that the end result is readable. Every value in the diff must exist: no
   placeholders, no TODO. The diff holds every change the fix needs in order to work, across
   files if needed. Consequences of the fix go in the blast radius, not the diff. Code in a
   diff is copied exactly from the file, dashes and all.

   Comment lines carry the reasoning, so the code and the reason read in one scan. Every run of
   `-` lines opens with a comment line saying what is wrong (`Problem:`): who it hurts, how
   badly, and whether it predates the diff. Every run of `+` lines opens with one saying why the
   new code fixes it (`Fix:`). A comment line takes the sign of its run, no line number, the
   file's own comment syntax, and a colored square right after that syntax:
   `-   |     // 🟥 Problem: ...` and `+   |     // 🟩 Fix: ...`. The square sets the comment
   apart from the removed or added code, which shares its line color, so every comment line
   carries it, a second one in the same run too. Keep each one to a short sentence. Comment
   lines are for reading, not part of the fix: applying it leaves them out unless the
   developer asks to keep them.
8. `**Blast radius:**` then a list, one sentence per item, each with a `` `file:line` ``
   reference (`` `:737` `` is fine for another line in a file already named), no code. Cover
   other callers and readers the fix changes, behavior that changes for users, existing data
   the fix does not repair, tests the fix needs, and anything the fix leaves open. Every item
   names a place that changes, breaks or still needs work. Never list what stays the same,
   such as a caller the fix does not touch.

## Scores

| Score | Dot | Meaning |
|---|---|---|
| 5 | 🔴 | Breaks production, loses money or data, or opens a security hole, every time or whenever someone tries |
| 4 | 🔴 | The same kinds of damage, but only under some real conditions |
| 3 | 🟡 | Wrong behavior users notice, with no lasting damage |
| 2 | 🟡 | Slows future work: a missing test, confusing code |
| 1 | ⚪ | Cosmetic and visible to users, such as a missing cover image |

- Code formatting and style are never reported, so they never get a score.
- Every finding gets the full shape, whatever its score. No cap, no compact tail.
- Order: highest score first. Equal scores are ordered by path, then line.

## Layout rules

- Never wrap the output in a code fence. Inside an outer fence, diffs render as plain text
  and lose their color.
- Diffs are top-level ```` ```diff ```` blocks.
- A `---` separator goes after the header and between findings, with a blank line above and
  below it. Without the blank line above, Markdown turns the preceding line into a heading.
- No blank lines inside a finding. Blank lines appear only around separators. A blank line
  of code in a diff keeps its number: ` 15 |`.
- Labels are bold: **Impact:**, **Needs:**, **Blocked:**, **PROPOSED FIX:**, **Blast radius:**.
- No sections other than the ones above. No summary, no "what is fine", no closing line.
- No em dashes or en dashes in your own words or in code you add. Code in a diff is copied
  exactly from the file.

## Example: a review with findings

<!-- example:start review -->
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
<!-- example:end -->

## Example: nothing broken, with an override

<!-- example:start review -->
⚠️ Overriding REVIEW.md layout (summary paragraph, severity groups, verdict last). Its review rules still apply.
## Safe to merge
0 findings · 7 files
<!-- example:end -->
