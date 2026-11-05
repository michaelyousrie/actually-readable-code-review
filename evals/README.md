# Review-depth evals

Each case is a real bug-fix commit from a public repo. `prepare.py` clones the repo, checks
out the fix and reverse-applies it, so the uncommitted changes put the bug back. A reviewer
using ARCR should find it.

Cases live in `cases/<id>.json`. Checkouts go to `work/`, which git ignores. Each checkout is
a fresh repo with one commit, "baseline", and no remote, so its history does not name the
fix. A case may list `revert_paths` to revert only the code files; tests the fix added are
then left out of the baseline, so they cannot give the bug away.

## Run a case

1. Prepare the checkout:
   `python3 evals/prepare.py evals/cases/<id>.json evals/work`
   It prints the checkout path and the prompt to use.
2. Open any agent that has the skill installed, give it the printed prompt, and save its
   final message, exactly as sent, to `evals/work/<id>-output.md`.
3. Score it:
   `python3 evals/score.py evals/cases/<id>.json evals/work/<id>-output.md`
   It prints `PASS`, or `FAIL` with the reasons.

A pass needs output that follows the contract, plus a finding at the case's expected file
and line range with at least the expected score.

## Run the reformat variant

Cases with a `reformat` field also carry a noisy review in `reformat/<id>.md`, containing the
true finding and one false finding.

1. Prepare the checkout as above.
2. Ask the agent to reformat `evals/reformat/<id>.md` with ARCR against the prepared
   checkout, and save its final message.
3. Score with `--reformat`:
   `python3 evals/score.py evals/cases/<id>.json evals/work/<id>-reformat.md --reformat`

On top of the normal pass rules, the false finding must be gone (a finding within 3 lines of
it counts as kept), and the stats line must report at least one dropped finding.

## Clean up

`rm -rf evals/work`
