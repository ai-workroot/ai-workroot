from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.workroot_migrations import Migration, MigrationRunner, read_migration_records


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


if __name__ == "__main__":
    unittest.main()
