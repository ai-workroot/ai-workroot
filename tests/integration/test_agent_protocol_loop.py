from __future__ import annotations

import os
import sqlite3
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

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])

    def effects(self, event_id: str) -> list[dict[str, str]]:
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            rows = conn.execute(
                """
                SELECT effect_type, target_type, target_id
                FROM protocol_event_effects
                WHERE event_id = ?
                ORDER BY effect_id
                """,
                (event_id,),
            ).fetchall()
        return [{"type": row[0], "target_type": row[1], "target_id": row[2]} for row in rows]

    def test_next_agent_can_continue_from_latest_handoff(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-before-work",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement protocol P0 continuity.",
                "work_signal": {"phase": "planning", "work_kind": "task", "intended_action": "plan"},
            }
        )

        self.assertTrue(first_sync["ok"])
        self.assertEqual(first_sync["workroot_contract"]["next_exchange"]["action"], "commit")
        intent = commit(
            self.commit_request(
                self.lease_id(first_sync),
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
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        progress = commit(
            self.commit_request(
                self.lease_id(intent),
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
                self.lease_id(progress),
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
        self.assertEqual(handoff["workroot_contract"]["next_exchange"]["action"], "none")

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
        self.assertEqual(next_sync["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertIn("Continuity loader is the next missing piece.", next_sync["workroot_view"]["task_brief"])
        self.assertIn(
            {
                "type": "handoff",
                "id": "handoff-evt-handoff-loop",
                "role": "next_step",
                "summary": "Wire sync to load the latest continuity package.",
            },
            next_sync["workroot_view"]["refs"],
        )
        self.assertIn(
            {
                "type": "task_item",
                "id": "item-open-loop",
                "role": "open",
                "summary": "Wire continuity loader",
            },
            next_sync["workroot_view"]["refs"],
        )
        self.assertIn(
            {
                "type": "task_item",
                "id": "item-done-loop",
                "role": "recent_done",
                "summary": "Verify projection loop: Projection loop is green.",
            },
            next_sync["workroot_view"]["refs"],
        )

    def test_temporary_task_can_resume_and_promote_to_normal_work(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-temporary",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Explore a temporary topic.",
                "work_signal": {"phase": "planning", "work_kind": "inbox", "intended_action": "preserve"},
            }
        )
        intent = commit(
            self.commit_request(
                self.lease_id(first_sync),
                "intent",
                "evt-intent-temporary-loop",
                {
                    "intent_text": "Explore a temporary topic",
                    "classification": {"persistence": "temporary", "confidence": 0.8, "reason": "integration"},
                    "task_hint": {"title": "Temporary topic", "task_id": None, "parent_task_id": None},
                },
            )
        )
        self.assertTrue(intent["ok"])
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        progress = commit(
            self.commit_request(
                self.lease_id(intent),
                "progress",
                "evt-progress-temporary-loop",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Temporary topic has enough structure to continue.",
                    "items_created": [
                        {"item_id": "item-temporary-open", "title": "Decide whether to promote", "status": "todo"}
                    ],
                },
            )
        )
        self.assertTrue(progress["ok"])
        handoff = commit(
            self.commit_request(
                self.lease_id(progress),
                "handoff",
                "evt-handoff-temporary-loop",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "current_state": "Temporary topic captured.",
                    "next_action": "Promote if user confirms this is real work.",
                    "open_items": [],
                    "open_questions": [],
                    "important_refs": [],
                    "source_refs": [],
                },
            )
        )
        self.assertTrue(handoff["ok"])

        next_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-temporary-continue",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "continue",
                "known_state": {"task_id": task_id, "run_id": run_id},
            }
        )
        self.assertIn(
            {"type": "task_item", "id": "item-temporary-open", "role": "open", "summary": "Decide whether to promote"},
            next_sync["workroot_view"]["refs"],
        )

        promoted = commit(
            self.commit_request(
                self.lease_id(next_sync),
                "state",
                "evt-state-promote-temporary-loop",
                {
                    "target_type": "task",
                    "target_id": task_id,
                    "to_role": "normal",
                    "to_process_level": "L1",
                    "to_visibility": "normal",
                    "to_retention_policy": "until_closed",
                    "reason": "User confirmed continuation.",
                },
            )
        )
        self.assertTrue(promoted["ok"])
        self.assertIn(
            {"type": "task_promoted", "target_type": "task", "target_id": task_id},
            self.effects("evt-state-promote-temporary-loop"),
        )

    def test_next_sync_reports_degraded_continuity_when_run_completed_without_handoff(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-no-handoff",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement recovery.",
                "work_signal": {"phase": "planning", "work_kind": "task", "intended_action": "plan"},
            }
        )
        intent = commit(
            self.commit_request(
                self.lease_id(first_sync),
                "intent",
                "evt-intent-no-handoff",
                {
                    "intent_text": "Implement recovery",
                    "classification": {"persistence": "normal", "confidence": 0.9, "reason": "integration"},
                    "task_hint": {"title": "Recovery", "task_id": None, "parent_task_id": None},
                },
            )
        )
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        progress = commit(
            self.commit_request(
                self.lease_id(intent),
                "progress",
                "evt-progress-no-handoff",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Useful result without handoff.",
                    "run_status": "completed",
                },
            )
        )
        self.assertTrue(progress["ok"])

        continued = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-recover-no-handoff",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "continue",
                "query": "continue",
                "known_state": {"task_id": task_id, "run_id": run_id},
            }
        )

        self.assertTrue(continued["agent_may_continue"])
        self.assertIn("handoff", " ".join(continued["workroot_view"]["warnings"]).lower())

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
