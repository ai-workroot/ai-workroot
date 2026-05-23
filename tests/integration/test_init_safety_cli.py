from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tests.support.cli import run_workroot_cli


class InitSafetyCliTest(unittest.TestCase):
    def test_init_rejects_duplicate_user_directory_with_different_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            first = run_workroot_cli(
                env, "init", "--name", "One", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            second = run_workroot_cli(
                env, "init", "--name", "Two", "--directory", str(user_dir), "--no-native-agent-entry"
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already registered as Workroot", second.stderr)

    def test_init_rejects_duplicate_user_directory_with_different_generated_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            first = run_workroot_cli(
                env, "init", "--name", "Same", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            second = run_workroot_cli(
                env, "init", "--name", "Same", "--directory", str(user_dir), "--no-native-agent-entry"
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            records = json.loads(run_workroot_cli(env, "list", "--format", "json").stdout)
            self.assertEqual(len(records), 1)

    def test_duplicate_user_directory_error_mentions_existing_workroot_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            first = run_workroot_cli(
                env,
                "init",
                "--name",
                "One",
                "--id",
                "wr_existing",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            second = run_workroot_cli(
                env,
                "init",
                "--name",
                "Two",
                "--id",
                "wr_other",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("wr_existing", second.stderr)

    def test_init_rejects_file_system_and_home_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            file_path = base / "not-a-directory"
            file_path.write_text("not a directory", encoding="utf-8")
            env = {"AI_WORKROOT_HOME": str(home)}

            file_result = run_workroot_cli(
                env, "init", "--name", "File", "--directory", str(file_path), "--no-native-agent-entry"
            )
            home_result = run_workroot_cli(
                env, "init", "--name", "Home", "--directory", str(home), "--no-native-agent-entry"
            )

            self.assertNotEqual(file_result.returncode, 0)
            self.assertIn("not a directory", file_result.stderr)
            self.assertNotEqual(home_result.returncode, 0)
            self.assertIn("AI_WORKROOT_HOME", home_result.stderr)

    def test_concurrent_init_rejects_duplicate_user_directory_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            def run_one(index: int) -> subprocess.CompletedProcess[str]:
                return run_workroot_cli(
                    env,
                    "init",
                    "--name",
                    f"Concurrent {index}",
                    "--directory",
                    str(user_dir),
                    "--no-native-agent-entry",
                )

            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(run_one, [1, 2]))

            records = json.loads(run_workroot_cli(env, "list", "--format", "json").stdout)
            successes = [result for result in results if result.returncode == 0]
            failures = [result for result in results if result.returncode != 0]

            self.assertEqual(len(successes), 1, [result.stderr for result in results])
            self.assertEqual(len(failures), 1, [result.stderr for result in results])
            self.assertEqual(len(records), 1)
            self.assertIn("already registered as Workroot", failures[0].stderr)


if __name__ == "__main__":
    unittest.main()
