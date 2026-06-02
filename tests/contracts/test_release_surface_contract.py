from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workroot.diagnostics.release_validation import validate_release_surface


class ReleaseSurfaceContractTest(unittest.TestCase):
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
            self.assertIn(
                "generated managed state path must not be committed for release: context/debug/latest.json", text
            )
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

    def test_release_validation_uses_git_file_lists_not_per_path_ignore_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            (root / ".gitignore").write_text("__pycache__/\n.idea/\n", encoding="utf-8")
            (root / "README.md").write_text("release surface\n", encoding="utf-8")
            subprocess.run(["git", "add", ".gitignore", "README.md"], cwd=root, check=True, capture_output=True)
            for index in range(50):
                path = root / "__pycache__" / f"ignored-{index}.pyc"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"ignored")
            errors: list[str] = []

            with patch(
                "ai_workroot.diagnostics.release_validation.is_git_ignored",
                side_effect=AssertionError("per-path check-ignore used"),
            ):
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

    def test_release_validation_ignores_token_variable_control_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "src/example.py"
            source.parent.mkdir(parents=True)
            source.write_text(
                "def collect(values):\n"
                "    for token in values:\n"
                "        if not token:\n"
                "            continue\n"
                "        yield token\n",
                encoding="utf-8",
            )
            errors: list[str] = []

            validate_release_surface(root, errors)

            self.assertEqual(errors, [])

    def test_release_validation_rejects_secret_like_key_assignments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_file = root / "config.yaml"
            secret_file.write_text("token: secret-value\n", encoding="utf-8")
            errors: list[str] = []

            validate_release_surface(root, errors)

            self.assertIn("possible private residue in config.yaml", "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
