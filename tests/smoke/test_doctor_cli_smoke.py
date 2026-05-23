from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from tests.support.cli import run_workroot_cli


class DoctorCliSmokeTest(unittest.TestCase):
    def test_doctor_records_environment_summary_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}
            init = run_workroot_cli(
                env, "init", "--name", "Doctor Summary", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            self.assertEqual(init.returncode, 0, init.stderr)

            doctor = run_workroot_cli(env, "doctor", "--cwd", str(user_dir))

            self.assertEqual(doctor.returncode, 0, doctor.stderr)
            config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["summary"]["lastDoctorStatus"], "PASS")
            self.assertRegex(config["summary"]["lastDoctorRunAt"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_doctor_records_summary_in_explicit_environment_home_not_registry_state_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            fake_home = base / "fake-home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}
            init = run_workroot_cli(
                env, "init", "--name", "Doctor Home", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            record_path = home / "registry/workroots.jsonl"
            record = json.loads(record_path.read_text(encoding="utf-8").splitlines()[0])
            fake_state = fake_home / "workroots" / record["workroot_id"]
            fake_state.mkdir(parents=True)
            original_state = Path(record["state_directory"])
            (fake_state / "workroot.json").write_text(
                (original_state / "workroot.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            record["state_directory"] = str(fake_state)
            record_path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            doctor = run_workroot_cli(env, "doctor", "--cwd", str(user_dir))

            self.assertNotEqual(doctor.returncode, 0)
            real_config = json.loads((home / "config.json").read_text(encoding="utf-8"))
            self.assertEqual(real_config["summary"]["lastDoctorStatus"], "FAIL")
            self.assertFalse((fake_home / "config.json").exists())

    def test_doctor_reports_missing_sqlite_table_without_repairing_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            env = {"AI_WORKROOT_HOME": str(home)}
            init = run_workroot_cli(
                env, "init", "--name", "Demo", "--directory", str(user_dir), "--no-native-agent-entry"
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                conn.execute("DROP TABLE context_candidates")

            doctor = run_workroot_cli(env, "doctor", "--cwd", str(user_dir))

            self.assertNotEqual(doctor.returncode, 0)
            self.assertIn("missing SQLite table: context_candidates", doctor.stdout)
            with sqlite3.connect(db_path) as conn:
                table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'context_candidates'"
                ).fetchone()
            self.assertIsNone(table)


if __name__ == "__main__":
    unittest.main()
