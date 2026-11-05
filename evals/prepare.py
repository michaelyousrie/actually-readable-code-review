#!/usr/bin/env python3
"""Build an eval checkout whose uncommitted changes reintroduce a real bug.

Usage: prepare.py CASE.json WORKDIR
The checkout at WORKDIR/<id> is a fresh repo with one commit, "baseline", and no remote, so
its history does not name the fix. The baseline is the fix commit's parent with the fix
applied to the reverted files only, so tests the fix added are absent. The working tree then
holds the parent's version of those files: the bug, as uncommitted changes. Without
"revert_paths", every file the fix changed is reverted.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IDENTITY = ["-c", "user.name=eval", "-c", "user.email=eval@example.com"]


def _git(*args: str, cwd: Path | None = None, stdin: str | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, input=stdin, check=True,
                            capture_output=True, text=True)
    return result.stdout


def _exists(clone: Path, revision: str, path: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{revision}:{path}"], cwd=clone,
                          capture_output=True).returncode == 0


def prepare(case: dict, workdir: Path) -> Path:
    """Return the checkout path whose uncommitted changes reintroduce the case's bug."""
    target = Path(workdir) / case["id"]
    if target.exists():
        raise FileExistsError(f"{target} already exists; delete it first")
    target.parent.mkdir(parents=True, exist_ok=True)
    sha = case["fix_commit"]
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        _git("clone", "--quiet", case["repo"], str(clone))
        paths = case.get("revert_paths") or _git("diff", "--name-only", f"{sha}^", sha, cwd=clone).split()
        _git("checkout", "--quiet", f"{sha}^", cwd=clone)
        for path in paths:
            if _exists(clone, sha, path):
                _git("checkout", sha, "--", path, cwd=clone)
            else:
                (clone / path).unlink(missing_ok=True)
        shutil.copytree(clone, target, ignore=shutil.ignore_patterns(".git"))
        _git("init", "-q", cwd=target)
        _git("add", "-A", cwd=target)
        _git(*IDENTITY, "commit", "-q", "-m", "baseline", cwd=target)
        for path in paths:
            destination = target / path
            if _exists(clone, f"{sha}^", path):
                content = subprocess.run(["git", "show", f"{sha}^:{path}"], cwd=clone,
                                         check=True, capture_output=True).stdout
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
            else:
                destination.unlink(missing_ok=True)
    return target


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: prepare.py CASE.json WORKDIR", file=sys.stderr)
        return 2
    case = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    path = prepare(case, Path(args[1])).resolve()
    print(path)
    print(f"Use actually-readable-code-review on the uncommitted changes in {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
