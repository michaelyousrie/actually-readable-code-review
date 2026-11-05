#!/usr/bin/env python3
"""Score an agent's ARCR output against an eval case.

Usage: score.py CASE.json OUTPUT.md [--reformat]
Passes when the output follows the contract and has a finding at the case's expected
location with at least the expected score. With --reformat, the case's false finding must
be absent and the stats line must report at least one dropped finding.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "actually-readable-code-review" / "scripts"))

import check_output  # noqa: E402

HEADING_RE = re.compile(r"^### \d+\. (?:\S+ )?\[([1-5])/5\] ")
LOCATION_RE = re.compile(r"^`([^`\s]+):(\d+)`$")
DROPPED_RE = re.compile(r" · from .+: \d+ confirmed, (\d+) dropped$")
NEARBY_LINES = 3


def _findings(output: str) -> list[tuple[str, int, int]]:
    lines = output.replace("\r\n", "\n").split("\n")
    found = []
    for index, line in enumerate(lines[:-1]):
        heading = HEADING_RE.match(line)
        location = LOCATION_RE.match(lines[index + 1].strip()) if heading else None
        if heading and location:
            found.append((location.group(1), int(location.group(2)), int(heading.group(1))))
    return found


def score(case: dict, output: str, reformat: bool = False) -> tuple[bool, list[str]]:
    """Return (passed, reasons it failed)."""
    reasons: list[str] = []
    problems = check_output.check(output, "review")
    if problems:
        listed = "; ".join(f"line {p.line} [{p.rule}]" for p in problems[:5])
        reasons.append(f"format: {len(problems)} contract problems ({listed})")

    expect = case["expect"]
    findings = _findings(output)
    if not any(path.endswith(expect["path"]) and expect["line_min"] <= line <= expect["line_max"]
               and points >= expect["min_score"] for path, line, points in findings):
        reasons.append(f"no finding at {expect['path']}:{expect['line_min']}-{expect['line_max']} "
                       f"scoring at least {expect['min_score']}/5")

    if reformat:
        false = case["reformat"]["false_finding"]
        if any(path.endswith(false["path"]) and abs(line - false["line"]) <= NEARBY_LINES
               for path, line, _points in findings):
            reasons.append(f"the false finding at {false['path']}:{false['line']} was kept")
        stats = next((line for line in output.split("\n") if " findings · " in line or " finding · " in line), "")
        dropped = DROPPED_RE.search(stats.strip())
        if not dropped or int(dropped.group(1)) < 1:
            reasons.append("the stats line reports nothing dropped")

    return not reasons, reasons


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    reformat = "--reformat" in args
    paths = [arg for arg in args if arg != "--reformat"]
    if len(paths) != 2:
        print("usage: score.py CASE.json OUTPUT.md [--reformat]", file=sys.stderr)
        return 2
    case = json.loads(Path(paths[0]).read_text(encoding="utf-8"))
    output = Path(paths[1]).read_text(encoding="utf-8")
    passed, reasons = score(case, output, reformat)
    print("PASS" if passed else "FAIL")
    for reason in reasons:
        print(f"- {reason}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
