from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class PackageEntrypointSmokeTest(unittest.TestCase):
    def test_python_module_help_uses_clean_workroot_language(self) -> None:
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}

        result = subprocess.run(
            [sys.executable, "-m", "ai_workroot", "--help"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AI Workroot", result.stdout)
        self.assertIn("Clean Workroot", result.stdout)
        self.assertIn("init", result.stdout)
        self.assertIn("context", result.stdout)
        self.assertIn("doctor", result.stdout)
        self.assertNotIn("Public Seed", result.stdout)


if __name__ == "__main__":
    unittest.main()
