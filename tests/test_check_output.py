import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "actually-readable-code-review" / "scripts"))

import check_output  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def rules(text, mode="auto"):
    return [p.rule for p in check_output.check(text, mode)]


ZERO = "## Safe to merge\n0 findings · 4 files\n"
OVERRIDE = "⚠️ Overriding REVIEW.md layout (summary paragraph, verdict last). Its review rules still apply.\n"


class HeaderTests(unittest.TestCase):
    def test_zero_findings_passes(self):
        self.assertEqual(check_output.check(ZERO), [])

    def test_outer_fence_rejected(self):
        problems = check_output.check("```markdown\n" + ZERO + "```\n")
        self.assertEqual([(p.line, p.rule) for p in problems], [(1, "outer-fence")])

    def test_override_line_passes(self):
        self.assertEqual(rules(OVERRIDE + "## Safe to merge\n0 findings · 2 files\n"), [])

    def test_override_without_variation_selector_passes(self):
        text = OVERRIDE.replace("⚠️", "⚠") + "## Safe to merge\n0 findings · 2 files\n"
        self.assertEqual(rules(text), [])

    def test_override_line_malformed(self):
        text = "⚠️ Overriding REVIEW.md.\n" + ZERO
        self.assertIn("override-line", rules(text))

    def test_bad_header(self):
        self.assertIn("header", rules("## Looks good\n0 findings · 4 files\n"))

    def test_stats_malformed(self):
        self.assertIn("stats", rules("## Safe to merge\nno findings\n"))

    def test_singular_plural(self):
        self.assertEqual(rules("## Safe to merge\n0 findings · 1 file\n"), [])
        self.assertIn("stats", rules("## Safe to merge\n0 findings · 1 files\n"))
        self.assertIn("stats", rules("## Safe to merge\n0 finding · 2 files\n"))

    def test_zero_with_extra_content(self):
        self.assertIn("zero-extra", rules(ZERO + "\nAll good otherwise.\n"))

    def test_crlf_same_result(self):
        inputs = [
            ZERO,
            OVERRIDE + "## Safe to merge\n0 findings · 2 files\n",
            "## Looks good\n0 findings · 4 files\n",
            "## Safe to merge\nno findings\n",
            ZERO + "\nAll good otherwise.\n",
        ]
        for text in inputs:
            with self.subTest(text=text):
                self.assertEqual(rules(text.replace("\n", "\r\n")), rules(text))

    def test_trailing_blank_lines_ok(self):
        self.assertEqual(rules(ZERO + "\n\n\n"), [])
        self.assertEqual(rules(ZERO.rstrip("\n")), [])

    def test_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = Path(tmp) / "good.md"
            good.write_text(ZERO, encoding="utf-8")
            bad = Path(tmp) / "bad.md"
            bad.write_text("## Looks good\n", encoding="utf-8")

            out = io.StringIO()
            with redirect_stdout(out):
                code = check_output.main([str(good)])
            self.assertEqual(code, 0)
            self.assertEqual(out.getvalue().strip(), "OK")

            out = io.StringIO()
            with redirect_stdout(out):
                code = check_output.main([str(bad)])
            self.assertEqual(code, 1)
            self.assertTrue(out.getvalue().startswith("line 1: [header]"), out.getvalue())



VALID = (FIXTURES / "review_valid.md").read_text(encoding="utf-8")
COUPON_PLUS = "+18 |     total -= total * coupon.percent / 100;"
PROBLEM = "-   |     // 🟥 Problem: each coupon comes off the original price, so a 60% and a 50% coupon make the total negative."
FIX = "+   |     // 🟩 Fix: take each coupon off the running total, which can never drop below zero."
ICON_FIX = "+   |     // 🟩 Fix: the card showed an empty square where every other card shows its icon."


class ReviewFindingTests(unittest.TestCase):
    def test_valid_review_passes(self):
        self.assertEqual(check_output.check(VALID), [])

    def test_extra_section_rejected(self):
        self.assertIn("finding-heading", rules(VALID + "\n---\n\n### Checked, fine\n- all good\n"))

    def test_missing_separator(self):
        self.assertIn("separator", rules(VALID.replace("\n---\n\n### 2.", "\n### 2.")))

    def test_separator_without_blank_above(self):
        text = VALID.replace("stacking needs its own case.\n\n---", "stacking needs its own case.\n---")
        self.assertIn("separator", rules(text))

    def test_blank_line_inside_finding(self):
        text = VALID.replace("`src/cart/applyDiscounts.ts:18`\n**PROPOSED FIX:**", "`src/cart/applyDiscounts.ts:18`\n\n**PROPOSED FIX:**")
        self.assertIn("blank-line", rules(text))

    def test_blank_line_inside_diff_ok(self):
        self.assertEqual(rules(VALID.replace(" 19 |   }\n 20 |   return total;", " 19 |   }\n 20 |\n 21 |   return total;")), [])

    def test_heading_malformed(self):
        self.assertIn("finding-heading", rules(VALID.replace("### 1. 🔴 [4/5]", "### 1. [4]")))

    def test_numbering_gap(self):
        text = VALID.replace("### 3. ⚪ [1/5]", "### 4. ⚪ [1/5]").replace("### 2. 🟡 [3/5]", "### 3. 🟡 [3/5]")
        self.assertIn("numbering", rules(text))

    def test_scores_not_sorted(self):
        text = VALID.replace("### 1. 🔴 [4/5]", "### 1. ⚪ [1/5]").replace("### 3. ⚪ [1/5]", "### 3. 🔴 [4/5]")
        self.assertIn("order", rules(text))

    def test_location_missing(self):
        self.assertIn("location", rules(VALID.replace("`src/cart/applyDiscounts.ts:18`\n", "")))

    def test_needs_after_diff(self):
        needs = "**Needs:** the icon file at `public/icons/export.svg`.\n"
        text = VALID.replace(needs, "").replace(" 13 |   },\n```\n", " 13 |   },\n```\n" + needs)
        self.assertIn("field-order", rules(text))

    def test_blocked_with_diff(self):
        text = VALID.replace("support for the limit.\n", "support for the limit.\n```diff\n+1 | x\n```\n")
        self.assertIn("blocked-extra", rules(text))

    def test_no_diff_no_blocked(self):
        start = VALID.index("**PROPOSED FIX:**\n```diff\n@@ src/cart")
        end = VALID.index("stacking needs its own case.\n") + len("stacking needs its own case.\n")
        self.assertIn("diff-missing", rules(VALID[:start] + VALID[end:]))

    def test_wrong_fence_language(self):
        self.assertIn("diff-fence", rules(VALID.replace("```diff\n@@ src/cart", "```php\n@@ src/cart")))
        self.assertIn("diff-fence", rules(VALID.replace(" 13 |   },\n```\n**Blast radius:**", " 13 |   },\n**Blast radius:**")))

    def test_git_hunk_header_rejected(self):
        text = VALID.replace("@@ src/cart/applyDiscounts.ts:17 @@", "@@ -12,6 +12,7 @@")
        self.assertIn("hunk-header", rules(text))

    def test_blast_radius_missing(self):
        text = VALID.replace("**Blast radius:**\n- `src/ui/ToolGrid.vue:30` renders the icon in place of the empty square.\n", "")
        self.assertIn("blast-radius", rules(text))

    def test_blast_item_without_ref(self):
        item = "- `src/cart/summary.ts:40` shows per-coupon savings from the original price and must switch to the running total."
        self.assertIn("blast-ref", rules(VALID.replace(item, "- the summary changes too.")))
        self.assertEqual(rules(VALID.replace(item, "- `:40` in the same summary file must switch to the running total.")), [])

    def test_placeholder(self):
        self.assertIn("placeholder", rules(VALID.replace(COUPON_PLUS, "+18 |     total -= total * <fal value>;")))
        self.assertIn("placeholder", rules(VALID.replace(COUPON_PLUS, "+18 |     total -= total; // TODO")))
        ok = "+18 |     const rows = render('<div class=\"x\">', total as Array<T extends U>);"
        self.assertEqual(rules(VALID.replace(COUPON_PLUS, ok)), [])

    def test_dash_in_prose(self):
        self.assertIn("dash", rules(VALID.replace("stacking needs its own case.", "stacking needs its own case \u2014 bad.")))
        self.assertIn("dash", rules(VALID.replace(COUPON_PLUS, COUPON_PLUS + " // a \u2013 b")))

    def test_dash_in_existing_code_ok(self):
        text = VALID.replace(" 17 |   for (const coupon of coupons) {", " 17 |   for (const coupon of coupons) { // a \u2014 b")
        text = text.replace("-18 |     total -= price * coupon.percent / 100;", "-18 |     total -= price * coupon.percent / 100; // \u2014")
        self.assertEqual(rules(text), [])

    def test_separator_and_heading_inside_diff_ok(self):
        body = " 10 |   export: {\n 11 |     label: 'Export',\n" + ICON_FIX + "\n+12 |     icon: '/icons/export.svg',\n 13 |   },"
        self.assertEqual(rules(VALID.replace(body, " 10 | ---\n 11 | ### Notes\n+   | # 🟩 Fix: x\n+12 | icon: /icons/export.svg")), [])

    def test_stats_count_mismatch(self):
        self.assertIn("stats-count", rules(VALID.replace("3 findings · top", "2 findings · top")))

    def test_top_impact_mismatch(self):
        self.assertIn("stats-top", rules(VALID.replace("top impact 4/5", "top impact 5/5")))

    def test_verdict_mismatch(self):
        self.assertIn("verdict", rules(VALID.replace("## Fix before merge", "## Safe to merge")))
        low = (VALID.replace("### 1. 🔴 [4/5]", "### 1. 🟡 [2/5]").replace("### 2. 🟡 [3/5]", "### 2. 🟡 [2/5]")
               .replace("top impact 4/5", "top impact 2/5"))
        self.assertIn("verdict", rules(low))

    def test_reformat_stats_passes(self):
        stats = "3 findings · top impact 4/5 · 5 files"
        self.assertEqual(rules(VALID.replace(stats, stats + " · from CodeRabbit: 2 confirmed, 6 dropped")), [])
        self.assertIn("stats-count", rules(VALID.replace(stats, stats + " · from CodeRabbit: 4 confirmed, 6 dropped")))


APPLIED = (FIXTURES / "applied_valid.md").read_text(encoding="utf-8")


class AppliedTests(unittest.TestCase):
    def test_valid_applied_passes(self):
        self.assertEqual(check_output.check(APPLIED, "applied"), [])

    def test_auto_detects_applied(self):
        self.assertEqual(check_output.check(APPLIED), [])

    def test_applied_header_malformed(self):
        self.assertIn("header", rules(APPLIED.replace("## Applied 1 of 3 fixes", "## Applied 1 fixes")))
        self.assertIn("header", rules(APPLIED.replace("## Applied 1 of 3 fixes", "## Applied 1 of 1 fixes")))

    def test_applied_stats_variants(self):
        ran = "tests ran: 12 passed, 0 failed"
        self.assertEqual(rules(APPLIED.replace(ran, "tests not run: nothing in the repo documents a test command")), [])
        self.assertIn("applied-stats", rules(APPLIED.replace(ran, "tests not run")))
        self.assertIn("applied-stats", rules(APPLIED.replace("1 file edited", "1 files edited")))

    def test_counts_mismatch(self):
        self.assertIn("applied-counts", rules(APPLIED.replace("Applied 1 of 3", "Applied 2 of 3")))
        self.assertIn("applied-counts", rules(APPLIED.replace("1 file edited", "2 files edited")))
        self.assertIn("applied-counts", rules(APPLIED.replace("1 skipped", "2 skipped")))

    def test_two_outcomes(self):
        text = APPLIED.replace("**Skipped:** `public", "**Edited:**\n- `src/ui/ToolCard.vue`: applied as proposed.\n**Skipped:** `public")
        self.assertIn("outcome", rules(text))

    def test_no_outcome(self):
        text = APPLIED.replace("**Blocked:** the provider publishes no per-minute limit; ask its support for the number.\n", "")
        self.assertIn("outcome", rules(text))

    def test_edited_item_format(self):
        text = APPLIED.replace("- `src/cart/applyDiscounts.ts`: applied as proposed.", "- `src/cart/applyDiscounts.ts` changed")
        self.assertIn("edited-items", rules(text))

    def test_still_open_after_skipped(self):
        self.assertIn("still-open", rules(APPLIED + "**Still open:**\n- `a.ts:1` is not covered.\n"))

    def test_still_open_item_without_ref(self):
        text = APPLIED.replace("not repaired (`src/orders/OrderRepository.ts:88`).", "not repaired.")
        self.assertIn("still-open", rules(text))

    def test_numbering_not_sequential(self):
        self.assertIn("numbering", rules(APPLIED.replace("### 3. ⚪ [1/5]", "### 4. ⚪ [1/5]")))

    def test_not_requested_skip_passes(self):
        start = APPLIED.index("**Skipped:**")
        self.assertEqual(rules(APPLIED[:start] + "**Skipped:** not requested\n"), [])

    def test_location_line_not_allowed(self):
        heading = "### 1. 🔴 [4/5] Stacked coupons can push an order total below zero\n"
        self.assertIn("field-order", rules(APPLIED.replace(heading, heading + "`src/cart/applyDiscounts.ts:18`\n")))


EM = "\u2014"
COUPON_MINUS = "-18 |     total -= price * coupon.percent / 100;"


class FinalReviewFixTests(unittest.TestCase):
    def test_html_boolean_attributes_not_placeholders(self):
        for line in ["+18 |     <button disabled>Save</button>", "+18 |     <details open>", "+18 |     <input required>",
                     "+18 |     <my-widget open>"]:
            with self.subTest(line=line):
                self.assertEqual(rules(VALID.replace(COUPON_PLUS, line)), [])

    def test_carried_todo_not_placeholder(self):
        text = VALID.replace(COUPON_MINUS, "-18 |     total -= price; // TODO(ana): drop after launch")
        text = text.replace(COUPON_PLUS, "+18 |     total -= total; // TODO(ana): drop after launch")
        self.assertEqual(rules(text), [])

    def test_todo_string_value_not_placeholder(self):
        self.assertEqual(rules(VALID.replace(COUPON_PLUS, "+18 |     status: 'TODO',")), [])
        self.assertIn("placeholder", rules(VALID.replace(COUPON_PLUS, "+18 |     total = TODO;")))

    def test_placeholder_message_does_not_push_blocked(self):
        problems = check_output.check(VALID.replace(COUPON_PLUS, "+18 |     total -= total * <fal value>;"))
        message = next(p.message for p in problems if p.rule == "placeholder")
        self.assertNotIn("Blocked", message)

    def test_dash_carried_from_existing_code_ok(self):
        text = VALID.replace(COUPON_MINUS, "-18 |     label = 'Total " + EM + " ' + price;")
        text = text.replace(COUPON_PLUS, "+18 |     label = t('Total " + EM + " ') + price;")
        self.assertEqual(rules(text), [])

    def test_inner_fence_in_numbered_diff_passes(self):
        text = VALID.replace(" 17 |   for (const coupon of coupons) {", " 17 | ```sh")
        self.assertEqual(rules(text), [])

    def test_unnumbered_fence_line_closes_diff_early(self):
        self.assertIn("diff-fence", rules(VALID.replace(" 19 |   }\n", " ```\n")))


BLAST_ITEM = "- `src/cart/summary.ts:40` shows per-coupon savings from the original price and must switch to the running total."


class LiveTestFixTests(unittest.TestCase):
    def test_override_two_sources_their_passes(self):
        line = "⚠️ Overriding REVIEW.md and AGENTS.md layout (summary first, verdict last). Their review rules still apply.\n"
        self.assertEqual(rules(line + ZERO), [])

    def test_blast_item_about_what_stays_the_same_rejected(self):
        for item in [
            "- `index.php:13` and `:14` stay the only other readers of `$password`, so the database connection is unchanged.",
            "- `index.php:8` is the only reader of the password, so no other caller changes.",
            "- `src/cart/summary.ts:40` is unaffected by the fix.",
            "- `src/cart/summary.ts:40` stays the same.",
            "- `src/cart/summary.ts:40` reads the total, and nothing else changes.",
        ]:
            with self.subTest(item=item):
                self.assertIn("blast-filler", rules(VALID.replace(BLAST_ITEM, item)))

    def test_blast_item_stating_a_problem_passes(self):
        item = "- `index.php:8` still holds the password in source, readable to anyone with repo access."
        self.assertEqual(rules(VALID.replace(BLAST_ITEM, item)), [])



ALIGNED = (" 10 |   export: {\n 11 |     label: 'Export',\n" + ICON_FIX
           + "\n+12 |     icon: '/icons/export.svg',\n 13 |   },")


class NumberedDiffTests(unittest.TestCase):
    def test_unlabeled_diff_rejected(self):
        self.assertIn("fix-label", rules(VALID.replace("**PROPOSED FIX:**\n", "", 1)))

    def test_label_on_top_of_earlier_fix_passes(self):
        text = VALID.replace("export.svg`.\n**PROPOSED FIX:**", "export.svg`.\n**PROPOSED FIX (on top of fix 1):**")
        self.assertEqual(rules(text), [])

    def test_label_on_top_of_own_or_later_fix_rejected(self):
        for label in ["**PROPOSED FIX (on top of fix 3):**", "**PROPOSED FIX (on top of fixes 1 and 4):**"]:
            with self.subTest(label=label):
                text = VALID.replace("export.svg`.\n**PROPOSED FIX:**", "export.svg`.\n" + label)
                self.assertIn("fix-label", rules(text))

    def test_unnumbered_line_rejected(self):
        self.assertIn("diff-numbers", rules(VALID.replace(COUPON_PLUS, "+    total -= total * coupon.percent / 100;")))

    def test_context_after_added_line_takes_new_number(self):
        self.assertIn("diff-numbers", rules(VALID.replace(" 13 |   },", " 12 |   },")))

    def test_removed_line_keeps_current_number(self):
        old = COUPON_MINUS + "\n" + FIX + "\n" + COUPON_PLUS + "\n 19 |   }\n"
        ok = COUPON_MINUS + "\n 18 |   }\n"
        self.assertEqual(rules(VALID.replace(old, ok).replace(" 20 |   return total;", " 19 |   return total;")), [])
        self.assertIn("diff-numbers", rules(VALID.replace(old, ok.replace(" 18 |   }", " 19 |   }"))))

    def test_hunk_header_names_first_line(self):
        text = VALID.replace("@@ src/cart/applyDiscounts.ts:17 @@", "@@ src/cart/applyDiscounts.ts:18 @@")
        self.assertIn("hunk-header", rules(text))

    def test_numbers_line_up(self):
        header = "@@ src/ui/ToolCard.vue:10 @@\n"
        short = "@@ src/ui/ToolCard.vue:9 @@\n 9 | a\n" + ALIGNED
        self.assertIn("diff-align", rules(VALID.replace(header + ALIGNED, short)))
        padded = "@@ src/ui/ToolCard.vue:9 @@\n  9 | a\n" + ALIGNED
        self.assertEqual(rules(VALID.replace(header + ALIGNED, padded)), [])

    def test_second_hunk_carries_the_first_hunks_shift(self):
        two = (ALIGNED + "\n@@ src/ui/ToolCard.vue:21 @@\n 21 |   import: {\n-   |     // 🟥 Problem: x.\n"
               "-21 |     hidden: true,\n 22 |   },")
        self.assertEqual(rules(VALID.replace(ALIGNED, two)), [])
        wrong = two.replace(":21 @@\n 21 |", ":20 @@\n 20 |")
        self.assertIn("diff-numbers", rules(VALID.replace(ALIGNED, wrong)))


class ScoreColorTests(unittest.TestCase):
    def test_missing_dot_rejected(self):
        self.assertIn("score-color", rules(VALID.replace("### 1. 🔴 [4/5]", "### 1. [4/5]")))

    def test_wrong_dot_rejected(self):
        self.assertIn("score-color", rules(VALID.replace("### 1. 🔴 [4/5]", "### 1. 🟡 [4/5]")))
        self.assertIn("score-color", rules(VALID.replace("### 2. 🟡 [3/5]", "### 2. 🔴 [3/5]")))
        self.assertIn("score-color", rules(VALID.replace("### 3. ⚪ [1/5]", "### 3. 🟡 [1/5]")))

    def test_dot_with_variation_selector_passes(self):
        self.assertEqual(rules(VALID.replace("### 3. ⚪ [1/5]", "### 3. ⚪" + chr(0xFE0F) + " [1/5]")), [])

    def test_applied_heading_needs_matching_dot(self):
        self.assertIn("score-color", rules(APPLIED.replace("### 1. 🔴 [4/5]", "### 1. [4/5]")))
        self.assertIn("score-color", rules(APPLIED.replace("### 3. ⚪ [1/5]", "### 3. 🔴 [1/5]")))


BLOCKED_IMPACT = ("**Impact:** all pending orders are sent in one burst, and the provider rejects requests over "
                  "its per-minute limit without a retry.\n")


class DiffCommentTests(unittest.TestCase):
    def test_removed_lines_need_a_problem_comment(self):
        self.assertIn("diff-comment", rules(VALID.replace(PROBLEM + "\n", "")))

    def test_added_lines_need_a_fix_comment(self):
        self.assertIn("diff-comment", rules(VALID.replace(ICON_FIX + "\n", "")))

    def test_comment_needs_its_label(self):
        self.assertIn("diff-comment", rules(VALID.replace("// 🟥 Problem:", "// 🟥 Why:")))
        self.assertIn("diff-comment", rules(VALID.replace("// 🟩 Fix: take", "// 🟩 Take")))

    def test_comment_line_lines_up(self):
        self.assertIn("diff-align", rules(VALID.replace(FIX, FIX.replace("+   |", "+  |"))))

    def test_more_comment_lines_inside_a_run_pass(self):
        self.assertEqual(rules(VALID.replace(FIX, FIX + "\n+   |     // 🟩 and the summary can reuse it.")), [])

    def test_comment_opener_carries_its_square(self):
        self.assertIn("diff-comment", rules(VALID.replace("// 🟥 Problem:", "// Problem:")))
        self.assertIn("diff-comment", rules(VALID.replace("// 🟩 Fix: take", "// Fix: take")))

    def test_square_matches_the_sign(self):
        self.assertIn("diff-comment", rules(VALID.replace("// 🟥 Problem:", "// 🟩 Problem:")))
        self.assertIn("diff-comment", rules(VALID.replace("// 🟩 Fix: take", "// 🟥 Fix: take")))

    def test_every_comment_line_carries_its_square(self):
        self.assertIn("diff-comment", rules(VALID.replace(FIX, FIX + "\n+   |     // and the summary can reuse it.")))

    def test_impact_only_on_blocked_findings(self):
        location = "`src/cart/applyDiscounts.ts:18`\n"
        self.assertIn("impact", rules(VALID.replace(location, location + "**Impact:** totals go negative.\n")))
        self.assertIn("impact", rules(VALID.replace(BLOCKED_IMPACT, "")))

    def test_applied_output_shows_no_diff(self):
        diff = "```diff\n@@ src/cart/applyDiscounts.ts:18 @@\n+18 |     total -= total;\n```\n"
        edited = "- `src/cart/applyDiscounts.ts`: applied as proposed.\n"
        self.assertIn("applied-diff", rules(APPLIED.replace(edited, edited + diff)))
        self.assertIn("applied-diff", rules(APPLIED.replace(edited, edited + "**PROPOSED FIX:**\n" + diff)))

if __name__ == "__main__":
    unittest.main()
