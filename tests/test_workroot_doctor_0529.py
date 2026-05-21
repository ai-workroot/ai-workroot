from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.legacy_doctor import run_doctor
from ai_workroot.storage.legacy_sqlite import initialize_workroot_sqlite
from scripts.workroot_state import initialize_workroot_state, write_json


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/workroot_cli.py"


class WorkrootDoctor0529Test(unittest.TestCase):
    def test_healthy_clean_mode_state_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")

            result = run_doctor(home, cwd=user_dir)

            self.assertFalse(result.has_errors())
            self.assertTrue(any(check.check_id == "clean-mode-boundary" for check in result.checks))

    def test_doctor_no_migration_warning_after_fresh_init(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")

            result = run_doctor(home, cwd=user_dir)

            migration = next(check for check in result.checks if check.check_id == "migration-records")
            self.assertEqual(migration.status, "pass")
            self.assertNotIn("not present yet", migration.message)

    def test_state_inside_user_directory_fails_clean_mode_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            bad_state_dir = user_dir / ".ai-workroot/workroots/wr_demo"
            bad_state_dir.mkdir(parents=True)
            write_json(
                bad_state_dir / "workroot.json",
                {
                    "workrootId": "wr_demo",
                    "name": "Demo",
                    "mode": "clean",
                    "userDirectory": str(user_dir.resolve()),
                    "stateDirectory": str(bad_state_dir.resolve()),
                },
            )

            result = run_doctor(home, cwd=user_dir, state_directory=bad_state_dir)
            clean_mode = next(check for check in result.checks if check.check_id == "clean-mode-boundary")

            self.assertEqual(clean_mode.status, "fail")
            self.assertEqual(clean_mode.severity, "error")
            self.assertTrue(result.has_errors())

    def test_missing_sqlite_table_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            sqlite3.connect(initialized.state_directory / "cache/workroot.sqlite").close()

            result = run_doctor(home, cwd=user_dir)
            sqlite_check = next(check for check in result.checks if check.check_id == "sqlite-schema")

            self.assertEqual(sqlite_check.status, "fail")
            self.assertIn("missing SQLite table", sqlite_check.message)
            self.assertTrue(result.has_errors())

    def test_cli_json_output_contains_actionable_check_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")
            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "doctor",
                    "--format",
                    "json",
                    "--cwd",
                    str(user_dir),
                ],
                cwd=ROOT,
                env={**os.environ, "AI_WORKROOT_HOME": str(home)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("checks", payload)
            self.assertTrue(payload["checks"])
            first_check = payload["checks"][0]
            for key in ("checkId", "category", "status", "severity", "suggestedAction"):
                self.assertIn(key, first_check)

    def test_default_doctor_from_registered_user_directory_runs_managed_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")

            result = subprocess.run(
                [sys.executable, str(CLI), "doctor"],
                cwd=user_dir,
                env={**os.environ, "AI_WORKROOT_HOME": str(home)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("AI Workroot doctor: PASS", result.stdout)

    def test_runtime_hints_check_passes_when_missing_and_defaults_are_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")
            (initialized.state_directory / "state/runtime-hints.json").unlink()

            result = run_doctor(home, cwd=user_dir)
            check = next(item for item in result.checks if item.check_id == "context-runtime-hints")

            self.assertEqual(check.status, "pass")
            self.assertIn("built-in defaults", check.message)

    def test_malformed_runtime_hints_fail_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")
            (initialized.state_directory / "state/runtime-hints.json").write_text("{not json", encoding="utf-8")

            result = run_doctor(home, cwd=user_dir)
            check = next(item for item in result.checks if item.check_id == "context-runtime-hints")

            self.assertEqual(check.status, "fail")
            self.assertIn("malformed", check.message)
            self.assertTrue(result.has_errors())

    def test_invalid_runtime_hint_budget_values_fail_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")
            hints = json.loads((initialized.state_directory / "state/runtime-hints.json").read_text(encoding="utf-8"))
            hints["contextGuide"]["agentBudgets"]["codex"]["targetTokens"] = "abc"
            write_json(initialized.state_directory / "state/runtime-hints.json", hints)

            result = run_doctor(home, cwd=user_dir)
            check = next(item for item in result.checks if item.check_id == "context-runtime-hints")

            self.assertEqual(check.status, "fail")
            self.assertIn("targetTokens", check.message)
            self.assertTrue(result.has_errors())

    def test_cli_context_rejects_negative_target_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialized = initialize_workroot_state(
                home,
                "wr_demo",
                "Demo",
                user_dir,
                now="2026-05-19T00:00:00Z",
            )
            initialize_workroot_sqlite(initialized.state_directory / "cache/workroot.sqlite")

            result = subprocess.run(
                [
                    sys.executable,
                    str(CLI),
                    "context",
                    "--agent",
                    "codex",
                    "--cwd",
                    str(user_dir),
                    "--target-tokens",
                    "-1",
                ],
                cwd=ROOT,
                env={**os.environ, "AI_WORKROOT_HOME": str(home)},
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("target token budget must be positive", result.stderr)


if __name__ == "__main__":
    unittest.main()
