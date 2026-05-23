from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import ROOT, run_workroot_cli


class InitCleanModeCliTest(unittest.TestCase):
    def test_init_creates_clean_mode_state_outside_user_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            result = run_workroot_cli(
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
            records = json.loads(run_workroot_cli({"AI_WORKROOT_HOME": str(home)}, "list", "--format", "json").stdout)
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
            result = run_workroot_cli(
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
            records = json.loads(
                run_workroot_cli(
                    {"AI_WORKROOT_HOME": str(home), "PYTHONPATH": str(ROOT / "src")}, "list", "--format", "json"
                ).stdout
            )
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
            init = run_workroot_cli(
                env,
                "init",
                "--name",
                "Demo Workroot",
                "--directory",
                str(user_dir),
                "--no-native-agent-entry",
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            listed = run_workroot_cli(env, "list")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("Demo Workroot", listed.stdout)
            status = run_workroot_cli(env, "status", "--cwd", str(user_dir))
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertIn("Workroot:", status.stdout)
            self.assertIn("UserDirectory:", status.stdout)
            self.assertIn("StateDirectory:", status.stdout)
            self.assertIn("Demo Workroot", status.stdout)

    def test_init_preserves_existing_home_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            first = base / "first"
            second = base / "second"
            env = {"AI_WORKROOT_HOME": str(home)}

            self.assertEqual(
                run_workroot_cli(
                    env, "init", "--name", "One", "--directory", str(first), "--no-native-agent-entry"
                ).returncode,
                0,
            )
            config_path = home / "config.json"
            config = json.loads(config_path.read_text(encoding="utf-8"))
            config["custom"] = "keep-me"
            config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            self.assertEqual(
                run_workroot_cli(
                    env, "init", "--name", "Two", "--directory", str(second), "--no-native-agent-entry"
                ).returncode,
                0,
            )
            updated = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(updated["custom"], "keep-me")

    def test_init_warns_for_nested_workroot_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            parent = base / "parent"
            child = parent / "child"
            env = {"AI_WORKROOT_HOME": str(home)}

            parent_result = run_workroot_cli(
                env, "init", "--name", "Parent", "--directory", str(parent), "--no-native-agent-entry"
            )
            child_result = run_workroot_cli(
                env, "init", "--name", "Child", "--directory", str(child), "--no-native-agent-entry"
            )

            self.assertEqual(parent_result.returncode, 0, parent_result.stderr)
            self.assertEqual(child_result.returncode, 0, child_result.stderr)
            self.assertIn("nested Workroot", child_result.stderr)

    def test_init_runs_doctor_equivalent_after_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}

            result = run_workroot_cli(
                env, "init", "--name", "Doctor", "--directory", str(user_dir), "--no-native-agent-entry"
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            doctor = run_workroot_cli(env, "doctor", "--cwd", str(user_dir))
            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            self.assertIn("AI Workroot doctor: PASS", doctor.stdout)


if __name__ == "__main__":
    unittest.main()
