#!/usr/bin/env python3
"""Check an ARCR output against the output contract.

Usage: check_output.py [--mode auto|review|applied] FILE   (FILE may be - for stdin)
Prints OK and exits 0, or prints one "line <n>: [<rule>] <message>" per problem and exits 1.
Standard library only, Python 3.10+.
"""
from __future__ import annotations

import argparse
import re
import sys
from typing import NamedTuple


class Problem(NamedTuple):
    line: int
    rule: str
    message: str


OVERRIDE_RE = re.compile(
    r"^⚠️? Overriding .+ layout \(.+\)\. (Its|Their) review rules still apply\.$"
)
REVIEW_HEADER_RE = re.compile(r"^## (Fix before merge|Safe to merge)$")
APPLIED_HEADER_RE = re.compile(r"^## Applied (\d+) of (\d+) (fix|fixes)$")
REVIEW_STATS_RE = re.compile(
    r"^(\d+) (finding|findings)(?: · top impact ([1-5])/5)? · (\d+) (file|files)"
    r"(?: · from (.+): (\d+) confirmed, (\d+) dropped)?$"
)


HEADING_RE = re.compile(r"^### (\d+)\. (?:(\S+) )?\[([1-5])/5\] \S.*$")
SCORE_DOTS = {5: "\U0001F534", 4: "\U0001F534", 3: "\U0001F7E1", 2: "\U0001F7E1", 1: "\u26aa"}
LOCATION_RE = re.compile(r"^`[^`\s]+:\d+`$")
REF_RE = re.compile(r"`[^`]*:\d+`")
FILLER_RE = re.compile(
    r"\b(unchanged|unaffected|stays? the same|nothing else|no other (callers?|readers?|files?|code|changes?))\b",
    re.I,
)
HUNK_RE = re.compile(r"^@@ (\S+):(\d+) @@$")
ANGLE_RE = re.compile(r"<([a-z][\w-]*)\s+[a-z][a-z ]*>")
TODO_RE = re.compile(r"(?<![\w'\"])(TODO|FIXME)(?![\w'\"])")
HTML_TAGS = frozenset("""
    a abbr address area article aside audio b base bdi bdo blockquote body br button canvas caption
    circle cite code col colgroup component data datalist dd defs del details dfn dialog div dl dt em
    embed fieldset figcaption figure footer form g h1 h2 h3 h4 h5 h6 head header hgroup hr html i
    iframe img input ins kbd label legend li line link main map mark menu meta meter nav noscript
    object ol optgroup option output p param path picture polygon polyline pre progress q rect rp rt
    ruby s samp script search section select slot small source span strong style sub summary sup svg
    table tbody td template text textarea tfoot th thead time title tr track transition u ul use var
    video wbr
""".split())
FENCE_OPEN_RE = re.compile(r"^(`{3,})[^`]*$")
FENCE_CLOSE_RE = re.compile(r"^ {0,3}(`{3,})\s*$")
DIFF_OPEN_RE = re.compile(r"^`{3,}diff$")
COMMENT_SQUARES = {"-": "\U0001F7E5", "+": "\U0001F7E9"}
COMMENT_LINE_RE = re.compile(r"^([+-])( +)\|(?: (.*))?$")
DIFF_LINE_RE = re.compile(r"^([ +-])( *)(\d+) \|(?: .*)?$")
FIX_LABEL_RE = re.compile(r"^\*\*PROPOSED FIX(?: \(on top of fix(?:es)? (\d+(?:(?:, | and )\d+)*)\))?:\*\*$")
APPLIED_STATS_RE = re.compile(
    r"^(\d+) (file|files) edited · (\d+) skipped · (\d+) blocked · tests "
    r"(?:ran: (\d+) passed, (\d+) failed|not run: \S.*)$"
)
OUTCOME_RE = re.compile(r"^\*\*(Edited|Skipped|Blocked):\*\*")
EDITED_ITEM_RE = re.compile(r"^- `([^`]+)`( \(new\))?: \S.*$")
DASHES = ("\u2014", "\u2013")
SEPARATOR = "---"


class ReviewStats(NamedTuple):
    findings: int
    top: int | None
    confirmed: int | None


def _singular_ok(number: int, word: str, singular: str) -> bool:
    return (number == 1) == (word == singular)


def _normalize(text: str) -> list[str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _fence_kinds(lines: list[str]) -> list[str]:
    """Label each line "open", "close", "code" or "text", following CommonMark fence rules:
    a fence closes only on a line of at least as many backticks, indented 0 to 3 spaces."""
    kinds: list[str] = []
    length = 0
    for line in lines:
        if length == 0:
            opening = FENCE_OPEN_RE.match(line)
            kinds.append("open" if opening else "text")
            length = len(opening.group(1)) if opening else 0
        else:
            closing = FENCE_CLOSE_RE.match(line)
            if closing and len(closing.group(1)) >= length:
                kinds.append("close")
                length = 0
            else:
                kinds.append("code")
    return kinds


def _is_placeholder(line: str, others: list[str]) -> bool:
    """A placeholder on an added line: <some words> that is not an HTML tag, or a new TODO/FIXME."""
    for match in ANGLE_RE.finditer(line):
        word = match.group(1)
        if "-" not in word and word not in HTML_TAGS:
            return True
    for match in TODO_RE.finditer(line):
        carried = line[match.start():].strip()
        if not any(carried in other for other in others):
            return True
    return False


def check(text: str, mode: str = "auto") -> list[Problem]:
    """Return every contract problem in an ARCR output. An empty list means it passes."""
    lines = _normalize(text)
    first = next((i for i, line in enumerate(lines) if line.strip()), None)
    if first is None:
        return [Problem(1, "header", "the output is empty")]
    if lines[first].lstrip().startswith("```"):
        return [Problem(first + 1, "outer-fence",
                        "the output is wrapped in a code fence; never fence the output")]

    problems: list[Problem] = []
    i = first
    if lines[i].startswith("⚠"):
        if not OVERRIDE_RE.match(lines[i]):
            problems.append(Problem(i + 1, "override-line",
                                    "expected '⚠️ Overriding <source> layout (<what it asked for>). "
                                    "Its review rules still apply.' ('Their' for several sources)"))
        i += 1

    problems += _check_text(lines, first)
    header = lines[i] if i < len(lines) else ""
    if mode == "auto":
        mode = "applied" if header.startswith("## Applied") else "review"
    if mode == "review":
        problems += _check_review(lines, i)
    else:
        problems += _check_applied(lines, i)
    return sorted(problems, key=lambda p: p.line)


def _check_review(lines: list[str], i: int) -> list[Problem]:
    problems: list[Problem] = []
    header = lines[i] if i < len(lines) else ""
    if not REVIEW_HEADER_RE.match(header):
        problems.append(Problem(i + 1, "header",
                                "expected '## Fix before merge' or '## Safe to merge'"))
    stats, stats_problem = _parse_review_stats(lines, i + 1)
    if stats_problem:
        problems.append(stats_problem)

    rest_start = i + 2
    if stats is not None and stats.findings == 0:
        for n in range(rest_start, len(lines)):
            if lines[n].strip():
                problems.append(Problem(n + 1, "zero-extra",
                                        "a review with 0 findings has nothing after the stats line"))
                break
        if REVIEW_HEADER_RE.match(header) and header != "## Safe to merge":
            problems.append(Problem(i + 1, "verdict", "a review with 0 findings is '## Safe to merge'"))
        return problems

    findings: list[tuple[int, int, int]] = []  # (line, number, score)
    for kind, start, block in _sequence(lines, rest_start, problems):
        if kind == "finding":
            parsed = _check_review_finding(start, block, problems)
            if parsed is not None:
                findings.append(parsed)

    for position, (line, number, _score) in enumerate(findings, start=1):
        if number != position:
            problems.append(Problem(line, "numbering", f"expected finding number {position}, found {number}"))
            break
    for (line, _n, score), (_l, _n2, previous) in zip(findings[1:], findings):
        if score > previous:
            problems.append(Problem(line, "order", "findings must be ordered by score, highest first"))
            break

    top = max((score for _l, _n, score in findings), default=0)
    if stats is not None:
        if stats.findings != len(findings):
            problems.append(Problem(i + 2, "stats-count",
                                    f"the stats line says {stats.findings} findings but the review has {len(findings)}"))
        elif stats.confirmed is not None and stats.confirmed > stats.findings:
            problems.append(Problem(i + 2, "stats-count",
                                    "the confirmed count cannot exceed the number of findings"))
        if findings and stats.top != top:
            problems.append(Problem(i + 2, "stats-top", f"top impact must be {top}/5, the highest score"))
    if findings and REVIEW_HEADER_RE.match(header):
        expected = "## Fix before merge" if top >= 3 else "## Safe to merge"
        if header != expected:
            problems.append(Problem(i + 1, "verdict",
                                    f"with a top score of {top}/5 the verdict is '{expected[3:]}'"))
    return problems


def split_blocks(lines: list[str], start: int) -> list[tuple[int, list[str]]]:
    """Split lines into blocks separated by blank lines outside code fences.

    Returns (0-based index of the block's first line, the block's lines)."""
    blocks: list[tuple[int, list[str]]] = []
    current: list[str] = []
    current_start = start
    kinds = _fence_kinds(lines[start:])
    for offset, line in enumerate(lines[start:]):
        n = start + offset
        if kinds[offset] == "text" and not line.strip():
            if current:
                blocks.append((current_start, current))
                current = []
            continue
        if not current:
            current_start = n
        current.append(line)
    if current:
        blocks.append((current_start, current))
    return blocks


def _sequence(lines: list[str], start: int, problems: list[Problem]):
    """Yield ("finding", start, block) for each finding block, checking the separators."""
    previous = "header"
    blocks = split_blocks(lines, start)
    for start_index, block in blocks:
        if block == [SEPARATOR]:
            if previous == "separator":
                problems.append(Problem(start_index + 1, "separator", "two separators in a row"))
            previous = "separator"
            continue

        cleaned: list[str] = []
        kinds = _fence_kinds(block)
        for offset, line in enumerate(block):
            if kinds[offset] == "text" and line == SEPARATOR:
                problems.append(Problem(start_index + offset + 1, "separator",
                                        "a separator needs a blank line above and below it"))
                cleaned.append("")
                continue
            cleaned.append(line)
        while cleaned and cleaned[-1] == "":
            cleaned.pop()

        if previous in ("header", "finding"):
            if block[0].startswith("### "):
                where = "after the header" if previous == "header" else "between findings"
                problems.append(Problem(start_index + 1, "separator", f"expected a '---' separator {where}"))
            else:
                problems.append(Problem(start_index, "blank-line",
                                        "no blank lines inside a finding, only around separators"))
                previous = "finding"
                continue
        previous = "finding"
        yield "finding", start_index, cleaned
    if previous == "separator" and blocks:
        problems.append(Problem(blocks[-1][0] + 1, "separator", "nothing follows the last separator"))


def _check_score_color(start: int, heading: re.Match, problems: list[Problem]) -> None:
    score = int(heading.group(3))
    dot = (heading.group(2) or "").replace("\ufe0f", "")
    if dot != SCORE_DOTS[score]:
        problems.append(Problem(start + 1, "score-color",
                                f"a {score}/5 heading starts with {SCORE_DOTS[score]}: "
                                f"{SCORE_DOTS[5]} for 4 and 5, {SCORE_DOTS[3]} for 2 and 3, {SCORE_DOTS[1]} for 1"))


def _check_review_finding(start: int, block: list[str], problems: list[Problem]) -> tuple[int, int, int] | None:
    heading = HEADING_RE.match(block[0])
    if not heading:
        problems.append(Problem(start + 1, "finding-heading",
                                "expected '### <n>. <dot> [X/5] <title>'; no other sections are allowed"))
        return None
    number, score = int(heading.group(1)), int(heading.group(3))
    _check_score_color(start, heading, problems)

    def at(index: int) -> str:
        return block[index] if index < len(block) else ""

    idx = 1
    if LOCATION_RE.match(at(idx)):
        idx += 1
    else:
        problems.append(Problem(start + idx + 1, "location", "expected the defect's `path:line` under the heading"))
    impact = None
    if at(idx).startswith("**Impact:** "):
        impact = idx
        if not at(idx)[12:].strip():
            problems.append(Problem(start + idx + 1, "impact", "expected '**Impact:** <one or two sentences>'"))
        idx += 1
    if at(idx).startswith("**Needs:** "):
        idx += 1

    if at(idx).startswith("**Blocked:** "):
        if impact is None:
            problems.append(Problem(start + idx + 1, "impact",
                                    "a blocked finding has no diff to explain the problem, so it keeps "
                                    "'**Impact:** <one or two sentences>' above **Blocked:**"))
        idx += 1
        if idx < len(block):
            problems.append(Problem(start + idx + 1, "blocked-extra",
                                    "a blocked finding has no diff and no blast radius"))
        return start + 1, number, score

    if impact is not None:
        problems.append(Problem(start + impact + 1, "impact",
                                "the problem goes in the diff's 'Problem:' comments; only a blocked "
                                "finding has **Impact:**"))
    kinds = _fence_kinds(block)
    label = FIX_LABEL_RE.match(at(idx))
    if label:
        if any(int(ref) >= number for ref in re.findall(r"\d+", label.group(1) or "")):
            problems.append(Problem(start + idx + 1, "fix-label",
                                    "a fix can only build on the fix of a finding above it"))
        idx += 1
    elif idx < len(block) and kinds[idx] == "open":
        problems.append(Problem(start + idx + 1, "fix-label",
                                "put '**PROPOSED FIX:**' on the line above the diff"))
    if idx < len(block) and kinds[idx] == "open":
        close = _check_diff_fence(start, block, kinds, idx, problems)
        if close is None:
            return start + 1, number, score
        _check_diff_numbers(start, block, idx + 1, close, problems, {})
        idx = close + 1
        if at(idx) == "**Blast radius:**":
            idx += 1
            items = 0
            while idx < len(block) and block[idx].startswith("- "):
                if not REF_RE.search(block[idx]):
                    problems.append(Problem(start + idx + 1, "blast-ref",
                                            "each blast radius item needs a `file:line` reference"))
                if FILLER_RE.search(block[idx]):
                    problems.append(Problem(start + idx + 1, "blast-filler",
                                            "list only what changes, breaks or still needs work; drop items "
                                            "about what stays the same, or state the problem directly"))
                items += 1
                idx += 1
            if items == 0:
                problems.append(Problem(start + idx + 1, "blast-radius",
                                        "the blast radius needs at least one item"))
        elif idx >= len(block):
            problems.append(Problem(start + idx, "blast-radius", "expected '**Blast radius:**' after the diff"))
    elif idx >= len(block):
        problems.append(Problem(start + idx, "diff-missing",
                                "a finding needs a diff and a blast radius, or a **Blocked:** line"))
        return start + 1, number, score

    if idx < len(block):
        problems.append(Problem(start + idx + 1, "field-order",
                                "unexpected line; the order is heading, location, Impact (blocked only), "
                                "Needs, then Blocked, or PROPOSED FIX, a diff and Blast radius"))
    return start + 1, number, score


def _check_diff_fence(start: int, block: list[str], kinds: list[str], idx: int,
                      problems: list[Problem]) -> int | None:
    """Check the diff fence opening at block[idx]; return the index of its closing line."""
    if not DIFF_OPEN_RE.match(block[idx]):
        problems.append(Problem(start + idx + 1, "diff-fence", "code goes in a top-level ```diff block"))
    close = next((k for k in range(idx + 1, len(block)) if kinds[k] == "close"), None)
    if close is None:
        problems.append(Problem(start + idx + 1, "diff-fence", "the diff block is never closed"))
        return None
    if block[close].startswith(" "):
        problems.append(Problem(start + close + 1, "diff-fence",
                                "this line closes the diff early; every diff line starts with its sign "
                                "and line number, like '+18 |     return total;'"))
    return close


def _check_diff_numbers(start: int, block: list[str], first: int, close: int,
                        problems: list[Problem], offsets: dict[str | None, int]) -> None:
    """Check the numbered lines in block[first:close].

    A `-` line carries its number in the file now; context and `+` lines carry their number in
    the file after the fix. `offsets` holds, per file, the shift left by earlier hunks of the
    same fix, so a later hunk can be checked against it. Every run of `-` lines opens with an
    unnumbered 'Problem:' comment line, and every run of `+` lines with a 'Fix:' one. Every
    comment line carries its sign's square (red on `-`, green on `+`) so it stands apart from
    the code lines that share its color."""
    file: str | None = None
    header: tuple[int, int] | None = None
    old = new = None
    bar = None
    misaligned = False
    previous = None
    for k in range(first, close):
        line = block[k]
        if line.startswith("@@"):
            if old is not None:
                offsets[file] = new - old
            hunk = HUNK_RE.match(line)
            file = hunk.group(1) if hunk else None
            header = (k, int(hunk.group(2))) if hunk else None
            old = new = None
            previous = None
            continue
        comment = COMMENT_LINE_RE.match(line)
        numbered = DIFF_LINE_RE.match(line)
        if not comment and not numbered:
            problems.append(Problem(start + k + 1, "diff-numbers",
                                    "every diff line starts with its sign and line number, "
                                    "like '+18 |     return total;'"))
            return
        position = line.index("|")
        if bar is None:
            bar = position
        elif position != bar and not misaligned:
            misaligned = True
            problems.append(Problem(start + k + 1, "diff-align",
                                    "pad the line numbers so every '|' in a diff lines up"))
        if comment:
            sign = comment.group(1)
            square = COMMENT_SQUARES[sign]
            label = f"{square} " + ("Problem:" if sign == "-" else "Fix:")
            text = comment.group(3) or ""
            if square not in text:
                problems.append(Problem(start + k + 1, "diff-comment",
                                        f"a comment line on '{sign}' carries {square} right after the "
                                        f"comment syntax, like '{sign}   |     // {label} ...'"))
            elif previous != sign and label not in text:
                problems.append(Problem(start + k + 1, "diff-comment",
                                        f"the comment that opens a run of '{sign}' lines says '{label}'"))
            previous = sign
            continue
        sign, number = numbered.group(1), int(numbered.group(3))
        if sign != " " and previous != sign:
            label = f"{COMMENT_SQUARES[sign]} " + ("Problem:" if sign == "-" else "Fix:")
            problems.append(Problem(start + k + 1, "diff-comment",
                                    f"open this run of '{sign}' lines with a '{label}' comment on a line "
                                    f"with no number, like '{sign}   |     // {label} ...'"))
        previous = sign
        if old is None:
            if header is not None and header[1] != number:
                problems.append(Problem(start + header[0] + 1, "hunk-header",
                                        f"the hunk header names line {header[1]}, but its first line is {number}"))
            shift = offsets.get(file, 0)
            old, new = (number, number + shift) if sign == "-" else (number - shift, number)
        expected = old if sign == "-" else new
        if number != expected:
            problems.append(Problem(start + k + 1, "diff-numbers",
                                    f"expected line number {expected}: a '-' line keeps its number in the "
                                    "file now, context and '+' lines take their number after the fix"))
            if sign == "-":
                old = number
            else:
                old, new = old + number - new, number
        if sign != "+":
            old += 1
        if sign != "-":
            new += 1
    if old is not None:
        offsets[file] = new - old


def _check_text(lines: list[str], start: int) -> list[Problem]:
    """Dashes in prose and in newly added code, placeholders and hunk headers in diffs."""
    problems: list[Problem] = []
    segment = lines[start:]
    kinds = _fence_kinds(segment)

    def check_fence(indexes: list[int]) -> None:
        others = [segment[k] for k in indexes if not segment[k].startswith("+")]
        for k in indexes:
            line = segment[k]
            if line.startswith("@@") and not HUNK_RE.match(line):
                problems.append(Problem(start + k + 1, "hunk-header", "hunk headers are '@@ <file>:<line> @@'"))
            if not line.startswith("+"):
                continue
            if _is_placeholder(line, others):
                problems.append(Problem(start + k + 1, "placeholder",
                                        "this looks like a placeholder; a fix may only use values that exist. "
                                        "If it is real code, keep it"))
            if any(d in line and not any(d in other for other in others) for d in DASHES):
                problems.append(Problem(start + k + 1, "dash",
                                        "no new em dashes or en dashes in added code; dashes copied from "
                                        "existing code are fine"))

    fence: list[int] = []
    for k, kind in enumerate(kinds):
        if kind == "open":
            fence = []
        elif kind == "code":
            fence.append(k)
        elif kind == "close":
            check_fence(fence)
            fence = []
        elif any(d in segment[k] for d in DASHES):
            problems.append(Problem(start + k + 1, "dash", "no em dashes or en dashes"))
    if fence:
        check_fence(fence)
    return problems


def _parse_review_stats(lines: list[str], i: int) -> tuple[ReviewStats | None, Problem | None]:
    line = lines[i] if i < len(lines) else ""
    expected = ("expected '<N> findings · top impact <X>/5 · <F> files', "
                "with 'finding' and 'file' singular only for 1, and no top impact for 0 findings")
    m = REVIEW_STATS_RE.match(line)
    if not m:
        return None, Problem(i + 1, "stats", expected)
    findings, finding_word, top, files, file_word = (
        int(m.group(1)), m.group(2), m.group(3), int(m.group(4)), m.group(5))
    if (not _singular_ok(findings, finding_word, "finding")
            or not _singular_ok(files, file_word, "file")
            or (top is None) != (findings == 0)):
        return None, Problem(i + 1, "stats", expected)
    confirmed = int(m.group(7)) if m.group(7) is not None else None
    return ReviewStats(findings, int(top) if top else None, confirmed), None


def _check_applied(lines: list[str], i: int) -> list[Problem]:
    problems: list[Problem] = []
    header = lines[i] if i < len(lines) else ""
    head = APPLIED_HEADER_RE.match(header)
    if not head or not _singular_ok(int(head.group(2)), head.group(3), "fix"):
        problems.append(Problem(i + 1, "header", "expected '## Applied <A> of <M> fixes' ('fix' only for 1)"))
        head = None

    stats_line = lines[i + 1] if i + 1 < len(lines) else ""
    stats = APPLIED_STATS_RE.match(stats_line)
    if not stats or not _singular_ok(int(stats.group(1)), stats.group(2), "file"):
        problems.append(Problem(i + 2, "applied-stats",
                                "expected '<F> files edited · <S> skipped · <B> blocked · tests ran: "
                                "<X> passed, <Y> failed' or '... · tests not run: <why>'"))
        stats = None

    findings: list[tuple[int, int, str | None]] = []
    edited_paths: set[str] = set()
    for _kind, start, block in _sequence(lines, i + 2, problems):
        parsed = _check_applied_finding(start, block, problems, edited_paths)
        if parsed is not None:
            findings.append(parsed)

    for position, (line, number, _outcome) in enumerate(findings, start=1):
        if number != position:
            problems.append(Problem(line, "numbering", f"expected finding number {position}, found {number}"))
            break

    outcomes = [outcome for _l, _n, outcome in findings]
    if head:
        applied, total = int(head.group(1)), int(head.group(2))
        if applied != outcomes.count("Edited") or total != len(findings):
            problems.append(Problem(i + 1, "applied-counts",
                                    f"the header must read 'Applied {outcomes.count('Edited')} of {len(findings)}'"))
    if stats:
        files, skipped, blocked = int(stats.group(1)), int(stats.group(3)), int(stats.group(4))
        if (files != len(edited_paths) or skipped != outcomes.count("Skipped")
                or blocked != outcomes.count("Blocked")):
            problems.append(Problem(i + 2, "applied-counts",
                                    f"expected {len(edited_paths)} files edited, {outcomes.count('Skipped')} "
                                    f"skipped, {outcomes.count('Blocked')} blocked"))
    return problems


def _check_applied_finding(start: int, block: list[str], problems: list[Problem],
                           edited_paths: set[str]) -> tuple[int, int, str | None] | None:
    heading = HEADING_RE.match(block[0])
    if not heading:
        problems.append(Problem(start + 1, "finding-heading",
                                "expected '### <n>. <dot> [X/5] <title>'; no other sections are allowed"))
        return None
    number = int(heading.group(1))
    _check_score_color(start, heading, problems)
    labels = [line for line in block[1:] if OUTCOME_RE.match(line)]
    if len(labels) != 1:
        problems.append(Problem(start + 1, "outcome",
                                "each finding has exactly one of **Edited:**, **Skipped:** or **Blocked:**"))
        return start + 1, number, None

    def at(index: int) -> str:
        return block[index] if index < len(block) else ""

    first = at(1)
    if first == "**Edited:**":
        idx = 2
        items = 0
        while at(idx).startswith("- "):
            item = EDITED_ITEM_RE.match(at(idx))
            if item:
                edited_paths.add(item.group(1))
            else:
                problems.append(Problem(start + idx + 1, "edited-items",
                                        "expected '- `<path>`: <why>' or '- `<path>` (new): <why>'"))
            items += 1
            idx += 1
        if items == 0:
            problems.append(Problem(start + idx + 1, "edited-items", "list every edited file under **Edited:**"))
        kinds = _fence_kinds(block)
        if idx < len(block) and (FIX_LABEL_RE.match(block[idx]) or kinds[idx] == "open"):
            problems.append(Problem(start + idx + 1, "applied-diff",
                                    "applying inserts the review's diff exactly as shown, so the applied "
                                    "output shows no diff"))
            while idx < len(block) and block[idx] != "**Still open:**":
                idx += 1
        if at(idx) == "**Still open:**":
            idx += 1
            open_items = 0
            while at(idx).startswith("- "):
                if not REF_RE.search(at(idx)):
                    problems.append(Problem(start + idx + 1, "still-open",
                                            "each still-open item needs a `file:line` reference"))
                open_items += 1
                idx += 1
            if open_items == 0:
                problems.append(Problem(start + idx + 1, "still-open", "**Still open:** needs at least one item"))
        if idx < len(block):
            problems.append(Problem(start + idx + 1, "field-order",
                                    "unexpected line; the order is Edited items, then Still open"))
        return start + 1, number, "Edited"

    outcome = OUTCOME_RE.match(first)
    if not outcome or not first[len(outcome.group(0)):].strip():
        problems.append(Problem(start + 2, "field-order",
                                "the line under the heading is **Edited:**, **Skipped:** <why> or **Blocked:** <why>"))
        return start + 1, number, OUTCOME_RE.match(labels[0]).group(1)
    if at(2) == "**Still open:**":
        problems.append(Problem(start + 3, "still-open", "**Still open:** only follows **Edited:**"))
    elif len(block) > 2:
        problems.append(Problem(start + 3, "field-order", "a skipped or blocked finding is a single line"))
    return start + 1, number, outcome.group(1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check an ARCR output against its contract.")
    parser.add_argument("file", help="the output to check, or - for stdin")
    parser.add_argument("--mode", choices=["auto", "review", "applied"], default="auto")
    args = parser.parse_args(argv)

    if args.file == "-":
        text = sys.stdin.read()
    else:
        with open(args.file, encoding="utf-8") as handle:
            text = handle.read()

    problems = check(text, args.mode)
    if not problems:
        print("OK")
        return 0
    for problem in problems:
        print(f"line {problem.line}: [{problem.rule}] {problem.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
