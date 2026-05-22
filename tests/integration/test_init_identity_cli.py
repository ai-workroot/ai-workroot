from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import run_workroot_cli


class InitIdentityCliTest(unittest.TestCase):
    def test_init_allows_duplicate_names_with_unique_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            first = base / "first"
            second = base / "second"
            env = {"AI_WORKROOT_HOME": str(home)}

            first_result = run_workroot_cli(env, "init", "--name", "Demo", "--directory", str(first), "--no-native-agent-entry")
            second_result = run_workroot_cli(env, "init", "--name", "Demo", "--directory", str(second), "--no-native-agent-entry")

            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            records = json.loads(run_workroot_cli(env, "list", "--format", "json").stdout)
            ids = {record["workrootId"] for record in records}
            self.assertEqual(len(records), 2)
            self.assertEqual(len(ids), 2)
            self.assertEqual({record["name"] for record in records}, {"Demo"})

    def test_init_rejects_duplicate_explicit_workroot_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            first = base / "first"
            second = base / "second"
            env = {"AI_WORKROOT_HOME": str(home)}

            first_result = run_workroot_cli(env, "init", "--name", "One", "--id", "wr_fixed", "--directory", str(first), "--no-native-agent-entry")
            second_result = run_workroot_cli(env, "init", "--name", "Two", "--id", "wr_fixed", "--directory", str(second), "--no-native-agent-entry")

            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertNotEqual(second_result.returncode, 0)
            self.assertIn("already exists", second_result.stderr)

    def test_init_rejects_workroot_id_with_path_separator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(base / "home")},
                "init",
                "--name",
                "Bad",
                "--id",
                "wr_bad/name",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid Workroot ID", result.stderr)

    def test_init_rejects_workroot_id_with_backslash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(base / "home")},
                "init",
                "--name",
                "Bad",
                "--id",
                "wr_bad\\name",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid Workroot ID", result.stderr)

    def test_init_rejects_workroot_id_with_dotdot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(base / "home")},
                "init",
                "--name",
                "Bad",
                "--id",
                "wr_../bad",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid Workroot ID", result.stderr)

    def test_init_rejects_absolute_path_like_workroot_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for bad_id in ("/bad", "C:\\bad"):
                with self.subTest(workroot_id=bad_id):
                    result = run_workroot_cli(
                        {"AI_WORKROOT_HOME": str(base / "home")},
                        "init",
                        "--name",
                        "Bad",
                        "--id",
                        bad_id,
                        "--directory",
                        str(base / f"project-{bad_id.replace('/', 'slash').replace(':', 'colon').replace(chr(92), 'backslash')}"),
                        "--no-native-agent-entry",
                    )

                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("invalid Workroot ID", result.stderr)

    def test_init_rejects_workroot_id_without_wr_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(base / "home")},
                "init",
                "--name",
                "Bad",
                "--id",
                "bad_without_wr_prefix",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid Workroot ID", result.stderr)

    def test_state_directory_never_escapes_ai_workroot_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            result = run_workroot_cli(
                {"AI_WORKROOT_HOME": str(home)},
                "init",
                "--name",
                "Bad",
                "--id",
                "../../bad",
                "--directory",
                str(base / "project"),
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((base / "bad").exists())
            self.assertIn("invalid Workroot ID", result.stderr)


if __name__ == "__main__":
    unittest.main()
