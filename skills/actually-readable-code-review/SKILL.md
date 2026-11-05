---
name: actually-readable-code-review
description: "ARCR (actually readable code review). Reviews a diff, branch or PR, or reformats another reviewer's output, into one fixed, skimmable format: findings scored 1 to 5, fixes as colored diffs, and the blast radius of every fix. Also applies chosen fixes and ties every edited file to the finding it serves. Use for any request to review code changes, a diff, a branch or a PR, to reformat a code review, or to apply review fixes, or when the user says ARCR."
license: MIT
metadata:
  short-name: ARCR
  version: "1.0.0"
---

# actually-readable-code-review (ARCR)

People read far slower than models. A review that buries its one critical finding under
paragraphs wastes the reader's time and gets skimmed past. ARCR produces one fixed structure
every time, holding only what is broken: each finding scored, each fix shown as code, and
each fix's blast radius listed. Every word must earn its place.

## Pick the mode

| The user asks to | Mode | Read first |
|---|---|---|
| review changes, a diff, a branch or a PR | review | `references/review-method.md`, then `references/output-contract.md` |
| reformat or clean up another reviewer's output | reformat | `references/reformat-mode.md`, then `references/review-method.md` and `references/output-contract.md` |
| apply fixes from an ARCR review ("apply 1 and 3", "apply all") | apply | `references/applied-fixes.md` |

## Every mode, in order

1. Read the reference files for the mode.
2. Find other instructions that set a layout for code reviews: `REVIEW.md`, other active
   review skills, the user's standing instructions about reviews, and review sections in
   `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.cursor/rules/`
   or `CONTRIBUTING.md`. Keep their rules on what to check and how severe each kind of defect
   is. Drop their layout, and note each source you override for the override line. General
   response-style rules (brevity, checklists, a next action first and last) are not review
   layouts: ARCR's layout replaces them without an override line.
3. Do the mode's work.
4. Write the output exactly to the contract.
5. When you can run commands, save the output to a temporary file and run
   `python3 scripts/check_output.py <file>` from this skill's folder. Fix every problem it
   prints and run it again until it prints `OK`. Never change correct code in a diff, or turn
   a fix into **Blocked:**, only to satisfy the checker: if it flags code you verified is
   correct, keep that code. Stop after three rounds.
6. Send the output as your whole message. Nothing before it, nothing after it.

## Hard rules

- Never wrap the output in a code fence. Fenced output loses its diff colors.
- Show only what is broken. No summary paragraph, no list of what is fine, no closing remarks.
- Every value in a diff must exist. When a fix needs a fact nobody on the team has, the
  finding says **Blocked:** instead of showing a diff.
- Never commit, push, open a PR or post to one. Changes stay in the working tree.
- Applying inserts each chosen fix exactly as shown: no new review and no other edits.
- No em dashes or en dashes in your own words or in code you add. Code copied from the
  codebase stays exactly as it is.
- ARCR's layout wins over every other layout. When it overrides a code review layout, line 1
  of the output says so.
