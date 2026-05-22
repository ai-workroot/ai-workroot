from __future__ import annotations

import tempfile
import unittest
from importlib import import_module
from pathlib import Path

from ai_workroot.storage.migrations import (
    Migration,
    MigrationRunner,
    migration_lock,
    read_migration_records,
)


def _legacy_snake_time_key(prefix: str) -> str:
    return f"{prefix}_at"


def _assert_utc_z(testcase: unittest.TestCase, value: str) -> None:
    testcase.assertRegex(value, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class WorkrootMigrationsTest(unittest.TestCase):
    def test_migrations_apply_once_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            applied: list[str] = []
            migrations = [
                Migration("0002_second", "global", lambda _: applied.append("0002_second")),
                Migration("0001_first", "global", lambda _: applied.append("0001_first")),
            ]
            runner = MigrationRunner(root, migrations)
            runner.apply("global")
            runner.apply("global")
            self.assertEqual(applied, ["0001_first", "0002_second"])
            records = read_migration_records(root / "migrations/global.jsonl")
            self.assertEqual([row["migrationId"] for row in records], ["0001_first", "0002_second"])
            for row in records:
                self.assertIn("startedAt", row)
                self.assertIn("completedAt", row)
                _assert_utc_z(self, row["startedAt"])
                _assert_utc_z(self, row["completedAt"])
                self.assertNotIn("startedAtUtc", row)
                self.assertNotIn("completedAtUtc", row)

    def test_failed_migration_records_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fail(_: Path) -> None:
                raise RuntimeError("boom")

            runner = MigrationRunner(root, [Migration("0001_fail", "global", fail)])
            with self.assertRaises(SystemExit):
                runner.apply("global")
            records = read_migration_records(root / "migrations/global.jsonl")
            self.assertEqual(records[0]["status"], "failed")
            self.assertIn("boom", records[0]["error"])
            self.assertIn("startedAt", records[0])
            self.assertIn("completedAt", records[0])
            _assert_utc_z(self, records[0]["startedAt"])
            _assert_utc_z(self, records[0]["completedAt"])
            self.assertNotIn("startedAtUtc", records[0])
            self.assertNotIn("completedAtUtc", records[0])

    def test_migration_runner_is_active_package_owner_without_legacy_wrapper(self) -> None:
        active_migrations = import_module("ai_workroot.storage.migrations")

        self.assertIs(active_migrations.MigrationRunner, MigrationRunner)
        with self.assertRaises(ModuleNotFoundError):
            import_module("scripts.compat.workroot_migrations")

    def test_migration_lock_times_out_when_lock_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with migration_lock(root, "global"):
                lock_text = (root / "migrations/locks/global.lock").read_text(encoding="utf-8")
                self.assertIn("createdAt=", lock_text)
                self.assertNotIn(_legacy_snake_time_key("created") + "=", lock_text)
                with self.assertRaises(TimeoutError):
                    with migration_lock(root, "global", timeout=0.01):
                        pass


if __name__ == "__main__":
    unittest.main()
