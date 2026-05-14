from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NewTaskScriptTest(unittest.TestCase):
    def test_multilingual_task_script(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/test_new_task.py"],
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
            "print(m.normalize_instant('2026-05-15T17:00:00+08:00'))"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "2026-05-15T09:00:00Z")

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


if __name__ == "__main__":
    unittest.main()
