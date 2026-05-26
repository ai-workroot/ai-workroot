from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol.controller import commit, sync
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class AgentProtocolLoopTest(unittest.TestCase):
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
        initialize_workroot_sqlite(workroot_sqlite_path(Path(self.registration.state_directory)))
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_next_agent_can_continue_from_latest_handoff(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-before-work",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement protocol P0 continuity.",
            }
        )

        self.assertTrue(first_sync["ok"])
        self.assertEqual(first_sync["directive"]["type"], "commit_required")
        intent = commit(
            self.commit_request(
                first_sync["lease"]["lease_id"],
                "intent",
                "evt-intent-loop",
                {
                    "intent_text": "Implement protocol P0 continuity",
                    "classification": {"persistence": "normal", "confidence": 0.9, "reason": "integration"},
                    "task_hint": {"title": "Protocol P0 Continuity", "task_id": None, "parent_task_id": None},
                },
            )
        )
        self.assertTrue(intent["ok"])
        task_id = intent["lease"]["task_id"]
        run_id = intent["lease"]["run_id"]

        progress = commit(
            self.commit_request(
                intent["lease"]["lease_id"],
                "progress",
                "evt-progress-loop",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Continuity loader is the next missing piece.",
                    "items_created": [
                        {
                            "item_id": "item-open-loop",
                            "title": "Wire continuity loader",
                            "status": "doing",
                            "order": 10,
                        },
                        {
                            "item_id": "item-done-loop",
                            "title": "Verify projection loop",
                            "status": "done",
                            "order": 20,
                            "result_summary": "Projection loop is green.",
                        },
                    ],
                    "open_questions": [],
                    "source_refs": [],
                },
            )
        )
        self.assertTrue(progress["ok"])

        handoff = commit(
            self.commit_request(
                progress["lease"]["lease_id"],
                "handoff",
                "evt-handoff-loop",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "current_state": "Projection loop is green.",
                    "next_action": "Wire sync to load the latest continuity package.",
                    "open_items": [],
                    "open_questions": [],
                    "important_refs": [],
                    "source_refs": [],
                },
            )
        )
        self.assertTrue(handoff["ok"])
        self.assertEqual(handoff["directive"]["type"], "safe_to_stop")

        next_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-continue",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "continue",
                "known_state": {"task_id": task_id, "run_id": run_id},
            }
        )

        self.assertTrue(next_sync["ok"])
        self.assertEqual(next_sync["directive"]["type"], "continue_task")
        self.assertIn("Continuity loader is the next missing piece.", next_sync["context"]["brief"])
        self.assertIn(
            {
                "type": "handoff",
                "id": "handoff-evt-handoff-loop",
                "role": "next_step",
                "summary": "Wire sync to load the latest continuity package.",
            },
            next_sync["context"]["refs"],
        )
        self.assertIn(
            {
                "type": "task_item",
                "id": "item-open-loop",
                "role": "open",
                "summary": "Wire continuity loader",
            },
            next_sync["context"]["refs"],
        )
        self.assertIn(
            {
                "type": "task_item",
                "id": "item-done-loop",
                "role": "recent_done",
                "summary": "Verify projection loop: Projection loop is green.",
            },
            next_sync["context"]["refs"],
        )

    def commit_request(
        self,
        lease_id: str,
        kind: str,
        event_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
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
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-loop"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": payload,
                    "evidence": [],
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()
