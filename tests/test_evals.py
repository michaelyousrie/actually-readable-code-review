import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "evals"))

import prepare  # noqa: E402
import score  # noqa: E402

REVIEW = (ROOT / "tests" / "fixtures" / "review_valid.md").read_text(encoding="utf-8")
STATS = "3 findings · top impact 4/5 · 5 files"


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.email=eval@example.com", "-c", "user.name=eval", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )
    return result.stdout


def case(**overrides):
    base = {
        "id": "coupons",
        "repo": "unused",
        "fix_commit": "0" * 40,
        "summary": "coupons were applied to the original price",
        "expect": {"path": "src/cart/applyDiscounts.ts", "line_min": 10, "line_max": 30, "min_score": 3},
    }
    base.update(overrides)
    return base


class PrepareTests(unittest.TestCase):
    def test_prepare_reintroduces_bug(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            git(source, "init", "-q")
            (source / "calc.py").write_text("def total(a, b):\n    return a - b\n", encoding="utf-8")
            git(source, "add", "calc.py")
            git(source, "commit", "-q", "-m", "add total")
            (source / "calc.py").write_text("def total(a, b):\n    return a + b\n", encoding="utf-8")
            git(source, "commit", "-q", "-am", "fix total subtracting instead of adding")
            sha = git(source, "rev-parse", "HEAD").strip()

            path = prepare.prepare(case(id="calc", repo=str(source), fix_commit=sha), Path(tmp) / "work")

            diff = git(path, "diff", "HEAD")
            self.assertIn("-    return a + b", diff)
            self.assertIn("+    return a - b", diff)


    def test_prepare_reverts_only_listed_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            git(source, "init", "-q")
            (source / "calc.py").write_text("def total(a, b):\n    return a - b\n", encoding="utf-8")
            git(source, "add", "calc.py")
            git(source, "commit", "-q", "-m", "add total")
            (source / "calc.py").write_text("def total(a, b):\n    return a + b\n", encoding="utf-8")
            (source / "test_calc.py").write_text("assert total(1, 2) == 3\n", encoding="utf-8")
            git(source, "add", "calc.py", "test_calc.py")
            git(source, "commit", "-q", "-m", "fix total and add a test")
            sha = git(source, "rev-parse", "HEAD").strip()

            listed = case(id="calc", repo=str(source), fix_commit=sha, revert_paths=["calc.py"])
            path = prepare.prepare(listed, Path(tmp) / "work")

            self.assertEqual(git(path, "diff", "HEAD", "--name-only").split(), ["calc.py"])
            self.assertFalse((path / "test_calc.py").exists())

    def test_prepare_hides_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            source.mkdir()
            git(source, "init", "-q")
            (source / "calc.py").write_text("def total(a, b):\n    return a - b\n", encoding="utf-8")
            git(source, "add", "calc.py")
            git(source, "commit", "-q", "-m", "add total")
            (source / "calc.py").write_text("def total(a, b):\n    return a + b\n", encoding="utf-8")
            git(source, "commit", "-q", "-am", "fix total subtracting instead of adding")
            sha = git(source, "rev-parse", "HEAD").strip()

            path = prepare.prepare(case(id="calc", repo=str(source), fix_commit=sha), Path(tmp) / "work")

            self.assertEqual(git(path, "log", "--format=%s").split("\n")[:-1], ["baseline"])
            self.assertEqual(git(path, "remote").strip(), "")


class ScoreTests(unittest.TestCase):
    def test_score_pass(self):
        self.assertEqual(score.score(case(), REVIEW), (True, []))

    def test_score_wrong_location(self):
        expect = {"path": "src/other.ts", "line_min": 10, "line_max": 30, "min_score": 3}
        passed, reasons = score.score(case(expect=expect), REVIEW)
        self.assertFalse(passed)
        self.assertTrue(reasons)

    def test_score_low_score(self):
        expect = {"path": "src/cart/applyDiscounts.ts", "line_min": 10, "line_max": 30, "min_score": 5}
        passed, reasons = score.score(case(expect=expect), REVIEW)
        self.assertFalse(passed)
        self.assertTrue(reasons)

    def test_score_invalid_format(self):
        passed, reasons = score.score(case(), "```markdown\n" + REVIEW + "```\n")
        self.assertFalse(passed)
        self.assertTrue(any("format" in reason for reason in reasons))

    def test_score_reformat_false_finding_present(self):
        reformat = {"source_review": "reformat/coupons.md",
                    "false_finding": {"path": "src/sync/pushOrders.ts", "line": 42}}
        output = REVIEW.replace(STATS, STATS + " · from CodeRabbit: 2 confirmed, 1 dropped")
        passed, reasons = score.score(case(reformat=reformat), output, reformat=True)
        self.assertFalse(passed)
        self.assertTrue(any("false finding" in reason for reason in reasons))

    def test_score_reformat_pass(self):
        reformat = {"source_review": "reformat/coupons.md",
                    "false_finding": {"path": "src/billing/invoice.ts", "line": 7}}
        output = REVIEW.replace(STATS, STATS + " · from CodeRabbit: 2 confirmed, 1 dropped")
        self.assertEqual(score.score(case(reformat=reformat), output, reformat=True), (True, []))

    def test_score_reformat_nothing_dropped(self):
        reformat = {"source_review": "reformat/coupons.md",
                    "false_finding": {"path": "src/billing/invoice.ts", "line": 7}}
        output = REVIEW.replace(STATS, STATS + " · from CodeRabbit: 2 confirmed, 0 dropped")
        passed, reasons = score.score(case(reformat=reformat), output, reformat=True)
        self.assertFalse(passed)


if __name__ == "__main__":
    unittest.main()
