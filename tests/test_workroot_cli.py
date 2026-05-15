from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkrootCliTest(unittest.TestCase):
    def test_cli_creates_l1_task(self) -> None:
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
                    "scripts/workroot_cli.py",
                    "task",
                    "create",
                    "CLI task",
                    "--id",
                    "task-cli",
                    "--process-level",
                    "L1",
                    "--created-at",
                    "2026-05-15T00:00:00Z",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(".workroot/runtime/work/tasks/task-cli", result.stdout)
            self.assertTrue((work / ".workroot/runtime/work/tasks/task-cli/plans").is_dir())

    def test_cli_adds_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            shutil.copytree(
                ROOT,
                work,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            create = subprocess.run(
                [
                    sys.executable,
                    "scripts/workroot_cli.py",
                    "task",
                    "create",
                    "CLI task",
                    "--id",
                    "task-cli",
                    "--process-level",
                    "L1",
                    "--created-at",
                    "2026-05-15T00:00:00Z",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(create.returncode, 0, create.stderr)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/workroot_cli.py",
                    "run",
                    "add",
                    "--task-id",
                    "task-cli",
                    "--run-id",
                    "run-cli",
                    "--title",
                    "CLI run",
                    "--status",
                    "completed",
                    "--started-at",
                    "2026-05-15T00:01:00Z",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("run-cli", result.stdout)
            self.assertTrue((work / ".workroot/runtime/work/tasks/task-cli/runs/run-cli.md").exists())


if __name__ == "__main__":
    unittest.main()
