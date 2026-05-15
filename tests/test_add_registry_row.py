from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AddRegistryRowTest(unittest.TestCase):
    def test_adds_run_registry_row(self) -> None:
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
                    "scripts/add_registry_row.py",
                    "run",
                    "run_id=run-test",
                    "task_id=task-test",
                    "title=Test run",
                    "status=completed",
                    "started_at=2026-05-15T00:00:00Z",
                    "updated_at=2026-05-15T00:00:00Z",
                ],
                cwd=work,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("added run", result.stdout)
            self.assertIn(
                "run-test",
                (work / ".workroot/runtime/index/run_registry.csv").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
