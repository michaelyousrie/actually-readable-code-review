# actually-readable-code-review (ARCR)

An Agent Skill that reviews code changes, or reformats another reviewer's output, into one
fixed, skimmable format. The product is the output format; read
`skills/actually-readable-code-review/references/output-contract.md` before changing anything.

## Layout

- `skills/actually-readable-code-review/SKILL.md`: entry point the agent loads.
- `skills/actually-readable-code-review/references/`: the contract and the method, read on demand.
- `skills/actually-readable-code-review/scripts/check_output.py`: checks an output against the
  contract. Standard library only, Python 3.10+.
- `tests/`: unit tests for the checker, the skill files and the eval scripts.
- `tests/<Project>/`: live test projects reviewed with ARCR after skill changes. `src/` holds
  the code, and `ARCR.md` beside it holds how to run each round, the expected findings and
  the latest outputs.
- `evals/`: review-depth evals built from real public bug-fix commits.

## Commands

- Run every test: `python3 -m unittest discover -s tests -v`
- Check an output: `python3 skills/actually-readable-code-review/scripts/check_output.py FILE`

## Rules

- `references/output-contract.md` and `check_output.py` change together. A contract change
  needs a checker change and a test, in the same change.
- Examples are synthetic and sit between `<!-- example:start <mode> -->` and
  `<!-- example:end -->` markers, where `<mode>` is `review` or `applied`. The tests run the
  checker on every one of them.
- No em dashes or en dashes in any file. Write them as `\u2014` or `\u2013` escapes in test
  source. Check with Python, not grep.
- `SKILL.md` frontmatter uses only `name`, `description`, `license` and `metadata`.
- Skill text names no vendor-specific tools and must work without subagents.
- No code or identifiers from private projects anywhere in the repo.
