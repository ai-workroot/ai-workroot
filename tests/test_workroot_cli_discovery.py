from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


def run_cli(*args: str) -> str:
    result = subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


class WorkrootCliDiscoveryTest(unittest.TestCase):
    def test_quickstart_mentions_happy_path(self) -> None:
        out = run_cli("quickstart")
        self.assertIn("task complete", out)
        self.assertIn("continue rebuild", out)
        self.assertIn("schema", out)

    def test_schema_lists_enums_and_path_rules(self) -> None:
        out = run_cli("schema")
        self.assertIn("manual_check", out)
        self.assertIn("model_generation", out)
        self.assertIn("artifact audiences", out)
        self.assertIn("source_paths", out)
        self.assertIn("input_ref", out)

    def test_recipe_task_l2_evidence(self) -> None:
        out = run_cli("recipe", "task-l2-evidence")
        self.assertIn("task complete", out)
        self.assertIn("--process-level L2", out)
        self.assertIn("--checkpoint", out)

    def test_doctor_runs_kernel_validation(self) -> None:
        out = run_cli("doctor")
        self.assertIn("AI Workroot kernel validation passed.", out)


if __name__ == "__main__":
    unittest.main()
