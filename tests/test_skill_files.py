import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "actually-readable-code-review"
sys.path.insert(0, str(SKILL_DIR / "scripts"))

import check_output  # noqa: E402

PORTABLE_KEYS = {"name", "description", "license", "metadata"}
EXAMPLE_RE = re.compile(r"<!-- example:start (review|applied) -->\n(.*?)<!-- example:end -->", re.S)
TOOL_NAMES = ["Grep", "Glob", "Bash tool", "Read tool", "Task tool", "Agent tool", "TodoWrite", "WebFetch"]
PRIVATE_IDENTIFIERS = ["contentcreator", "h3max", "registerusermedia", "minimax"]
SKIP_DIRS = {".git", "__pycache__", "work"}


def text_files(base: Path):
    for path in sorted(base.rglob("*")):
        if path.is_file() and not SKIP_DIRS.intersection(path.relative_to(ROOT).parts):
            try:
                yield path, path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue


def frontmatter() -> dict[str, str]:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    lines = text.split("\n")
    assert lines[0] == "---", "SKILL.md must start with frontmatter"
    end = lines.index("---", 1)
    keys: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.match(r"^([A-Za-z][\w-]*):\s?(.*)$", line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            keys[match.group(1)] = value
    return keys


def examples():
    files = list(SKILL_DIR.rglob("*.md"))
    if (ROOT / "README.md").exists():
        files.append(ROOT / "README.md")
    for path in files:
        for match in EXAMPLE_RE.finditer(path.read_text(encoding="utf-8")):
            yield path, match.group(1), match.group(2)


class SkillFileTests(unittest.TestCase):
    def test_frontmatter_portable_keys_only(self):
        keys = set(frontmatter())
        self.assertTrue(keys <= PORTABLE_KEYS, keys - PORTABLE_KEYS)
        self.assertTrue({"name", "description", "license"} <= keys)

    def test_name(self):
        name = frontmatter()["name"]
        self.assertEqual(name, SKILL_DIR.name)
        self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)

    def test_description(self):
        description = frontmatter()["description"]
        self.assertTrue(1 <= len(description) <= 1024, len(description))
        self.assertIn("ARCR", description)

    def test_referenced_files_exist(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        referenced = set(re.findall(r"(references/[\w-]+\.md|scripts/[\w-]+\.py)", text))
        self.assertGreaterEqual(len(referenced), 5, referenced)
        for relative in referenced:
            self.assertTrue((SKILL_DIR / relative).is_file(), relative)

    def test_examples_pass_checker(self):
        found = list(examples())
        for path, mode, body in found:
            with self.subTest(path=path.name, first_line=body.split("\n", 1)[0]):
                self.assertEqual(check_output.check(body, mode), [])
        reviews = [body for _p, mode, body in found if mode == "review"]
        self.assertTrue(any("\n0 findings" not in body for body in reviews), "need a review with findings")
        self.assertTrue(any("\n0 findings" in body for body in reviews), "need a zero-findings review")
        self.assertTrue(any(mode == "applied" for _p, mode, _b in found), "need an applied example")

    def test_no_vendor_tool_names(self):
        for path, text in text_files(SKILL_DIR):
            for name in TOOL_NAMES:
                with self.subTest(path=path.name, name=name):
                    self.assertIsNone(re.search(rf"\b{re.escape(name)}\b", text))

    def test_no_dashes_anywhere(self):
        for path, text in text_files(ROOT):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("\u2014", text)
                self.assertNotIn("\u2013", text)

    def test_no_private_identifiers(self):
        for path, text in text_files(ROOT):
            if path == Path(__file__).resolve():
                continue
            lowered = text.lower()
            for identifier in PRIVATE_IDENTIFIERS:
                with self.subTest(path=str(path.relative_to(ROOT)), identifier=identifier):
                    self.assertNotIn(identifier, lowered)


    def test_contract_rules_from_final_review(self):
        contract = " ".join((SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8").split())
        self.assertIn("Consequences of the fix go in the blast radius, not the diff.", contract)
        self.assertIn("Code in a diff is copied exactly", contract)

    def test_skill_has_checker_escape_hatch(self):
        skill = " ".join((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("Never change correct code", skill)
        self.assertIn("Stop after three rounds", skill)

    def test_override_line_only_for_review_layouts(self):
        skill = " ".join((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").split())
        contract = " ".join((SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8").split())
        for text in (skill, contract):
            self.assertIn("General response-style rules", text)
        self.assertIn("Their review rules still apply.", contract)

    def test_blast_radius_never_lists_what_stays_the_same(self):
        contract = " ".join((SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8").split())
        method = " ".join((SKILL_DIR / "references" / "review-method.md").read_text(encoding="utf-8").split())
        for text in (contract, method):
            self.assertIn("Never list what stays the same", text)

    def test_contract_has_label_numbers_and_overlap_rule(self):
        contract = " ".join((SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8").split())
        self.assertIn("**PROPOSED FIX:**", contract)
        self.assertIn("(on top of fix 1)", contract)
        self.assertIn("A `-` line keeps its number in the file now", contract)

    def test_contract_names_score_colors(self):
        contract = (SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8")
        for color in ("🔴 for 4 and 5", "🟡 for 2 and 3", "⚪ for 1"):
            self.assertIn(color, contract)

    def test_reasoning_lives_in_diff_comments(self):
        contract = " ".join((SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8").split())
        applied = " ".join((SKILL_DIR / "references" / "applied-fixes.md").read_text(encoding="utf-8").split())
        self.assertIn("`Problem:`", contract)
        self.assertIn("`Fix:`", contract)
        self.assertIn("apply 1 with comments", applied)

    def test_comment_lines_carry_colored_squares(self):
        contract = " ".join((SKILL_DIR / "references" / "output-contract.md").read_text(encoding="utf-8").split())
        applied = " ".join((SKILL_DIR / "references" / "applied-fixes.md").read_text(encoding="utf-8").split())
        self.assertIn("`- | // 🟥 Problem: ...`", contract)
        self.assertIn("`+ | // 🟩 Fix: ...`", contract)
        self.assertIn("without the 🟥 and 🟩 squares", applied)

    def test_apply_inserts_the_fix_as_is(self):
        skill = " ".join((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8").split())
        applied = " ".join((SKILL_DIR / "references" / "applied-fixes.md").read_text(encoding="utf-8").split())
        for text in (skill, applied):
            self.assertIn("exactly as shown", text)
        self.assertIn("Never run the review again", applied)
        self.assertNotIn("run it again, show it", applied)

    def test_apply_expects_line_shifts_from_earlier_fixes(self):
        applied = " ".join((SKILL_DIR / "references" / "applied-fixes.md").read_text(encoding="utf-8").split())
        self.assertIn("Find each fix by its `-` and context lines, not by its line numbers alone", applied)
        self.assertIn("That shift is not drift", applied)


if __name__ == "__main__":
    unittest.main()
