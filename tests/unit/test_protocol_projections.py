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

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])

    def effects(self, event_id: str) -> list[dict[str, str]]:
        with sqlite3.connect(self.sqlite_path) as conn:
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

    def test_commit_intent_creates_task_and_run(self) -> None:
        response = commit(self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload()))

        self.assertTrue(response["ok"])
        task_id = self.task_id(response)
        run_id = self.run_id(response)
        with sqlite3.connect(self.sqlite_path) as conn:
            task = conn.execute("SELECT role, process_level, title FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            run = conn.execute("SELECT status, goal FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()

        self.assertEqual(task, ("normal", "L1", "Protocol P0"))
        self.assertEqual(run, ("active", "Implement protocol P0"))
        self.assertIn("progress", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

    def test_commit_temporary_intent_creates_inbox_task_and_run(self) -> None:
        response = commit(
            self.commit_request(
                self.create_lease(events=["intent"]),
                "intent",
                {
                    "intent_text": "Keep a temporary discussion thread",
                    "classification": {"persistence": "temporary", "confidence": 0.8, "reason": "inbox test"},
                    "task_hint": {"title": "Temporary protocol discussion", "task_id": None, "parent_task_id": None},
                },
                event_id="evt-intent-temporary",
            )
        )

        self.assertTrue(response["ok"])
        task_id = self.task_id(response)
        run_id = self.run_id(response)
        with sqlite3.connect(self.sqlite_path) as conn:
            task = conn.execute(
                """
                SELECT role, process_level, task_kind, retention_policy, visibility, title
                FROM tasks
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
            run = conn.execute("SELECT status, goal FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()

        self.assertEqual(task, ("inbox", "L0", "inbox", "rolling_7d", "implicit", "Temporary protocol discussion"))
        self.assertEqual(run, ("active", "Keep a temporary discussion thread"))

    def test_commit_progress_updates_run_and_returns_next_lease(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "progress",
                {"task_id": task_id, "run_id": run_id, "summary": "Implemented protocol models."},
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT output_summary FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()
        self.assertEqual(row, ("Implemented protocol models.",))
        self.assertEqual(self.task_id(response), task_id)

    def test_commit_progress_can_complete_run_without_handoff(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Run produced a usable result.",
                    "run_status": "completed",
                },
                event_id="evt-progress-completed",
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT status, output_summary, ended_at FROM task_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        self.assertEqual(row[:2], ("completed", "Run produced a usable result."))
        self.assertIsNotNone(row[2])

    def test_commit_progress_creates_task_items(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
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
            self.effects("evt-progress-create-items"),
        )

    def test_commit_progress_updates_task_items(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)
        created = commit(
            self.commit_request(
                self.lease_id(intent_response),
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
                self.lease_id(created),
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
            self.effects("evt-progress-update-item"),
        )

    def test_commit_progress_skips_invalid_item_update_but_preserves_summary(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Safe summary preserved.",
                    "items_updated": [{"item_id": "", "status": "impossible"}],
                },
                event_id="evt-progress-skip-invalid-item-update",
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            summary = conn.execute("SELECT summary_text FROM task_summaries WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(summary, ("Safe summary preserved.",))

    def test_commit_progress_rejects_terminal_task_item_reopen(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)
        created = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Completed item.",
                    "items_created": [
                        {"item_id": "item-schema", "title": "Implement task item schema", "status": "done"}
                    ],
                },
                event_id="evt-progress-create-done-item",
            )
        )

        response = commit(
            self.commit_request(
                self.lease_id(created),
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Attempted to reopen terminal item.",
                    "items_updated": [{"item_id": "item-schema", "status": "doing"}],
                },
                event_id="evt-progress-reopen-done-item",
            )
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_state_transition")
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status FROM task_items WHERE item_id = 'item-schema'").fetchone()
        self.assertEqual(row, ("done",))

    def test_commit_handoff_returns_safe_to_stop(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
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
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "none")
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
        task_id = self.task_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
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

    def test_state_transition_archives_active_task(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "state",
                {
                    "target_type": "task",
                    "target_id": task_id,
                    "from_status": "active",
                    "to_status": "archived",
                    "reason": "Temporary branch no longer needed.",
                },
                event_id="evt-state-archive",
            )
        )

        self.assertTrue(response["ok"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status, archived_at FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(row[0], "archived")
        self.assertIsNotNone(row[1])

    def test_state_promotes_inbox_task_to_normal_task(self) -> None:
        intent_response = commit(
            self.commit_request(
                self.create_lease(events=["intent"]),
                "intent",
                {
                    "intent_text": "Explore a topic until it becomes real work",
                    "classification": {"persistence": "temporary", "confidence": 0.8, "reason": "inbox test"},
                    "task_hint": {"title": "Temporary topic", "task_id": None, "parent_task_id": None},
                },
                event_id="evt-intent-promote-temporary",
            )
        )
        task_id = self.task_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "state",
                {
                    "target_type": "task",
                    "target_id": task_id,
                    "to_role": "normal",
                    "to_process_level": "L1",
                    "to_visibility": "normal",
                    "to_retention_policy": "until_closed",
                    "reason": "User wants to continue as formal work.",
                },
                event_id="evt-state-promote-temporary",
            )
        )

        self.assertTrue(response["ok"])
        self.assertIn(
            {"type": "task_promoted", "target_type": "task", "target_id": task_id},
            self.effects("evt-state-promote-temporary"),
        )
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT role, process_level, visibility, retention_policy FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        self.assertEqual(row, ("normal", "L1", "normal", "until_closed"))

    def test_commit_asset_records_asset_candidate_and_task_relationship(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "asset",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "title": "Protocol design",
                    "asset_kind": "design_doc",
                    "path": "docs/protocol.md",
                    "summary": "Final protocol design for Agent exchange.",
                    "status": "current",
                },
                event_id="evt-asset-protocol-design",
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "applied")
        self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        asset_effects = self.effects("evt-asset-protocol-design")
        asset_id = next(effect["target_id"] for effect in asset_effects if effect["target_type"] == "asset")
        with sqlite3.connect(self.sqlite_path) as conn:
            asset = conn.execute(
                "SELECT asset_type, title, lifecycle_status, current_path FROM assets WHERE asset_id = ?",
                (asset_id,),
            ).fetchone()
            candidate = conn.execute(
                """
                SELECT source_type, source_id, title, summary, context_policy
                FROM context_candidates
                WHERE candidate_id = ?
                """,
                (f"asset:{asset_id}",),
            ).fetchone()
            edge = conn.execute(
                """
                SELECT relationship_type, status
                FROM relationship_edges
                WHERE edge_id = ?
                """,
                (f"edge-task-{task_id}-asset-{asset_id}",),
            ).fetchone()

        self.assertEqual(asset, ("design_doc", "Protocol design", "current", "docs/protocol.md"))
        self.assertEqual(
            candidate,
            (
                "asset",
                asset_id,
                "Protocol design",
                "Final protocol design for Agent exchange.",
                "task-related",
            ),
        )
        self.assertEqual(edge, ("produced_asset", "active"))
        self.assertIn({"type": "asset_recorded", "target_type": "asset", "target_id": asset_id}, asset_effects)

    def test_commit_decision_records_candidate_and_task_relationship_without_decision_table(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = self.task_id(intent_response)
        run_id = self.run_id(intent_response)

        response = commit(
            self.commit_request(
                self.lease_id(intent_response),
                "decision",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "title": "Protocol entry",
                    "decision": "Use shape-native commit for LLM-facing protocol.",
                    "reason": "Internal event kinds should not leak into model-facing instructions.",
                    "scope": "agent-protocol",
                },
                event_id="evt-decision-shape-native",
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "applied")
        decision_id = "decision-evt-decision-shape-native"
        with sqlite3.connect(self.sqlite_path) as conn:
            candidate = conn.execute(
                """
                SELECT source_type, source_id, title, summary, domains
                FROM context_candidates
                WHERE candidate_id = ?
                """,
                (f"decision:{decision_id}",),
            ).fetchone()
            edge = conn.execute(
                """
                SELECT relationship_type, status
                FROM relationship_edges
                WHERE edge_id = ?
                """,
                (f"edge-task-{task_id}-decision-{decision_id}",),
            ).fetchone()
            decision_table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='decisions'"
            ).fetchone()

        self.assertEqual(candidate[0:3], ("decision", decision_id, "Protocol entry"))
        self.assertIn("Use shape-native commit", candidate[3])
        self.assertIn("scope:agent-protocol", candidate[4])
        self.assertEqual(edge, ("made_decision", "active"))
        self.assertIsNone(decision_table)
        self.assertIn(
            {"type": "decision_recorded", "target_type": "decision", "target_id": decision_id},
            self.effects("evt-decision-shape-native"),
        )

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
