from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.work import (
    create_checkpoint,
    create_handoff,
    create_task,
    record_agent_run,
    record_invalidation,
    record_work_action,
)
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class RuntimeWorkTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_create_task_preserves_kind_and_process_level(self) -> None:
        conn = self.open_db()

        task = create_task(
            conn,
            workroot_id="wr_demo",
            task_id="task-architecture",
            title="Architecture reset",
            task_kind="project",
            process_level="L2",
        )

        row = conn.execute(
            """
            SELECT task_id, workroot_id, title, status, task_kind, process_level
            FROM tasks
            WHERE task_id = 'task-architecture'
            """
        ).fetchone()
        self.assertEqual(task.task_id, "task-architecture")
        self.assertEqual(task.process_level, "L2")
        self.assertEqual(row, ("task-architecture", "wr_demo", "Architecture reset", "active", "project", "L2"))

    def test_record_run_action_checkpoint_handoff_and_invalidation(self) -> None:
        conn = self.open_db()
        create_task(conn, workroot_id="wr_demo", task_id="task-runtime", title="Runtime parity")

        run = record_agent_run(
            conn,
            workroot_id="wr_demo",
            run_id="run-1",
            task_id="task-runtime",
            status="completed",
            validity="valid",
        )
        action = record_work_action(
            conn,
            workroot_id="wr_demo",
            action_id="action-1",
            task_id="task-runtime",
            action_type="edit",
            risk_level="normal",
        )
        checkpoint = create_checkpoint(
            conn,
            workroot_id="wr_demo",
            checkpoint_id="checkpoint-1",
            task_id="task-runtime",
            current_status="ContextRecallHint schema active.",
        )
        handoff = create_handoff(conn, workroot_id="wr_demo", handoff_id="handoff-1", title="Continue runtime parity")
        invalidation = record_invalidation(
            conn,
            workroot_id="wr_demo",
            invalidation_id="invalidation-1",
            invalidated_claim="Context cards were missing entirely.",
            reason="ContextRecallHint active path now exists.",
        )

        self.assertEqual(run.validity, "valid")
        self.assertEqual(action.risk_level, "normal")
        self.assertEqual(checkpoint.current_status, "ContextRecallHint schema active.")
        self.assertEqual(handoff["title"], "Continue runtime parity")
        self.assertEqual(invalidation.reason, "ContextRecallHint active path now exists.")
        self.assertEqual(
            conn.execute("SELECT status, validity FROM agent_runs WHERE run_id = 'run-1'").fetchone(),
            ("completed", "valid"),
        )
        self.assertEqual(
            conn.execute("SELECT action_type, risk_level FROM work_actions WHERE action_id = 'action-1'").fetchone(),
            ("edit", "normal"),
        )
        self.assertEqual(
            conn.execute("SELECT current_status FROM work_checkpoints WHERE checkpoint_id = 'checkpoint-1'").fetchone(),
            ("ContextRecallHint schema active.",),
        )
        self.assertEqual(
            conn.execute("SELECT title FROM handoffs WHERE handoff_id = 'handoff-1'").fetchone(),
            ("Continue runtime parity",),
        )
        self.assertEqual(
            conn.execute("SELECT reason FROM invalidation_records WHERE invalidation_id = 'invalidation-1'").fetchone(),
            ("ContextRecallHint active path now exists.",),
        )

    def test_work_runtime_rejects_missing_task_for_task_scoped_records(self) -> None:
        conn = self.open_db()

        with self.assertRaises(ValueError):
            record_agent_run(conn, workroot_id="wr_demo", run_id="run-missing", task_id="missing", status="active")

        with self.assertRaises(ValueError):
            record_work_action(
                conn,
                workroot_id="wr_demo",
                action_id="action-missing",
                task_id="missing",
                action_type="edit",
            )


if __name__ == "__main__":
    unittest.main()
