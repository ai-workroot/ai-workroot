from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class WorkrootInitCliTest(unittest.TestCase):
    def run_cli(self, env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
        process_env = {**os.environ, **env}
        process_env["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, "-m", "ai_workroot", *args],
            cwd=ROOT,
            env=process_env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_init_creates_clean_mode_state_outside_user_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            result = self.run_cli(
                {"AI_WORKROOT_HOME": str(home)},
                "init",
                "--name",
                "Demo Workroot",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(user_dir.is_dir())
            records = json.loads(self.run_cli({"AI_WORKROOT_HOME": str(home)}, "list", "--format", "json").stdout)
            self.assertEqual(len(records), 1)
            workroot_id = records[0]["workrootId"]
            self.assertRegex(workroot_id, r"^wr_demo_workroot_[a-z0-9]{8}$")
            state_path = home / f"workroots/{workroot_id}/workroot.json"
            self.assertTrue(state_path.exists())
            self.assertTrue((home / f"workroots/{workroot_id}/cache/workroot.sqlite").exists())
            self.assertFalse((user_dir / ".workroot").exists())
            self.assertFalse((user_dir / ".ai-workroot").exists())
            self.assertFalse((user_dir / "context").exists())
            self.assertFalse((user_dir / "runtime").exists())
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], "0.9.530")
            self.assertEqual(payload["user_directory"], str(user_dir.resolve()))

    def test_package_clean_init_uses_package_cli_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            result = self.run_cli(
                {"AI_WORKROOT_HOME": str(home), "PYTHONPATH": str(ROOT / "src")},
                "init",
                "--name",
                "Delegated Workroot",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertRegex(result.stdout, r"^initialized wr_delegated_workroot_[a-z0-9]{8} registered\n$")
            records = json.loads(self.run_cli({"AI_WORKROOT_HOME": str(home), "PYTHONPATH": str(ROOT / "src")}, "list", "--format", "json").stdout)
            workroot_id = records[0]["workrootId"]
            payload = json.loads((home / f"workroots/{workroot_id}/workroot.json").read_text(encoding="utf-8"))
            self.assertIn("workroot_id", payload)
            self.assertNotIn("workrootId", payload)

    def test_list_and_status_show_registered_workroot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            env = {"AI_WORKROOT_HOME": str(home)}
            init = self.run_cli(
                env,
                "init",
                "--name",
                "Demo Workroot",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            listed = self.run_cli(env, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("Demo Workroot", listed.stdout)
            status = self.run_cli(env, "status", "--cwd", str(user_dir))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Workroot:", status.stdout)
            self.assertIn("UserDirectory:", status.stdout)
            self.assertIn("StateDirectory:", status.stdout)
            self.assertIn("Demo Workroot", status.stdout)

    def test_init_allows_duplicate_names_with_unique_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            first = base / "first"
            second = base / "second"
            env = {"AI_WORKROOT_HOME": str(home)}

            first_result = self.run_cli(env, "init", "--name", "Demo", "--directory", str(first), "--no-native-agent-entry")
            second_result = self.run_cli(env, "init", "--name", "Demo", "--directory", str(second), "--no-native-agent-entry")

            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            records = json.loads(self.run_cli(env, "list", "--format", "json").stdout)
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

            first_result = self.run_cli(env, "init", "--name", "One", "--id", "wr_fixed", "--directory", str(first), "--no-native-agent-entry")
            second_result = self.run_cli(env, "init", "--name", "Two", "--id", "wr_fixed", "--directory", str(second), "--no-native-agent-entry")

            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertNotEqual(second_result.returncode, 0)
            self.assertIn("already exists", second_result.stderr)

    def test_init_rejects_workroot_id_with_path_separator(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = self.run_cli(
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
            result = self.run_cli(
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
            result = self.run_cli(
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
                    result = self.run_cli(
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
            result = self.run_cli(
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
            result = self.run_cli(
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

    def test_init_rejects_duplicate_user_directory_with_different_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(env, "init", "--name", "One", "--directory", str(user_dir), "--no-native-agent-entry")
            second = self.run_cli(env, "init", "--name", "Two", "--directory", str(user_dir), "--no-native-agent-entry")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already registered as Workroot", second.stderr)

    def test_init_rejects_duplicate_user_directory_with_different_generated_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(env, "init", "--name", "Same", "--directory", str(user_dir), "--no-native-agent-entry")
            second = self.run_cli(env, "init", "--name", "Same", "--directory", str(user_dir), "--no-native-agent-entry")

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            records = json.loads(self.run_cli(env, "list", "--format", "json").stdout)
            self.assertEqual(len(records), 1)

    def test_duplicate_user_directory_error_mentions_existing_workroot_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            first = self.run_cli(env, "init", "--name", "One", "--id", "wr_existing", "--directory", str(user_dir), "--no-native-agent-entry")
            second = self.run_cli(env, "init", "--name", "Two", "--id", "wr_other", "--directory", str(user_dir), "--no-native-agent-entry")

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

            file_result = self.run_cli(env, "init", "--name", "File", "--directory", str(file_path), "--no-native-agent-entry")
            home_result = self.run_cli(env, "init", "--name", "Home", "--directory", str(home), "--no-native-agent-entry")

            self.assertNotEqual(file_result.returncode, 0)
            self.assertIn("not a directory", file_result.stderr)
            self.assertNotEqual(home_result.returncode, 0)
            self.assertIn("AI_WORKROOT_HOME", home_result.stderr)

    def test_init_preserves_existing_home_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            first = base / "first"
            second = base / "second"
            env = {"AI_WORKROOT_HOME": str(home)}

            self.assertEqual(self.run_cli(env, "init", "--name", "One", "--directory", str(first), "--no-native-agent-entry").returncode, 0)
            config_path = home / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["custom"] = "keep-me"
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            self.assertEqual(self.run_cli(env, "init", "--name", "Two", "--directory", str(second), "--no-native-agent-entry").returncode, 0)
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["custom"], "keep-me")

    def test_init_warns_for_nested_workroot_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            parent = base / "parent"
            child = parent / "child"
            env = {"AI_WORKROOT_HOME": str(home)}

            parent_result = self.run_cli(env, "init", "--name", "Parent", "--directory", str(parent), "--no-native-agent-entry")
            child_result = self.run_cli(env, "init", "--name", "Child", "--directory", str(child), "--no-native-agent-entry")

            self.assertEqual(parent_result.returncode, 0, parent_result.stderr)
            self.assertEqual(child_result.returncode, 0, child_result.stderr)
            self.assertIn("nested Workroot", child_result.stderr)

    def test_init_runs_doctor_equivalent_after_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            result = self.run_cli(env, "init", "--name", "Doctor", "--directory", str(user_dir), "--no-native-agent-entry")

            self.assertEqual(result.returncode, 0, result.stderr)
            doctor = self.run_cli(env, "doctor", "--cwd", str(user_dir))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("AI Workroot doctor: PASS", doctor.stdout)

    def test_init_native_agent_entry_requires_explicit_authorization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            result = self.run_cli(
                {"AI_WORKROOT_HOME": str(home)},
                "init",
                "--name",
                "Demo",
                "--directory",
                str(user_dir),
                "--native-agent-entry",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            agents = user_dir / "AGENTS.md"
            claude = user_dir / "CLAUDE.md"
            self.assertTrue(agents.exists())
            self.assertTrue(claude.exists())
            self.assertIn("<!-- AI_WORKROOT_BEGIN -->", agents.read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent codex --cwd .", agents.read_text(encoding="utf-8"))
            self.assertIn("workroot context --agent claude --cwd .", claude.read_text(encoding="utf-8"))

    def test_init_native_agent_entry_flags_are_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = self.run_cli(
                {"AI_WORKROOT_HOME": str(base / "home")},
                "init",
                "--name",
                "Bad Flags",
                "--directory",
                str(base / "project"),
                "--native-agent-entry",
                "--no-native-agent-entry",
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("not allowed with argument", result.stderr)

    def test_concurrent_init_rejects_duplicate_user_directory_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            def run_one(index: int) -> subprocess.CompletedProcess[str]:
                return self.run_cli(
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

            records = json.loads(self.run_cli(env, "list", "--format", "json").stdout)
            successes = [result for result in results if result.returncode == 0]
            failures = [result for result in results if result.returncode != 0]

            self.assertEqual(len(successes), 1, [result.stderr for result in results])
            self.assertEqual(len(failures), 1, [result.stderr for result in results])
            self.assertEqual(len(records), 1)
            self.assertIn("already registered as Workroot", failures[0].stderr)


if __name__ == "__main__":
    unittest.main()
