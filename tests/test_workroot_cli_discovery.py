from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_package_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ai_workroot", *args],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=False,
    )


class WorkrootCliDiscoveryTest(unittest.TestCase):
    def test_package_default_help_shows_only_clean_workroot_commands(self) -> None:
        result = run_package_cli("--help")

        self.assertEqual(result.returncode, 0, result.stderr)
        for command in ("init", "list", "status", "context", "doctor", "bootstrap-dev"):
            self.assertIn(command, result.stdout)
        self.assertNotIn("legacy", result.stdout)
        self.assertNotIn("public-seed", result.stdout.lower())
        self.assertNotIn("==SUPPRESS==", result.stdout)

    def test_package_cli_rejects_legacy_namespace(self) -> None:
        result = run_package_cli("legacy", "--help")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)
        self.assertIn("legacy", result.stderr)

    def test_package_cli_version_remains_current_release_without_branch_bump(self) -> None:
        result = run_package_cli("--version")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AI Workroot 0.9.530", result.stdout)


if __name__ == "__main__":
    unittest.main()
