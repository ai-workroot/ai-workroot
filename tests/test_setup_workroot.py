from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SetupWorkrootTest(unittest.TestCase):
    def test_guided_setup_writes_identity_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/setup_workroot.py",
                    "--subject",
                    "This Workroot represents a personal AI Workroot.",
                    "--ai-role",
                    "Long-term thinking and execution partner.",
                    "--direction",
                    "Plan meaningful work and preserve reusable knowledge.",
                    "--values",
                    "Stay human-centered, practical, and kind.",
                    "--force",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Help me start my first real task", result.stdout)
            profile = (work / "space/profile/profile.md").read_text(encoding="utf-8")
            self.assertIn("personal AI Workroot", profile)
            self.assertIn("Long-term thinking and execution partner", profile)
            current = (work / ".workroot/runtime/context/current.md").read_text(encoding="utf-8")
            self.assertIn("Initialized at", current)
            continue_view = (work / "space/work/continue.md").read_text(encoding="utf-8")
            self.assertIn("Start the first real task", continue_view)

    def test_guided_setup_refuses_to_overwrite_custom_profile_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            profile = work / "space/profile/profile.md"
            profile.write_text("# Profile\n\nCustomized identity.\n", encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/setup_workroot.py",
                    "--subject",
                    "Subject",
                    "--ai-role",
                    "AI role",
                    "--direction",
                    "Direction",
                    "--values",
                    "Values",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already appears customized", result.stderr)


if __name__ == "__main__":
    unittest.main()
