from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class WorkrootBootstrapDevTest(unittest.TestCase):
    def run_cli(self, cwd: Path, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(cwd / "scripts/workroot_cli.py"), *args],
            cwd=cwd,
            env={**os.environ, **env},
            text=True,
            capture_output=True,
            check=False,
        )

    def copy_repo(self, dst: Path) -> None:
        shutil.copytree(
            ROOT,
            dst,
            ignore=shutil.ignore_patterns(".git", ".idea", "__pycache__", "*.pyc"),
        )

    def test_bootstrap_dev_dry_run_rejects_non_workroot_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self.copy_repo(repo)
            (repo / "PROJECT_BRIEF.md").unlink()
            result = self.run_cli(repo, {"AI_WORKROOT_HOME": str(Path(tmp) / "home")}, "bootstrap-dev", "--dry-run")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("AI Workroot repository", result.stderr)

    def test_bootstrap_dev_dry_run_accepts_repo_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self.copy_repo(repo)
            result = self.run_cli(repo, {"AI_WORKROOT_HOME": str(Path(tmp) / "home")}, "bootstrap-dev", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("bootstrap-dev preflight ok", result.stdout)
            self.assertFalse((repo / ".ai-workroot-local").exists())

    def test_bootstrap_dev_initializes_context_and_doctor_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.copy_repo(repo)
            env = {"AI_WORKROOT_HOME": str(home)}

            bootstrap = self.run_cli(repo, env, "bootstrap-dev")
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            self.assertTrue((home / "workroots/wr_repo/cache/workroot.sqlite").exists())

            context = self.run_cli(repo, env, "context", "--agent", "codex", "--cwd", str(repo))
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("# AI Workroot Context Package", context.stdout)

            doctor = self.run_cli(repo, env, "doctor", "--cwd", str(repo))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("AI Workroot doctor: PASS", doctor.stdout)


if __name__ == "__main__":
    unittest.main()
