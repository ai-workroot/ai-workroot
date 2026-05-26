from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol.controller import sync
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolControllerSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "ai-home"
        self.user_dir = Path(self.tmp.name) / "workspace"
        self.user_dir.mkdir()
        initialize_environment(self.home)
        self.registration = register_workroot(
            self.home,
            workroot_id="wr_demo",
            name="Demo",
            user_directory=self.user_dir,
        )
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)
        initialize_workroot_sqlite(workroot_sqlite_path(Path(self.registration.state_directory)))

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_sync_returns_directive_lease_context_contract(self) -> None:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-1",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement the Workroot Agent Protocol P0.",
            }
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["state"]["workroot_id"], "wr_demo")
        self.assertEqual(response["directive"]["type"], "commit_required")
        self.assertIn("intent", response["contract"]["allowed_events"])
        self.assertEqual(response["lease"]["scope"], "workroot")
        self.assertEqual(response["context"], {"brief": "", "refs": [], "warnings": []})

    def test_sync_does_not_create_task_or_run(self) -> None:
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        before = self.count_semantic_rows(sqlite_path)

        sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-2",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create a task later through commit.",
            }
        )

        after = self.count_semantic_rows(sqlite_path)
        self.assertEqual(after, before)

    def count_semantic_rows(self, sqlite_path: Path) -> tuple[int, int, int]:
        with sqlite3.connect(sqlite_path) as conn:
            task_count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            run_count = conn.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0]
            handoff_count = conn.execute(
                "SELECT COUNT(*) FROM handoffs WHERE task_id IS NOT NULL OR current_state IS NOT NULL"
            ).fetchone()[0]
        return task_count, run_count, handoff_count


if __name__ == "__main__":
    unittest.main()
