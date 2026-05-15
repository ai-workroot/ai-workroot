from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".json", ".csv", ".py", ".yml", ".yaml", ".txt", ".sql"}
NOVICE_INTERNAL_TERMS = [
    ".workroot",
    "kernel",
    "registry",
    "schema",
    "runtime",
]
FORBIDDEN_TEXT_PATTERNS = [
    ".".join(["0", "9", "0"]),
    "v" + ".".join(["0", "9", "0"]),
    "Un" + "released",
    "actor" + "_" + "registry",
    "owner" + "_" + "id",
    "parent" + "_" + "task" + "_" + "id",
    "migrate" + "_" + "workroot",
    "validate" + "_" + "workroot",
    "migration" + "_" + "registry",
    "migration" + "-" + "policy",
]


class PublicSeedSurfaceTest(unittest.TestCase):
    def test_public_seed_root_surface(self) -> None:
        allowed = {
            ".github",
            ".gitignore",
            ".workroot",
            "AGENTS.md",
            "AUTHOR.md",
            "CHANGELOG.md",
            "CLAUDE.md",
            "CONTRIBUTING.md",
            "DCO.md",
            "LICENSE",
            "NOTICE",
            "PROJECT_BRIEF.md",
            "README.md",
            "ROADMAP.md",
            "START_HERE_FOR_HUMANS.md",
            "TRADEMARKS.md",
            "assets",
            "docs",
            "scripts",
            "space",
            "tests",
        }
        present = {path.name for path in ROOT.iterdir() if path.name != ".git"}
        self.assertEqual(present - allowed, set())

    def test_release_validation(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate_kernel.py", "--release"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_public_seed_does_not_use_status_task_directories(self) -> None:
        self.assertFalse((ROOT / ".workroot/runtime/work/active").exists())
        self.assertFalse((ROOT / ".workroot/runtime/work/closed").exists())
        self.assertTrue((ROOT / ".workroot/runtime/work/tasks").is_dir())

    def test_no_stale_public_text_patterns(self) -> None:
        hits: list[str] = []
        for path in ROOT.rglob("*"):
            if ".git" in path.parts or not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if path == Path(__file__):
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_TEXT_PATTERNS:
                if pattern in text:
                    hits.append(f"{path.relative_to(ROOT).as_posix()}: {pattern}")
        self.assertEqual(hits, [])

    def test_human_entry_starts_with_one_sentence_path(self) -> None:
        first_sentence = "I want this workspace to help me with [area]. Please set it up with me, then help me start my first real task."
        for rel in ("README.md", "START_HERE_FOR_HUMANS.md"):
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                position = text.find(first_sentence)
                self.assertGreaterEqual(position, 0)
                self.assertLess(position, 700)

    def test_human_entry_does_not_expose_registry_paths(self) -> None:
        for rel in ("README.md", "START_HERE_FOR_HUMANS.md"):
            with self.subTest(rel=rel):
                text = (ROOT / rel).read_text(encoding="utf-8")
                self.assertNotIn(".workroot/runtime/index", text)
                self.assertNotIn("link_registry.csv", text)

    def test_start_here_first_screen_is_novice_safe(self) -> None:
        text = (ROOT / "START_HERE_FOR_HUMANS.md").read_text(encoding="utf-8")[:1500].lower()
        for term in NOVICE_INTERNAL_TERMS:
            with self.subTest(term=term):
                self.assertNotIn(term, text)

    def test_user_visible_work_files_do_not_expose_internal_terms(self) -> None:
        hits: list[str] = []
        for path in (ROOT / "space/work").rglob("*.md"):
            text = path.read_text(encoding="utf-8").lower()
            for term in NOVICE_INTERNAL_TERMS:
                if term in text:
                    hits.append(f"{path.relative_to(ROOT).as_posix()}: {term}")
        self.assertEqual(hits, [])

    def test_novice_task_language_exists(self) -> None:
        combined = "\n".join(
            (ROOT / rel).read_text(encoding="utf-8")
            for rel in (
                "README.md",
                "START_HERE_FOR_HUMANS.md",
                "docs/user-sop.md",
                "docs/user-interaction-contract.md",
            )
        )
        self.assertIn("A task is just the thing you are working on now.", combined)
        self.assertIn("Help me continue.", combined)
        self.assertIn("This task is finished. Save what matters and help me start a new task.", combined)
        self.assertIn("What tasks have I done before?", combined)
        self.assertIn("answer in the language", combined)


if __name__ == "__main__":
    unittest.main()
