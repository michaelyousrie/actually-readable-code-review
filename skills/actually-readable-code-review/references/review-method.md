# Review method

The point of the method is that fixes stop producing the next round's findings. Write the
output with `output-contract.md`.

## 1. Find the target

- No target named: review the uncommitted changes, meaning tracked changes against `HEAD`
  plus untracked files. If there are none, review the current branch against its merge-base
  with the default branch.
- A branch named: review it against its merge-base with the default branch.
- A PR named: it must be checked out locally, because the blast radius needs the code. If it
  is not, ask the developer to check it out. Never switch branches yourself.
- `<F>` in the stats line is the number of files in the reviewed diff.

## 2. Read the rules and the whole diff

- Read the repo's review rules (`REVIEW.md`, agent instruction files, `CONTRIBUTING.md`).
  Their high-risk areas, blocking categories and conventions decide what you check, and their
  severity labels map onto ARCR's scores.
- Read the whole diff before judging any part of it.

## 3. Trace inputs to their source

For every value that a charge, a permission or a limit depends on, find where the value
comes from: user input, the browser, a header, a config file, the database, a third party.
A value the server trusts but a user can set is a finding.

Example: a cost estimate can match the charge exactly and still be wrong, because the billed
duration came from the browser. Checking the estimate against the charge passes; asking where
the duration comes from finds the hole.

## 4. Scope

- Report defects in code the diff adds or changes.
- Defects older than the diff are in scope only when code the diff adds or changes relies on
  them, found by tracing from the changed lines. They count toward the verdict, because the
  new code ships on top of them. Say in the `Problem:` comment that they predate the diff,
  or in **Impact:** for a blocked finding.
- Old bugs in code the diff does not reach are not reported.

## 5. Verify every fact

Check each claim against the real source: the code, a live provider page, a schema, an API
response. A claim that could not be verified is labeled "unverified" inline, in the sentence
that makes it. Never fill a gap from memory or pattern.

## 6. Score

Use the scale in `output-contract.md`. Score the damage a reasonable user of the software
gets if the defect ships, not how interesting the code is.

## 7. Write the fix

- The diff holds every change the fix needs in order to work, across files if needed.
- When two fixes change the same lines, write the lower-ranked one on top of the higher-ranked
  fix, so applying them in order works (see `output-contract.md`).
- Every value in the diff must exist. If a value is unknown to everyone on the team (an
  unpublished limit, an undocumented provider behavior), there is no diff: the finding says
  **Blocked:**, names what is missing and who can supply it.
- If the fix needs something the developer can supply (an asset, a value they own), add a
  **Needs:** line and still show the diff.
- The reasoning goes in the diff's `Problem:` and `Fix:` comment lines, which are not applied
  by default. Add a real code comment, numbered like any other line, only when the code needs
  one long-term, such as one that stops a non-obvious invariant from being "fixed" later.
  Update existing comments and docblocks that the fix makes false.

## 8. Blast radius comes from a search, not a guess

Search the codebase for every caller and reader of each symbol, field, config key, route and
table the fix changes, then write the list. Cover:

- other callers and readers whose behavior changes
- behavior that changes for users
- existing data the fix does not repair
- tests the fix needs
- anything the fix leaves open, such as the same defect in a sibling feature

Never list what stays the same. A caller the fix does not affect is left out, not listed as
safe.

## 9. What never to report

- Formatting, style, import order, naming preferences. Formatters and linters own those.
- Speculation with no concrete failure.
- Findings manufactured to look thorough. Zero findings is a valid review.
- The same defect twice. Merge duplicates into one finding.
