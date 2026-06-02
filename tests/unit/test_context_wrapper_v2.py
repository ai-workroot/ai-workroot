from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.commands.build_context import build_context
from ai_workroot.context.control import workroot_guidance_text
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ContextWrapperV2Test(unittest.TestCase):
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
        self.sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        initialize_workroot_sqlite(self.sqlite_path)
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_context_wrapper_does_not_mint_lease_or_create_work_facts(self) -> None:
        before = self.count_rows(
            "exchange_leases",
            "protocol_events",
            "protocol_commit_batches",
            "tasks",
            "task_runs",
            "task_summaries",
            "handoffs",
        )

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Review protocol v2")

        after = self.count_rows(
            "exchange_leases",
            "protocol_events",
            "protocol_commit_batches",
            "tasks",
            "task_runs",
            "task_summaries",
            "handoffs",
        )
        self.assertEqual(after, before)
        self.assertIn("workroot agent sync", rendered)
        self.assertNotIn("Use sync to", rendered)
        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertNotIn("workroot agent commit --kind", rendered)

    def test_context_wrapper_does_not_expose_machine_state_or_storage_details(self) -> None:
        rendered = build_context(agent="codex", cwd=self.user_dir, query="Review protocol v2")

        for forbidden in (
            "observed_versions",
            "state_vector",
            "protocol_commit_batches",
            "exchange_leases",
            "workroot.sqlite",
            "cache/workroot.sqlite",
        ):
            self.assertNotIn(forbidden, rendered)

    def test_context_guidance_uses_requested_agent_name(self) -> None:
        rendered = build_context(agent="claude", cwd=self.user_dir, query="Review protocol v2")

        self.assertIn("workroot agent sync --agent claude", rendered)
        self.assertNotIn("workroot agent sync --agent codex", rendered)

    def test_fallback_workroot_guidance_uses_requested_agent_name(self) -> None:
        rendered = workroot_guidance_text(agent="claude")

        self.assertIn("workroot agent sync --agent claude", rendered)
        self.assertNotIn("workroot agent sync --agent codex", rendered)

    def test_context_wrapper_uses_sync_focus_and_does_not_bind_ambiguous_task(self) -> None:
        self.insert_task_graph("task-one", "run-one", "First Task")
        self.insert_task_graph("task-two", "run-two", "Second Task")

        rendered = build_context(agent="codex", cwd=self.user_dir, query="Continue.")

        self.assertIn("Focus: ambiguous", rendered)
        self.assertNotIn("## Current Task", rendered)
        self.assertNotIn("First Task [", rendered)
        self.assertNotIn("Second Task [", rendered)

    def count_rows(self, *tables: str) -> dict[str, int]:
        with sqlite3.connect(self.sqlite_path) as conn:
            return {table: int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) for table in tables}

    def insert_task_graph(self, task_id: str, run_id: str, title: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO tasks (
                  task_id, workroot_id, title, status, task_kind, process_level, role,
                  root_task_id, retention_policy, visibility, created_at, updated_at
                )
                VALUES (?, 'wr_demo', ?, 'active', 'task', 'L1', 'normal', ?, 'until_closed', 'normal',
                        '2026-05-28T00:00:00Z', '2026-05-28T00:00:00Z')
                """,
                (task_id, title, task_id),
            )
            conn.execute(
                """
                INSERT INTO task_runs (
                  run_id, task_id, workroot_id, agent_name, status, goal, input_summary,
                  output_summary, source_lease_id, started_at
                )
                VALUES (?, ?, 'wr_demo', 'codex', 'active', ?, ?, ?, '', '2026-05-28T00:00:00Z')
                """,
                (run_id, task_id, title, title, f"{title} summary"),
            )
            conn.commit()


if __name__ == "__main__":
    unittest.main()
