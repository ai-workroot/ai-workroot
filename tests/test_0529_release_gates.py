from __future__ import annotations

import ast
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.validate_kernel import validate_0529_specs, validate_release_surface


ROOT = Path(__file__).resolve().parents[1]


class ReleaseGates0529Test(unittest.TestCase):
    def test_install_and_bootstrap_scripts_exist(self) -> None:
        expected = [
            ROOT / "scripts/install.sh",
            ROOT / "scripts/install.ps1",
            ROOT / "scripts/bootstrap-dev.sh",
            ROOT / "scripts/bootstrap-dev.ps1",
        ]

        for path in expected:
            self.assertTrue(path.exists(), f"missing script: {path}")

    def test_install_script_help_and_dry_run_do_not_write_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "bin"
            env = {**os.environ, "AI_WORKROOT_INSTALL_DIR": str(install_dir)}

            help_result = subprocess.run(
                [str(ROOT / "scripts/install.sh"), "--help"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            dry_run_result = subprocess.run(
                [str(ROOT / "scripts/install.sh"), "--dry-run"],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn("CLI wrapper installer", help_result.stdout)
            self.assertEqual(dry_run_result.returncode, 0, dry_run_result.stderr)
            self.assertIn("would install", dry_run_result.stdout)
            self.assertFalse((install_dir / "workroot").exists())

    def test_local_bootstrap_state_is_ignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".ai-workroot-local/", gitignore.splitlines())

    def test_windows_powershell_validation_gap_is_documented(self) -> None:
        checklist = (ROOT / "docs/release-checklist.md").read_text(encoding="utf-8")

        self.assertIn("Windows PowerShell parse validation is pending", checklist)
        self.assertIn("scripts/install.ps1", checklist)
        self.assertIn("scripts/bootstrap-dev.ps1", checklist)

    def test_rebuild_sqlite_is_marked_as_legacy_seed_tooling(self) -> None:
        script = (ROOT / "scripts/rebuild_sqlite.py").read_text(encoding="utf-8")
        instantiate = (ROOT / "docs/instantiate-workroot.md").read_text(encoding="utf-8")

        self.assertIn("Legacy public-seed SQLite rebuild tool", script)
        self.assertIn("legacy public seed", instantiate)
        self.assertNotIn("Clean Mode users should run `python3 scripts/rebuild_sqlite.py`", instantiate)

    def test_release_notes_include_known_limitations(self) -> None:
        release_notes = (ROOT / "docs/releases/0.9.529.md").read_text(encoding="utf-8")

        for text in (
            "Windows PowerShell parse validation is pending",
            "install.sh is a CLI wrapper installer",
            "Quality Mode is currently labeled as quality-budget-expansion",
            "scripts/rebuild_sqlite.py remains legacy public-seed tooling",
        ):
            self.assertIn(text, release_notes)

    def test_numbered_0529_specs_exist(self) -> None:
        errors: list[str] = []

        validate_0529_specs(ROOT, errors)

        self.assertEqual(errors, [])

    def test_context_amendment_release_gate_requirements_are_present(self) -> None:
        errors: list[str] = []

        validate_0529_specs(ROOT, errors)

        self.assertEqual(errors, [])
        spec = (ROOT / "docs/specs/015-context-guide-modes-budgets-and-confidence.spec.md").read_text(encoding="utf-8")
        checklist = (ROOT / "docs/release-checklist.md").read_text(encoding="utf-8")
        context_source = (ROOT / "scripts/workroot_context.py").read_text(encoding="utf-8")

        self.assertIn("runtime-hints.json", spec)
        self.assertIn("Deep Mode requires explicit request", checklist)
        self.assertIn("Context Package includes mode, confidence, latency, token usage", checklist)
        self.assertIn("DEFAULT_CONTEXT_GUIDE_CONFIG", context_source)

    def test_release_validation_rejects_generated_state_and_cache_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = [
                root / "cache/generated.txt",
                root / "global-cache/generated.txt",
                root / ".ai-workroot-local/context-packages/latest.md",
                root / "context/debug/latest.json",
                root / "workroot.sqlite",
            ]
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("generated", encoding="utf-8")
            errors: list[str] = []

            validate_release_surface(root, errors)

            text = "\n".join(errors)
            self.assertIn("generated managed state path must not be committed for release: cache/generated.txt", text)
            self.assertIn(
                "generated managed state path must not be committed for release: global-cache/generated.txt",
                text,
            )
            self.assertIn(
                "generated managed state path must not be committed for release: .ai-workroot-local/context-packages/latest.md",
                text,
            )
            self.assertIn("generated managed state path must not be committed for release: context/debug/latest.json", text)
            self.assertIn("generated store must not be committed for release: workroot.sqlite", text)

    def test_release_validation_ignores_gitignored_local_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / ".gitignore").write_text(".idea/\n", encoding="utf-8")
            idea_file = root / ".idea/workspace.xml"
            idea_file.parent.mkdir(parents=True)
            idea_file.write_text("<project />\n", encoding="utf-8")
            errors: list[str] = []

            validate_release_surface(root, errors)

            self.assertEqual(errors, [])

    def test_release_validation_rejects_unignored_local_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            idea_file = root / ".idea/workspace.xml"
            idea_file.parent.mkdir(parents=True)
            idea_file.write_text("<project />\n", encoding="utf-8")
            errors: list[str] = []

            validate_release_surface(root, errors)

            text = "\n".join(errors)
            self.assertIn("local metadata must not be committed: .idea", text)
            self.assertIn("local metadata must not be committed: .idea/workspace.xml", text)

    def test_p0_code_paths_do_not_require_vector_or_remote_embeddings(self) -> None:
        p0_files = [
            "scripts/workroot_bootstrap.py",
            "scripts/workroot_candidates.py",
            "scripts/workroot_cli.py",
            "scripts/workroot_context.py",
            "scripts/workroot_doctor.py",
            "scripts/workroot_indexing.py",
            "scripts/workroot_migrations.py",
            "scripts/workroot_paths.py",
            "scripts/workroot_sqlite.py",
            "scripts/workroot_state.py",
        ]
        forbidden_import_roots = {"openai", "requests", "httpx", "chromadb", "faiss"}
        forbidden_calls = {"Embedding", "embeddings"}

        for rel in p0_files:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported = {alias.name.split(".")[0] for alias in node.names}
                    self.assertFalse(imported & forbidden_import_roots, f"{rel} imports {imported}")
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotIn(node.module.split(".")[0], forbidden_import_roots, rel)
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, forbidden_calls, rel)

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
