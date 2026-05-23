from __future__ import annotations

import re
import unittest
from pathlib import Path

from ai_workroot.runtime.release_validation import is_git_ignored

from tests.contracts.helpers import FORBIDDEN_TEXT_PATTERNS, ROOT, TEXT_SUFFIXES


class RepositoryRootContractTest(unittest.TestCase):
    def test_clean_workroot_root_surface(self) -> None:
        allowed = {
            ".github",
            ".gitignore",
            "AUTHOR.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "DCO.md",
            "LICENSE",
            "NOTICE",
            "PROJECT_BRIEF.md",
            "pyproject.toml",
            "README.md",
            "ROADMAP.md",
            "START_HERE_FOR_HUMANS.md",
            "TRADEMARKS.md",
            "assets",
            "docs",
            "install",
            "scripts",
            "src",
            "tests",
            "workroot.project.json",
        }
        present = {path.name for path in ROOT.iterdir() if path.name != ".git" and not is_git_ignored(ROOT, path)}
        self.assertEqual(present - allowed, set())
        self.assertFalse({"AGENTS.md", "CLAUDE.md", "space", ".workroot"} & present)

    def test_no_stale_public_text_patterns(self) -> None:
        hits: list[str] = []
        for path in ROOT.rglob("*"):
            if (
                ".git" in path.parts
                or ".venv" in path.parts
                or not path.is_file()
                or path.suffix.lower() not in TEXT_SUFFIXES
            ):
                continue
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_TEXT_PATTERNS:
                if pattern in text:
                    hits.append(f"{path.relative_to(ROOT).as_posix()}: {pattern}")
        self.assertEqual(hits, [])

    def test_test_like_python_files_are_under_tests(self) -> None:
        pattern = re.compile(r"(^|/)test_.*\.py$|(^|/).*_test\.py$")
        test_like_paths: list[str] = []
        for path in ROOT.rglob("*.py"):
            rel = path.relative_to(ROOT).as_posix()
            if rel.startswith(".git/") or rel.startswith(".venv/") or "__pycache__/" in rel:
                continue
            if pattern.search(rel) and not rel.startswith("tests/"):
                test_like_paths.append(rel)

        self.assertEqual(test_like_paths, [])


if __name__ == "__main__":
    unittest.main()
