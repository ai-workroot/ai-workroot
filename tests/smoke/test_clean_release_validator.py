from __future__ import annotations

import os
import subprocess
import sys
import tempfile
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

    def test_release_doctor_fails_tracked_public_seed_root_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            subprocess.run(["git", "init"], cwd=tmp, check=True, capture_output=True)
            repo.mkdir()
            for rel in (
                "src/ai_workroot/core",
                "src/ai_workroot/contracts",
                "src/ai_workroot/runtime",
                "src/ai_workroot/storage",
                "src/ai_workroot/indexing/providers",
                "src/ai_workroot/resources/templates/native_agent_entry",
                "tests/negative",
                "install/unix",
            ):
                (repo / rel).mkdir(parents=True, exist_ok=True)
            for rel in (
                "src/ai_workroot/agent/native_entry.py",
                "tests/negative/test_release_control_protection.py",
                "install/unix/install.sh",
            ):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("", encoding="utf-8")
            (repo / "src/ai_workroot/resources/templates/native_agent_entry/AGENTS.md.template").write_text("", encoding="utf-8")
            (repo / "AGENTS.md").write_text("tracked seed entry\n", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)

            result = subprocess.run(
                [sys.executable, "-m", "ai_workroot", "doctor", "--release"],
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("tracked Public Seed root paths", result.stdout)

    def test_release_doctor_fails_unignored_generated_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            for rel in (
                "src/ai_workroot/core",
                "src/ai_workroot/contracts",
                "src/ai_workroot/runtime",
                "src/ai_workroot/storage",
                "src/ai_workroot/indexing/providers",
                "src/ai_workroot/resources/templates/native_agent_entry",
                "tests/negative",
                "install/unix",
            ):
                (repo / rel).mkdir(parents=True, exist_ok=True)
            for rel in (
                "src/ai_workroot/agent/native_entry.py",
                "tests/negative/test_release_control_protection.py",
                "install/unix/install.sh",
                "cache/generated.txt",
            ):
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text("", encoding="utf-8")
            (repo / "src/ai_workroot/resources/templates/native_agent_entry/AGENTS.md.template").write_text("", encoding="utf-8")
            subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

            result = subprocess.run(
                [sys.executable, "-m", "ai_workroot", "doctor", "--release"],
                cwd=repo,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("release surface", result.stdout)
            self.assertIn("cache/generated.txt", result.stdout)


if __name__ == "__main__":
    unittest.main()
