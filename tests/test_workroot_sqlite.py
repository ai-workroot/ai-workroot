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

    def test_initialize_records_schema_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                tables = {
                    row[0]
                    for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual table')")
                }
                migration_ids = {
                    row[0]
                    for row in conn.execute("SELECT migration_id FROM schema_migrations ORDER BY migration_id")
                }

            self.assertIn("schema_migrations", tables)
            self.assertIn("001-initial-schema", migration_ids)

    def test_initialize_migrates_old_database_without_migration_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old.sqlite"
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE context_candidates (
                      candidate_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      source_type TEXT NOT NULL,
                      source_id TEXT NOT NULL,
                      title TEXT,
                      summary TEXT,
                      domains TEXT,
                      related_tasks TEXT,
                      related_assets TEXT,
                      importance TEXT,
                      confidence REAL,
                      status TEXT,
                      context_policy TEXT,
                      safety_policy TEXT,
                      token_estimate INTEGER,
                      updated_at TEXT,
                      last_used_at TEXT
                    )
                    """
                )
                conn.commit()

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as conn:
                columns = {row[1] for row in conn.execute("PRAGMA table_info(context_candidates)").fetchall()}
                migration_ids = {
                    row[0]
                    for row in conn.execute("SELECT migration_id FROM schema_migrations ORDER BY migration_id")
                }

            self.assertIn("use_count", columns)
            self.assertIn("001-initial-schema", migration_ids)
            self.assertIn("002-context-candidate-use-count", migration_ids)

    def test_graph_tables_are_scoped_by_per_workroot_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first_db = base / "wr_first" / "cache" / "workroot.sqlite"
            second_db = base / "wr_second" / "cache" / "workroot.sqlite"
            initialize_workroot_sqlite(first_db)
            initialize_workroot_sqlite(second_db)

            with sqlite3.connect(first_db) as conn:
                graph_columns = {row[1] for row in conn.execute("PRAGMA table_info(graph_nodes)").fetchall()}
                conn.execute(
                    """
                    INSERT INTO graph_nodes (
                      node_id, node_type, kind, title, summary, status, importance, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "node-first",
                        "decision",
                        "architecture",
                        "First Workroot node",
                        "Stored only in the first per-Workroot database.",
                        "active",
                        "high",
                        "2026-05-19T00:00:00Z",
                        "2026-05-19T00:00:00Z",
                    ),
                )
                conn.commit()

            with sqlite3.connect(second_db) as conn:
                second_count = conn.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]

            self.assertNotIn("workroot_id", graph_columns)
            self.assertEqual(second_count, 0)


if __name__ == "__main__":
    unittest.main()
