from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.retrieval.global_indexes import (
    query_global_index_health,
    query_global_asset_index,
    query_global_task_index,
    query_global_time_index,
    query_global_workroot_index,
    refresh_global_asset_index,
    refresh_global_task_index,
    refresh_global_time_index,
    refresh_global_workroot_index,
)
from ai_workroot.capabilities.assets.operations import create_internal_asset
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.capabilities.work.time import record_time_event
from ai_workroot.capabilities.work.operations import create_task
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class GlobalIndexesTest(unittest.TestCase):
    def test_refresh_and_query_global_workroot_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"
            initialize_workroot_sqlite(db_path)

            entry_count = refresh_global_workroot_index(home)
            entries = query_global_workroot_index(home, query="Demo")

            self.assertEqual(entry_count, 1)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["entryType"], "workroot")
            self.assertEqual(entries[0]["workrootId"], "wr_demo")
            self.assertEqual(entries[0]["title"], "Demo")
            index_path = home / "global-index/workroots.index.jsonl"
            self.assertTrue(index_path.is_file())
            self.assertIn('"workrootId": "wr_demo"', index_path.read_text(encoding="utf-8"))
            with sqlite3.connect(db_path) as conn:
                row = conn.execute(
                    """
                    SELECT entry_type, title
                    FROM global_index_entries
                    WHERE entry_id = 'workroot:wr_demo'
                    """
                ).fetchone()
            self.assertEqual(row, ("workroot", "Demo"))

    def test_global_workroot_index_skips_missing_database_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"

            entry_count = refresh_global_workroot_index(home)
            health = query_global_index_health(home)

            self.assertEqual(entry_count, 0)
            self.assertFalse(db_path.exists())
            self.assertEqual(len(health), 1)
            self.assertEqual(health[0]["reason"], "missing-workroot-sqlite")
            self.assertEqual(health[0]["workrootId"], "wr_demo")

    def test_global_workroot_index_does_not_create_context_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"
            initialize_workroot_sqlite(db_path)

            refresh_global_workroot_index(home)

            with sqlite3.connect(db_path) as conn:
                candidate_count = conn.execute("SELECT COUNT(*) FROM context_candidates").fetchone()[0]

            self.assertEqual(candidate_count, 0)

    def test_global_task_asset_and_time_indexes_skip_missing_database_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"

            self.assertEqual(refresh_global_task_index(home), 0)
            self.assertEqual(refresh_global_asset_index(home), 0)
            self.assertEqual(refresh_global_time_index(home), 0)

            health = query_global_index_health(home)
            self.assertFalse(db_path.exists())
            self.assertEqual([row["reason"] for row in health], ["missing-workroot-sqlite"])

    def test_refresh_and_query_global_task_asset_and_time_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, workroot_id="wr_demo", name="Demo", user_directory=user_dir)
            db_path = Path(registration.state_directory) / "cache/workroot.sqlite"
            initialize_workroot_sqlite(db_path)
            with sqlite3.connect(db_path) as conn:
                create_task(conn, workroot_id="wr_demo", task_id="task-1", title="Task index parity")
                create_internal_asset(
                    conn,
                    workroot_id="wr_demo",
                    asset_id="asset-1",
                    asset_type="decision",
                    title="Asset index parity",
                )
                record_time_event(
                    conn,
                    workroot_id="wr_demo",
                    event_id="time-1",
                    subject_type="task",
                    subject_id="task-1",
                    event_type="task_closed",
                    occurred_at="2026-05-21T10:00:00Z",
                )

            self.assertEqual(refresh_global_task_index(home), 1)
            self.assertEqual(refresh_global_asset_index(home), 1)
            self.assertEqual(refresh_global_time_index(home), 1)

            task_entries = query_global_task_index(home, query="parity")
            asset_entries = query_global_asset_index(home, query="decision")
            time_entries = query_global_time_index(home, query="task_closed")

            self.assertEqual(task_entries[0]["entryType"], "task")
            self.assertEqual(task_entries[0]["workrootId"], "wr_demo")
            self.assertEqual(task_entries[0]["taskId"], "task-1")
            self.assertEqual(asset_entries[0]["entryType"], "asset")
            self.assertEqual(asset_entries[0]["assetType"], "decision")
            self.assertEqual(time_entries[0]["entryType"], "time_event")
            self.assertEqual(time_entries[0]["occurredAt"], "2026-05-21T10:00:00Z")
            self.assertTrue((home / "global-index/tasks.index.jsonl").is_file())
            self.assertTrue((home / "global-index/assets.index.jsonl").is_file())
            self.assertTrue((home / "global-index/time.index.jsonl").is_file())

            with sqlite3.connect(db_path) as conn:
                candidate_count = conn.execute("SELECT COUNT(*) FROM context_candidates").fetchone()[0]
                global_entries = conn.execute(
                    """
                    SELECT entry_type, title
                    FROM global_index_entries
                    WHERE entry_id IN ('task:wr_demo:task-1', 'asset:wr_demo:asset-1', 'time:wr_demo:time-1')
                    ORDER BY entry_type ASC
                    """
                ).fetchall()

            self.assertEqual(candidate_count, 0)
            self.assertEqual(
                global_entries,
                [
                    ("asset", "Asset index parity"),
                    ("task", "Task index parity"),
                    ("time_event", "task_closed task task-1"),
                ],
            )


if __name__ == "__main__":
    unittest.main()
