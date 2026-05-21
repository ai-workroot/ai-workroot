from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tests.fixtures.public_seed import copy_repo_with_public_seed


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
        copy_repo_with_public_seed(dst, include_agent_entries=True)

    def test_bootstrap_dev_dry_run_rejects_non_workroot_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self.copy_repo(repo)
            (repo / "workroot.project.json").unlink()
            result = self.run_cli(repo, {"AI_WORKROOT_HOME": str(Path(tmp) / "home")}, "bootstrap-dev", "--dry-run")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("workroot.project.json", result.stderr)

    def test_bootstrap_dev_dry_run_accepts_repo_without_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            self.copy_repo(repo)
            result = self.run_cli(repo, {"AI_WORKROOT_HOME": str(Path(tmp) / "home")}, "bootstrap-dev", "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("bootstrap-dev preflight ok", result.stdout)
            self.assertFalse((repo / ".ai-workroot-local").exists())

    def test_repo_fixture_copy_excludes_ignored_local_runtime_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            local = ROOT / ".ai-workroot-local"
            marker = local / "test-fixture-marker.tmp"
            local.mkdir(exist_ok=True)
            marker.write_text("local runtime metadata must not enter fixture copies\n", encoding="utf-8")
            try:
                repo = Path(tmp) / "repo"
                self.copy_repo(repo)

                self.assertFalse((repo / ".ai-workroot-local").exists())
            finally:
                marker.unlink(missing_ok=True)

    def test_bootstrap_dev_initializes_context_and_doctor_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.copy_repo(repo)
            env = {"AI_WORKROOT_HOME": str(home)}

            bootstrap = self.run_cli(repo, env, "bootstrap-dev")
            self.assertEqual(bootstrap.returncode, 0, bootstrap.stderr)
            self.assertTrue((home / "workroots/wr_ai_workroot/cache/workroot.sqlite").exists())

            context = self.run_cli(repo, env, "context", "--agent", "codex", "--cwd", str(repo))
            self.assertEqual(context.returncode, 0, context.stderr)
            self.assertIn("# AI Workroot Context Package", context.stdout)

            doctor = self.run_cli(repo, env, "doctor", "--cwd", str(repo))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("AI Workroot doctor: PASS", doctor.stdout)

    def test_bootstrap_dev_is_idempotent_for_same_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.copy_repo(repo)
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(repo, env, "bootstrap-dev")
            second = self.run_cli(repo, env, "bootstrap-dev")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("bootstrap-dev initialized wr_ai_workroot", first.stdout)
            self.assertIn("bootstrap-dev reused wr_ai_workroot", second.stdout)

    def test_bootstrap_dev_reuses_existing_state_for_same_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.copy_repo(repo)
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(repo, env, "bootstrap-dev")
            second = self.run_cli(repo, env, "bootstrap-dev")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            records_path = home / "registry/workroots.jsonl"
            records = [line for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(records), 1)
            self.assertTrue((home / "workroots/wr_ai_workroot/cache/workroot.sqlite").exists())
            self.assertTrue((repo / ".ai-workroot-local/context-packages").is_dir())
            self.assertIn(".ai-workroot-local/", (repo / ".gitignore").read_text(encoding="utf-8").splitlines())

    def test_bootstrap_dev_rejects_same_id_for_different_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first_repo = Path(tmp) / "first" / "repo"
            second_repo = Path(tmp) / "second" / "repo"
            home = Path(tmp) / "home"
            self.copy_repo(first_repo)
            self.copy_repo(second_repo)
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(first_repo, env, "bootstrap-dev")
            second = self.run_cli(second_repo, env, "bootstrap-dev")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already exists for a different directory", second.stderr)

    def test_concurrent_bootstrap_dev_is_idempotent_for_same_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            home = Path(tmp) / "home"
            self.copy_repo(repo)
            env = {"AI_WORKROOT_HOME": str(home)}

            def run_one(_: int) -> subprocess.CompletedProcess[str]:
                return self.run_cli(repo, env, "bootstrap-dev")

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(run_one, [1, 2]))

            for result in results:
                self.assertEqual(result.returncode, 0, result.stderr)
            records_path = home / "registry/workroots.jsonl"
            records = [line for line in records_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(records), 1)
            self.assertTrue(any("bootstrap-dev initialized wr_ai_workroot" in result.stdout for result in results))
            self.assertTrue(any("bootstrap-dev reused wr_ai_workroot" in result.stdout for result in results))


if __name__ == "__main__":
    unittest.main()
