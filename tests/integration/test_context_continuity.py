from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.commands.build_context import build_context
from ai_workroot.commands.init_workroot import initialize_workroot
from ai_workroot.capabilities.handoff.operations import create_handoff
from ai_workroot.capabilities.work.operations import create_checkpoint, create_task


class ContextContinuityTest(unittest.TestCase):
    def test_active_task_checkpoint_and_handoff_are_rendered_as_continuity_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                create_task(
                    conn,
                    workroot_id=workroot_id,
                    task_id="task-active-context",
                    title="Active Context parity task",
                    task_kind="architecture",
                    process_level="L2",
                )
                create_checkpoint(
                    conn,
                    workroot_id=workroot_id,
                    checkpoint_id="checkpoint-active-context",
                    task_id="task-active-context",
                    current_status="Checkpoint says release filters are green.",
                )
                create_handoff(
                    conn,
                    workroot_id=workroot_id,
                    handoff_id="handoff-active-context",
                    title="Next: verify Context Control parity.",
                )

            package = build_context(
                agent="codex",
                cwd=user_dir,
                query="parity",
                debug=True,
                ai_workroot_home=home,
            )

            self.assertIn("## Workroot", package)
            self.assertIn("Demo", package)
            self.assertIn("## Current Task", package)
            self.assertIn("Active Context parity task", package)
            self.assertIn("architecture", package)
            self.assertIn("L2", package)
            self.assertIn("## Continuity", package)
            self.assertIn("Checkpoint says release filters are green.", package)
            self.assertIn("Next: verify Context Control parity.", package)
            self.assertIn("continuitySources:", package)
            with sqlite3.connect(db_path) as conn:
                trace_json = conn.execute(
                    "SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1"
                ).fetchone()[0]
            trace = json.loads(trace_json)
            self.assertEqual(trace["continuity"]["activeTaskId"], "task-active-context")
            self.assertEqual(trace["continuity"]["checkpointId"], "checkpoint-active-context")
            self.assertEqual(trace["continuity"]["handoffId"], "handoff-active-context")


if __name__ == "__main__":
    unittest.main()
