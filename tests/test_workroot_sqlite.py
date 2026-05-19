from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.workroot_sqlite import initialize_workroot_sqlite, required_tables, verify_workroot_sqlite


class WorkrootSqliteTest(unittest.TestCase):
    def test_initialize_creates_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
                }
            for table in required_tables():
                self.assertIn(table, tables)

    def test_wal_mode_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            self.assertEqual(mode.lower(), "wal")

    def test_verify_reports_missing_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "empty.sqlite"
            db_path.parent.mkdir(parents=True, exist_ok=True)
            sqlite3.connect(db_path).close()
            issues = verify_workroot_sqlite(db_path)
            self.assertTrue(any("graph_nodes" in issue for issue in issues))

    def test_sqlite_schema_contains_workroot_management_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
                }

            for table in ("tasks", "assets", "knowledge_items", "domains", "handoffs", "time_events"):
                self.assertIn(table, tables)

    def test_context_candidates_include_use_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(context_candidates)").fetchall()}

            self.assertIn("use_count", columns)


if __name__ == "__main__":
    unittest.main()
