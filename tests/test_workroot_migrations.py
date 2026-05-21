from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ai_workroot.storage.migrations import (
    Migration,
    MigrationRunner,
    migration_lock,
    read_migration_records,
)


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

    def test_legacy_script_wrapper_exports_package_runner(self) -> None:
        from scripts.compat.workroot_migrations import MigrationRunner as LegacyMigrationRunner

        self.assertIs(LegacyMigrationRunner, MigrationRunner)

    def test_migration_lock_times_out_when_lock_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with migration_lock(root, "global"):
                with self.assertRaises(TimeoutError):
                    with migration_lock(root, "global", timeout=0.01):
                        pass


if __name__ == "__main__":
    unittest.main()
