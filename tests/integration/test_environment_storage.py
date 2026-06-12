from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.composition.projections import project_decision
from ai_workroot.capabilities.retrieval.model import ContextRecallHint
from ai_workroot.capabilities.retrieval.providers.context_recall_hint_provider import upsert_context_recall_hint
from ai_workroot.state.environment import (
    initialize_environment,
    register_workroot,
    register_workroot_unlocked,
    unregister_workroot,
)
from ai_workroot.state.jsonl import read_jsonl
from ai_workroot.state.sqlite import SCHEMA, SQLITE_SCHEMA_MIGRATION_IDS, initialize_workroot_sqlite


def _legacy_snake_time_key(prefix: str) -> str:
    return f"{prefix}_at"


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

    def test_register_workroot_rejects_unsafe_workroot_id_at_state_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"
            user_dir = Path(tmp) / "project"
            user_dir.mkdir()
            initialize_environment(home)

            for registrar in (register_workroot, register_workroot_unlocked):
                with self.assertRaises(ValueError):
                    registrar(home, workroot_id="../escape", name="Unsafe", user_directory=user_dir)
                self.assertFalse((home / "escape").exists())

    def test_unregister_workroot_removes_target_registration_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"
            first_dir = Path(tmp) / "first"
            second_dir = Path(tmp) / "second"
            first_dir.mkdir()
            second_dir.mkdir()
            initialize_environment(home)
            register_workroot(home, workroot_id="wr_first", name="First", user_directory=first_dir)
            register_workroot(home, workroot_id="wr_second", name="Second", user_directory=second_dir)

            unregister_workroot(home, "wr_first", first_dir)

            workroots = read_jsonl(home / "registry/workroots.jsonl")
            bindings = read_jsonl(home / "registry/directory-bindings.jsonl")
            self.assertEqual([record["workroot_id"] for record in workroots], ["wr_second"])
            self.assertEqual([record["workroot_id"] for record in bindings], ["wr_second"])
            self.assertFalse((home / "workroots/wr_first").exists())
            self.assertTrue((home / "workroots/wr_second/workroot.json").is_file())

    def test_unregister_workroot_ignores_mismatched_user_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "ai-workroot-home"
            first_dir = Path(tmp) / "first"
            other_dir = Path(tmp) / "other"
            first_dir.mkdir()
            other_dir.mkdir()
            initialize_environment(home)
            register_workroot(home, workroot_id="wr_first", name="First", user_directory=first_dir)

            unregister_workroot(home, "wr_first", other_dir)

            workroots = read_jsonl(home / "registry/workroots.jsonl")
            bindings = read_jsonl(home / "registry/directory-bindings.jsonl")
            self.assertEqual([record["workroot_id"] for record in workroots], ["wr_first"])
            self.assertEqual([record["workroot_id"] for record in bindings], ["wr_first"])
            self.assertTrue((home / "workroots/wr_first/workroot.json").is_file())

    def test_initialize_workroot_sqlite_creates_0530_canonical_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                tables = {
                    row[0]
                    for row in connection.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')")
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

    def test_sqlite_schema_migrations_are_centralized_and_not_written_by_schema_text(self) -> None:
        self.assertEqual(len(SQLITE_SCHEMA_MIGRATION_IDS), len(set(SQLITE_SCHEMA_MIGRATION_IDS)))
        self.assertEqual(list(SQLITE_SCHEMA_MIGRATION_IDS), sorted(SQLITE_SCHEMA_MIGRATION_IDS))
        self.assertIn("001-clean-workroot-schema", SQLITE_SCHEMA_MIGRATION_IDS)
        self.assertIn("010-context-runtime-schema", SQLITE_SCHEMA_MIGRATION_IDS)
        self.assertNotIn("INSERT OR IGNORE INTO schema_migrations", SCHEMA)

    def test_initialize_workroot_sqlite_records_registered_migrations_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                first_rows = connection.execute(
                    "SELECT migration_id, appliedAt FROM schema_migrations ORDER BY migration_id"
                ).fetchall()

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                second_rows = connection.execute(
                    "SELECT migration_id, appliedAt FROM schema_migrations ORDER BY migration_id"
                ).fetchall()

            self.assertEqual([row[0] for row in first_rows], list(SQLITE_SCHEMA_MIGRATION_IDS))
            self.assertEqual(first_rows, second_rows)
            for _migration_id, appliedAt in first_rows:
                self.assertRegex(appliedAt, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_initialize_workroot_sqlite_creates_release_lookup_indexes_and_index_source_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                indexes = {
                    row[1] for row in connection.execute("SELECT type, name FROM sqlite_master WHERE type = 'index'")
                }
                indexed_file_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(indexed_files)").fetchall()
                }
                migration_rows = connection.execute("SELECT migration_id, appliedAt FROM schema_migrations").fetchall()
                migrations = {row[0] for row in migration_rows}

            for index_name in (
                "idx_release_records_workroot_target",
                "idx_tombstones_workroot_target",
                "idx_redactions_workroot_target",
                "idx_deletion_records_workroot_target",
                "idx_context_recall_hints_workroot_target",
                "idx_context_candidates_workroot_source",
                "idx_indexed_files_workroot_source",
                "idx_relationship_nodes_workroot_target",
                "idx_relationship_edges_workroot_nodes",
            ):
                with self.subTest(index=index_name):
                    self.assertIn(index_name, indexes)
            self.assertIn("source_type", indexed_file_columns)
            self.assertIn("source_id", indexed_file_columns)
            self.assertIn("002-release-target-resolution-indexes", migrations)
            self.assertIn("003-context-recall-hints", migrations)
            for _migration_id, appliedAt in migration_rows:
                self.assertRegex(appliedAt, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_initialize_workroot_sqlite_creates_active_work_runtime_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)").fetchall()}
                run_columns = {row[1] for row in connection.execute("PRAGMA table_info(agent_runs)").fetchall()}
                action_columns = {row[1] for row in connection.execute("PRAGMA table_info(work_actions)").fetchall()}
                asset_columns = {row[1] for row in connection.execute("PRAGMA table_info(assets)").fetchall()}
                publication_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(asset_publications)").fetchall()
                }
                migrations = {
                    row[0] for row in connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
                }

            self.assertIn("task_kind", task_columns)
            self.assertIn("process_level", task_columns)
            self.assertIn("validity", run_columns)
            self.assertIn("risk_level", action_columns)
            self.assertIn("surface_id", asset_columns)
            self.assertIn("updatedAt", asset_columns)
            self.assertNotIn(_legacy_snake_time_key("updated"), asset_columns)
            self.assertIn("publishedAt", publication_columns)
            self.assertIn("004-active-work-runtime-fields", migrations)
            self.assertIn("005-active-asset-runtime-fields", migrations)

    def test_initialize_workroot_sqlite_creates_time_event_projection_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                time_columns = {row[1] for row in connection.execute("PRAGMA table_info(time_events)").fetchall()}
                indexes = {
                    row[1] for row in connection.execute("SELECT type, name FROM sqlite_master WHERE type = 'index'")
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
                "occurredAt",
                "timezoneId",
                "localDate",
                "timeRangeStart",
                "timeRangeEnd",
                "source_ref",
                "createdAt",
            ):
                with self.subTest(column=column):
                    self.assertIn(column, time_columns)
            self.assertIn("idx_time_events_workroot_subject", indexes)
            self.assertIn("006-time-events", migrations)

    def test_initialize_workroot_sqlite_uses_canonical_utc_context_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "workroot.sqlite"

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                migration_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(schema_migrations)").fetchall()
                }
                candidate_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(context_candidates)").fetchall()
                }
                hint_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(context_recall_hints)").fetchall()
                }

            self.assertIn("appliedAt", migration_columns)
            self.assertNotIn(_legacy_snake_time_key("applied"), migration_columns)
            self.assertIn("updatedAt", candidate_columns)
            self.assertIn("lastUsedAt", candidate_columns)
            self.assertNotIn(_legacy_snake_time_key("updated"), candidate_columns)
            self.assertNotIn(_legacy_snake_time_key("last_used"), candidate_columns)
            self.assertIn("createdAt", hint_columns)
            self.assertIn("updatedAt", hint_columns)
            self.assertNotIn(_legacy_snake_time_key("created"), hint_columns)
            self.assertNotIn(_legacy_snake_time_key("updated"), hint_columns)

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
                    row[1] for row in connection.execute("SELECT type, name FROM sqlite_master WHERE type = 'index'")
                }
                row = connection.execute(
                    "SELECT file_id, relative_path FROM indexed_files WHERE file_id = 'file-1'"
                ).fetchone()

            self.assertIn("source_type", indexed_file_columns)
            self.assertIn("source_id", indexed_file_columns)
            self.assertIn("idx_indexed_files_workroot_source", indexes)
            self.assertEqual(row, ("file-1", "notes.md"))

    def test_initialize_workroot_sqlite_migrates_old_relationship_nodes_without_target_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old-workroot.sqlite"
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE relationship_nodes (
                      node_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      node_type TEXT NOT NULL,
                      title TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title)
                    VALUES ('graph-asset-node-1', 'wr_demo', 'asset', 'Asset node')
                    """
                )
                connection.commit()

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(relationship_nodes)").fetchall()}
                indexes = {
                    row[1] for row in connection.execute("SELECT type, name FROM sqlite_master WHERE type = 'index'")
                }
                migrations = {
                    row[0] for row in connection.execute("SELECT migration_id FROM schema_migrations").fetchall()
                }
                row = connection.execute(
                    """
                    SELECT node_id, node_type, target_type, target_id
                    FROM relationship_nodes
                    WHERE node_id = 'graph-asset-node-1'
                    """
                ).fetchone()

            self.assertIn("target_type", columns)
            self.assertIn("target_id", columns)
            self.assertIn("idx_relationship_nodes_workroot_target", indexes)
            self.assertIn("007-relationship-node-canonical-targets", migrations)
            self.assertEqual(row, ("graph-asset-node-1", "asset", None, None))

    def test_initialize_workroot_sqlite_migrates_old_context_candidate_schema_for_projection_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old-context-candidates.sqlite"
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE context_candidates (
                      candidate_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      source_type TEXT NOT NULL,
                      source_id TEXT NOT NULL,
                      title TEXT,
                      summary TEXT
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE VIRTUAL TABLE context_candidates_fts
                    USING fts5(candidate_id, title, summary)
                    """
                )
                connection.commit()

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                project_decision(
                    connection,
                    workroot_id="wr_demo",
                    lease={},
                    event={
                        "event_id": "event-decision-old-context",
                        "payload": {
                            "decision": "Preserve projection-compatible context candidates.",
                            "title": "Projection compatibility",
                            "reason": "Old databases must accept current projection writes.",
                        },
                    },
                )
                connection.commit()
                candidate_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(context_candidates)").fetchall()
                }
                fts_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(context_candidates_fts)").fetchall()
                }
                row = connection.execute(
                    """
                    SELECT domains, importance, confidence, status, context_policy,
                           safety_policy, token_estimate, updatedAt, lastUsedAt, use_count
                    FROM context_candidates
                    WHERE candidate_id LIKE 'decision:%'
                    """
                ).fetchone()
                fts_row = connection.execute(
                    """
                    SELECT candidate_id
                    FROM context_candidates_fts
                    WHERE context_candidates_fts MATCH 'Projection'
                    """
                ).fetchone()

            for column in (
                "domains",
                "importance",
                "confidence",
                "status",
                "context_policy",
                "safety_policy",
                "token_estimate",
                "updatedAt",
                "lastUsedAt",
                "use_count",
            ):
                with self.subTest(column=column):
                    self.assertIn(column, candidate_columns)
            self.assertEqual({"candidate_id", "title", "summary", "domains"}, fts_columns)
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "workroot scope:task")
            self.assertEqual(row[3], "active")
            self.assertIsNotNone(fts_row)

    def test_initialize_workroot_sqlite_migrates_old_context_recall_hint_schema_for_provider_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old-context-hints.sqlite"
            with sqlite3.connect(db_path) as connection:
                connection.execute(
                    """
                    CREATE TABLE context_recall_hints (
                      hint_id TEXT PRIMARY KEY,
                      workroot_id TEXT NOT NULL,
                      target_type TEXT NOT NULL,
                      target_id TEXT NOT NULL
                    )
                    """
                )
                connection.commit()

            initialize_workroot_sqlite(db_path)

            with sqlite3.connect(db_path) as connection:
                upsert_context_recall_hint(
                    connection,
                    ContextRecallHint(
                        hint_id="hint-old-schema",
                        workroot_id="wr_demo",
                        target_type="task",
                        target_id="task-demo",
                        scope_type="task",
                        scope_id="task-demo",
                        kind="context-card",
                        title="Old schema hint",
                        summary="Old schema accepts current hint writes.",
                        priority="high",
                        recall_rule="task-related",
                        lifecycle_status="active",
                        origin="projection",
                        source_ref="task:task-demo",
                        created_at="2026-06-09T00:00:00Z",
                        updated_at="2026-06-09T00:00:00Z",
                    ),
                )
                hint_columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(context_recall_hints)").fetchall()
                }
                row = connection.execute(
                    """
                    SELECT scope_type, scope_id, kind, title, summary, priority, recall_rule,
                           lifecycle_status, origin, source_ref, createdAt, updatedAt
                    FROM context_recall_hints
                    WHERE hint_id = 'hint-old-schema'
                    """
                ).fetchone()
                fts_row = connection.execute(
                    """
                    SELECT hint_id
                    FROM context_recall_hints_fts
                    WHERE context_recall_hints_fts MATCH 'schema'
                    """
                ).fetchone()

            for column in (
                "scope_type",
                "scope_id",
                "kind",
                "title",
                "summary",
                "priority",
                "recall_rule",
                "lifecycle_status",
                "origin",
                "source_ref",
                "createdAt",
                "updatedAt",
            ):
                with self.subTest(column=column):
                    self.assertIn(column, hint_columns)
            self.assertEqual(row[0], "task")
            self.assertEqual(row[5], "high")
            self.assertIsNotNone(fts_row)


if __name__ == "__main__":
    unittest.main()
