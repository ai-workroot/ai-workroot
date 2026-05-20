from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CleanReleaseValidatorSmokeTest(unittest.TestCase):
    def test_doctor_release_reports_clean_workroot_release_checks(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "ai_workroot", "doctor", "--release"],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AI Workroot release doctor: PASS", result.stdout)
        self.assertIn("import boundaries", result.stdout)
        self.assertIn("Native Agent Entry templates", result.stdout)
        self.assertIn("Release Control protection", result.stdout)
        self.assertIn("Public Seed quarantine", result.stdout)

    def test_validate_release_script_runs_clean_release_validator(self) -> None:
        result = subprocess.run(
            [str(ROOT / "scripts/dev/validate-release.sh")],
            cwd=ROOT,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Clean Workroot release validation passed", result.stdout)


if __name__ == "__main__":
    unittest.main()
