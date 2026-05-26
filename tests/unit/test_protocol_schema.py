from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolSchemaTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_protocol_tables_exist(self) -> None:
        conn = self.open_db()
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')").fetchall()
        }

        self.assertIn("protocol_commit_batches", tables)
        self.assertIn("protocol_events", tables)
        self.assertIn("protocol_event_effects", tables)
        self.assertIn("exchange_leases", tables)
        self.assertIn("state_versions", tables)
        self.assertIn("task_runs", tables)
        self.assertIn("task_summaries", tables)

    def test_state_versions_are_workroot_scoped(self) -> None:
        conn = self.open_db()
        conn.execute(
            """
            INSERT INTO state_versions (workroot_id, scope, version, updated_at)
            VALUES ('wr_one', 'workroot', 1, '2026-05-26T10:00:00Z')
            """
        )
        conn.execute(
            """
            INSERT INTO state_versions (workroot_id, scope, version, updated_at)
            VALUES ('wr_two', 'workroot', 1, '2026-05-26T10:00:00Z')
            """
        )

        rows = conn.execute("SELECT COUNT(*) FROM state_versions WHERE scope = 'workroot'").fetchone()
        self.assertEqual(rows, (2,))

    def test_existing_0_9_530_tasks_and_handoffs_are_upgraded(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        with sqlite3.connect(db_path) as conn:
            conn.executescript(
                """
                CREATE TABLE schema_migrations (migration_id TEXT PRIMARY KEY, appliedAt TEXT);
                CREATE TABLE tasks (
                  task_id TEXT PRIMARY KEY,
                  workroot_id TEXT NOT NULL,
                  title TEXT,
                  status TEXT,
                  task_kind TEXT,
                  process_level TEXT
                );
                CREATE TABLE handoffs (
                  handoff_id TEXT PRIMARY KEY,
                  workroot_id TEXT NOT NULL,
                  title TEXT,
                  target TEXT,
                  body TEXT
                );
                """
            )

        initialize_workroot_sqlite(db_path)

        with sqlite3.connect(db_path) as conn:
            task_columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            handoff_columns = {row[1] for row in conn.execute("PRAGMA table_info(handoffs)").fetchall()}

        self.assertIn("role", task_columns)
        self.assertIn("retention_policy", task_columns)
        self.assertIn("visibility", task_columns)
        self.assertIn("metadata_json", task_columns)
        self.assertIn("task_id", handoff_columns)
        self.assertIn("current_state", handoff_columns)
        self.assertIn("source_refs_json", handoff_columns)


if __name__ == "__main__":
    unittest.main()
