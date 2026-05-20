from __future__ import annotations

import subprocess
import sys
import unittest
import tempfile
from pathlib import Path

from tests.fixtures.public_seed import copy_repo_with_public_seed


ROOT = Path(__file__).resolve().parents[1]


class NewTaskScriptTest(unittest.TestCase):
    def test_multilingual_task_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/new_task_smoke.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_timezone_offset_is_normalized(self) -> None:
        code = (
            "import importlib.util;"
            "spec=importlib.util.spec_from_file_location('new_task','scripts/new_task.py');"
            "m=importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(m);"
            "print(m.normalize_instant('2026-05-15T08:00:00+08:00'))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "2026-05-15T00:00:00Z")

    def test_timezone_free_instant_is_rejected(self) -> None:
        code = (
            "import importlib.util;"
            "spec=importlib.util.spec_from_file_location('new_task','scripts/new_task.py');"
            "m=importlib.util.module_from_spec(spec);"
            "spec.loader.exec_module(m);"
            "m.normalize_instant('2026-05-15T17:00:00')"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timezone is required", result.stderr)

    def test_new_task_cli_creates_l1_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/new_task.py",
                    "Process task",
                    "--id",
                    "task-process-cli",
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
            task_dir = work / ".workroot/runtime/work/tasks/task-process-cli"
            self.assertTrue((task_dir / "plans").is_dir())
            self.assertTrue((task_dir / "retrieval_cards").is_dir())
            self.assertFalse((task_dir / "actions").exists())

    def test_new_task_cli_creates_l2_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "workroot"
            copy_repo_with_public_seed(work)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/new_task.py",
                    "Evidence task",
                    "--id",
                    "task-evidence-cli",
                    "--process-level",
                    "L2",
                    "--created-at",
                    "2026-05-15T00:00:00Z",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            task_dir = work / ".workroot/runtime/work/tasks/task-evidence-cli"
            self.assertTrue((task_dir / "actions").is_dir())
            self.assertTrue((task_dir / "recipes").is_dir())
            self.assertTrue((task_dir / "validation").is_dir())
            self.assertFalse((task_dir / "artifacts").exists())


if __name__ == "__main__":
    unittest.main()
