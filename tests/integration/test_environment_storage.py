from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.environment import initialize_environment, register_workroot
from ai_workroot.storage.jsonl_registry import read_jsonl
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class EnvironmentStorageTest(unittest.TestCase):
    def test_initialize_environment_creates_clean_global_layout_without_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"

            environment = initialize_environment(home)

            self.assertEqual(environment.home, str(home.resolve()))
            self.assertTrue((home / "config.json").is_file())
            self.assertTrue((home / "registry/workroots.jsonl").is_file())
            self.assertTrue((home / "registry/directory-bindings.jsonl").is_file())
            self.assertTrue((home / "registry/.registry.lock").exists())
            self.assertTrue((home / "preferences/operator-preferences.json").is_file())
            self.assertTrue((home / "preferences/policy-defaults.json").is_file())
            self.assertTrue((home / "global-index").is_dir())
            self.assertTrue((home / "global-cache").is_dir())
            self.assertFalse((home / "user/profile.md").exists())

    def test_register_workroot_writes_locked_registry_and_rejects_duplicate_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"
            user_dir = Path(tmp) / "project"
            user_dir.mkdir()
            initialize_environment(home)

            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)

            self.assertEqual(registration.workroot_id, "wr_demo")
            self.assertEqual(registration.user_directory, str(user_dir.resolve()))
            self.assertTrue((home / "workroots/wr_demo/workroot.json").is_file())
            self.assertTrue((home / "workroots/wr_demo/relationships").is_dir())
            self.assertTrue((home / "workroots/wr_demo/release").is_dir())

            workroots = read_jsonl(home / "registry/workroots.jsonl")
            bindings = read_jsonl(home / "registry/directory-bindings.jsonl")
            self.assertEqual(len(workroots), 1)
            self.assertEqual(len(bindings), 1)

            with self.assertRaises(ValueError):
                register_workroot(home, workroot_id="wr_other", name="Other", user_directory=user_dir)

    def test_initialize_workroot_sqlite_creates_0530_canonical_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')"
                    )
                }

            for table in (
                "schema_migrations",
                "assets",
                "asset_surfaces",
                "time_events",
                "release_records",
                "tombstones",
                "redactions",
                "deletion_records",
                "relationship_nodes",
                "relationship_edges",
                "relationship_evidence",
                "index_manifests",
                "context_recall_hints",
                "context_recall_hints_fts",
                "context_candidates",
                "context_packages",
                "context_traces",
                "doctor_runs",
            ):
                with self.subTest(table=table):
                    self.assertIn(table, tables)

            self.assertNotIn("knowledge_items", tables)

    def test_initialize_workroot_sqlite_creates_release_lookup_indexes_and_index_source_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                indexes = {
                    row[1]
                    for row in connection.execute(
                        "SELECT type, name FROM sqlite_master WHERE type = 'index'"
                    )
                }
                indexed_file_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(indexed_files)").fetchall()
                }
                migrations = {
                    row[0] for row in connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
                }

            for index_name in (
                "idx_release_records_workroot_target",
                "idx_tombstones_workroot_target",
                "idx_redactions_workroot_target",
                "idx_deletion_records_workroot_target",
                "idx_context_recall_hints_workroot_target",
                "idx_context_candidates_workroot_source",
                "idx_indexed_files_workroot_source",
                "idx_relationship_edges_workroot_nodes",
            ):
                with self.subTest(index=index_name):
                    self.assertIn(index_name, indexes)
            self.assertIn("source_type", indexed_file_columns)
            self.assertIn("source_id", indexed_file_columns)
            self.assertIn("002-release-target-resolution-indexes", migrations)
            self.assertIn("003-context-recall-hints", migrations)

    def test_initialize_workroot_sqlite_creates_active_work_runtime_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()}
                run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()}
                action_columns = {row[1] for row in connection.execute("PRAGMA table_info(work_actions)").fetchall()}
                asset_columns = {row[1] for row in connection.execute("PRAGMA table_info(assets)").fetchall()}
                migrations = {
                    row[0] for row in connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
                }

            self.assertIn("task_kind", task_columns)
            self.assertIn("process_level", task_columns)
            self.assertIn("validity", run_columns)
            self.assertIn("risk_level", action_columns)
            self.assertIn("surface_id", asset_columns)
            self.assertIn("004-active-work-runtime-fields", migrations)
            self.assertIn("005-active-asset-runtime-fields", migrations)

    def test_initialize_workroot_sqlite_creates_time_event_projection_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                time_columns = {row[1] for row in connection.execute("PRAGMA table_info(time_events)").fetchall()}
                indexes = {
                    row[1]
                    for row in connection.execute(
                        "SELECT type, name FROM sqlite_master WHERE type = 'index'"
                    )
                }
                migrations = {
                    row[0] for row in connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
                }

            for column in (
                "event_id",
                "workroot_id",
                "subject_type",
                "subject_id",
                "event_type",
                "occurred_at",
                "time_range_start",
                "time_range_end",
                "source_ref",
                "created_at",
            ):
                with self.subTest(column=column):
                    self.assertIn(column, time_columns)
            self.assertIn("idx_time_events_workroot_subject", indexes)
            self.assertIn("006-time-events", migrations)

    def test_initialize_workroot_sqlite_migrates_old_indexed_files_without_source_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old-workroot.sqlite"
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE indexed_files (
                      file_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      relative_path TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO indexed_files (file_id, workroot_id, relative_path)
                    VALUES ('file-1', 'wr_demo', 'notes.md')
                    """
                )

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                indexed_file_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(indexed_files)").fetchall()
                }
                indexes = {
                    row[1]
                    for row in connection.execute(
                        "SELECT type, name FROM sqlite_master WHERE type = 'index'"
                    )
                }
                row = connection.execute(
                    "SELECT file_id, relative_path FROM indexed_files WHERE file_id = 'file-1'"
                ).fetchone()

            self.assertIn("source_type", indexed_file_columns)
            self.assertIn("source_id", indexed_file_columns)
            self.assertIn("idx_indexed_files_workroot_source", indexes)
            self.assertEqual(row, ("file-1", "notes.md"))


if __name__ == "__main__":
    unittest.main()
