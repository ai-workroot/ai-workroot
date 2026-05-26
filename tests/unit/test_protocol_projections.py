from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol.controller import commit
from ai_workroot.protocol.lease import create_lease
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolProjectionTest(unittest.TestCase):
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
        self.sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        initialize_workroot_sqlite(self.sqlite_path)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def create_lease(self, *, task_id: str | None = None, run_id: str | None = None, events: list[str]) -> str:
        with sqlite3.connect(self.sqlite_path) as conn:
            lease = create_lease(
                conn,
                workroot_id="wr_demo",
                scope="task" if task_id else "workroot",
                task_id=task_id,
                run_id=run_id,
                allowed_events=events,
                required_before_stop=["handoff"] if task_id else [],
            )
            return lease["lease_id"]

    def test_commit_intent_creates_task_and_run(self) -> None:
        response = commit(self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload()))

        self.assertTrue(response["ok"])
        task_id = response["lease"]["task_id"]
        run_id = response["lease"]["run_id"]
        with sqlite3.connect(self.sqlite_path) as conn:
            task = conn.execute("SELECT role, process_level, title FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            run = conn.execute("SELECT status, goal FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()

        self.assertEqual(task, ("normal", "L1", "Protocol P0"))
        self.assertEqual(run, ("active", "Implement protocol P0"))
        self.assertIn("progress", response["contract"]["allowed_events"])

    def test_commit_progress_updates_run_and_returns_next_lease(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = intent_response["lease"]["task_id"]
        run_id = intent_response["lease"]["run_id"]

        response = commit(
            self.commit_request(
                intent_response["lease"]["lease_id"],
                "progress",
                {"task_id": task_id, "run_id": run_id, "summary": "Implemented protocol models."},
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT output_summary FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()
        self.assertEqual(row, ("Implemented protocol models.",))
        self.assertEqual(response["lease"]["task_id"], task_id)

    def test_commit_progress_creates_task_items(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = intent_response["lease"]["task_id"]
        run_id = intent_response["lease"]["run_id"]

        response = commit(
            self.commit_request(
                intent_response["lease"]["lease_id"],
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Planned task item work.",
                    "items_created": [
                        {
                            "item_id": "item-schema",
                            "title": "Implement task item schema",
                            "status": "todo",
                            "order": 10,
                        }
                    ],
                },
                event_id="evt-progress-create-items",
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT title, status, item_order FROM task_items WHERE item_id = 'item-schema'"
            ).fetchone()
        self.assertEqual(row, ("Implement task item schema", "todo", 10))
        self.assertIn(
            {"type": "task_item_created", "target_type": "task_item", "target_id": "item-schema"},
            response["effects"],
        )

    def test_commit_progress_updates_task_items(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = intent_response["lease"]["task_id"]
        run_id = intent_response["lease"]["run_id"]
        created = commit(
            self.commit_request(
                intent_response["lease"]["lease_id"],
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Created item.",
                    "items_created": [{"item_id": "item-schema", "title": "Implement task item schema"}],
                },
                event_id="evt-progress-create-item-for-update",
            )
        )

        response = commit(
            self.commit_request(
                created["lease"]["lease_id"],
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Completed item.",
                    "items_updated": [
                        {
                            "item_id": "item-schema",
                            "status": "done",
                            "result_summary": "Task item schema is active.",
                        }
                    ],
                },
                event_id="evt-progress-update-item",
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT status, result_summary, completed_at FROM task_items WHERE item_id = 'item-schema'"
            ).fetchone()
        self.assertEqual(row[:2], ("done", "Task item schema is active."))
        self.assertIsNotNone(row[2])
        self.assertIn(
            {"type": "task_item_updated", "target_type": "task_item", "target_id": "item-schema"},
            response["effects"],
        )

    def test_commit_handoff_returns_safe_to_stop(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = intent_response["lease"]["task_id"]
        run_id = intent_response["lease"]["run_id"]

        response = commit(
            self.commit_request(
                intent_response["lease"]["lease_id"],
                "handoff",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "current_state": "P0 implementation is in progress.",
                    "next_action": "Continue with CLI adapter.",
                    "open_items": [],
                    "open_questions": [],
                    "important_refs": [],
                    "source_refs": [],
                },
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["directive"]["type"], "safe_to_stop")
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT status, current_state, next_action FROM handoffs WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        self.assertEqual(row, ("current", "P0 implementation is in progress.", "Continue with CLI adapter."))

    def test_state_transition_updates_task_status(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = intent_response["lease"]["task_id"]

        response = commit(
            self.commit_request(
                intent_response["lease"]["lease_id"],
                "state",
                {
                    "target_type": "task",
                    "target_id": task_id,
                    "from_status": "active",
                    "to_status": "paused",
                    "reason": "Waiting for user review.",
                },
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(row, ("paused",))

    def intent_payload(self) -> dict[str, object]:
        return {
            "intent_text": "Implement protocol P0",
            "classification": {"persistence": "normal", "confidence": 0.9, "reason": "test"},
            "task_hint": {"title": "Protocol P0", "task_id": None, "parent_task_id": None},
        }

    def commit_request(
        self, lease_id: str, kind: str, payload: dict[str, object], event_id: str | None = None
    ) -> dict[str, object]:
        event_id = event_id or f"evt-{kind}-{payload.get('target_id') or payload.get('run_id') or 'new'}"
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-{event_id}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"key-{event_id}",
            "events": [
                {
                    "event_id": event_id,
                    "kind": kind,
                    "schema_version": f"{kind}.v1",
                    "occurred_at": "2026-05-26T10:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": payload,
                    "evidence": [],
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
