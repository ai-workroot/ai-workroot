from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.commands.agent_exchange import build_commit_request_from_shape
from ai_workroot.protocol.controller import commit, sync
from ai_workroot.protocol.lease import create_lease
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolTaskContinuityV2Test(unittest.TestCase):
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

    def test_task_close_uses_closed_with_close_reason_completed(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)

        response = commit(
            self.state_request(
                lease_id=self.lease_id(intent),
                event_id="evt-state-close-completed",
                payload={
                    "target_type": "task",
                    "target_id": task_id,
                    "from_status": "active",
                    "to_status": "closed",
                    "close_reason": "completed",
                    "reason": "The task objective is complete.",
                },
            )
        )

        self.assertEqual(response["result"]["status"], "applied")
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status, metadata_json FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(row[0], "closed")
        self.assertEqual(json.loads(row[1])["close_reason"], "completed")

    def test_task_completed_status_is_rejected(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)

        response = commit(
            self.state_request(
                lease_id=self.lease_id(intent),
                event_id="evt-state-completed-invalid",
                payload={
                    "target_type": "task",
                    "target_id": task_id,
                    "from_status": "active",
                    "to_status": "completed",
                    "reason": "Completed is not a Task status.",
                },
            )
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "invalid_state_transition")
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(row, ("active",))

    def test_task_run_incomplete_requires_handoff(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        response = commit(
            self.progress_request(
                lease_id=self.lease_id(intent),
                task_id=task_id,
                run_id=run_id,
                summary="Work stopped with open steps.",
                run_status="incomplete",
            )
        )

        self.assertEqual(response["result"]["status"], "applied")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertIn("continuation", response["workroot_contract"]["commit_contract"]["required_before_stop"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()
        self.assertEqual(row, ("incomplete",))

    def test_task_run_completed_returns_safe_to_stop_without_required_handoff(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        response = commit(
            self.progress_request(
                lease_id=self.lease_id(intent),
                task_id=task_id,
                run_id=run_id,
                summary="Run completed.",
                run_status="completed",
            )
        )

        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "none")
        self.assertEqual(response["workroot_contract"]["commit_contract"]["required_before_stop"], [])
        self.assertIsNone(response["workroot_contract"]["commit_contract"]["lease_id"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT status FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()
        self.assertEqual(row, ("completed",))

    def test_temporary_promote_mutates_same_task_metadata(self) -> None:
        intent = self.create_task(persistence="temporary", title="Temporary Discussion")
        task_id = self.task_id(intent)
        before_count = self.count_rows("tasks")

        response = commit(
            self.state_request(
                lease_id=self.lease_id(intent),
                event_id="evt-state-promote-same-task",
                payload={
                    "target_type": "task",
                    "target_id": task_id,
                    "to_role": "normal",
                    "to_process_level": "L1",
                    "to_visibility": "normal",
                    "to_retention_policy": "until_closed",
                    "to_task_kind": "task",
                    "reason": "Temporary exploration became durable work.",
                },
            )
        )

        self.assertEqual(response["result"]["status"], "applied")
        self.assertEqual(self.count_rows("tasks"), before_count)
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT role, process_level, visibility, retention_policy, task_kind FROM tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        self.assertEqual(row, ("normal", "L1", "normal", "until_closed", "task"))

    def test_repeated_start_work_attaches_to_existing_task(self) -> None:
        first = self.create_task(title="Six-week pricing and onboarding cadence")
        task_id = self.task_id(first)
        run_id = self.run_id(first)
        intent_lease = self.create_workroot_intent_lease("lease-repeat-intent")

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-repeat-intent",
                "exchange_lease_id": intent_lease,
                "idempotency_key": "idem-repeat-intent",
                "events": [
                    {
                        "event_id": "evt-repeat-intent",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-28T02:00:00Z",
                        "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-2"},
                        "confirmation": {"status": "agent_observed", "confirmed_by": None},
                        "payload": {
                            "intent_text": "Continue the six-week pricing and onboarding cadence.",
                            "classification": {"persistence": "normal"},
                            "task_hint": {
                                "title": "Six-week pricing and onboarding cadence",
                                "task_id": None,
                                "parent_task_id": None,
                            },
                            "source_refs": [],
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertEqual(response["result"]["status"], "applied")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], task_id)
        self.assertEqual(response["workroot_contract"]["state_refs"]["run_ref"], run_id)
        self.assertEqual(self.count_rows("tasks"), 1)
        self.assertEqual(self.count_rows("task_runs"), 1)
        with sqlite3.connect(self.sqlite_path) as conn:
            effects = conn.execute(
                """
                SELECT effect_type, target_type, target_id
                FROM protocol_event_effects
                WHERE event_id = 'evt-repeat-intent'
                ORDER BY effect_type
                """
            ).fetchall()
        self.assertIn(("task_attached", "task", task_id), effects)

    def test_checkpoint_shape_done_open_blocked_is_adapter_only(self) -> None:
        request = build_commit_request_from_shape(
            shape="checkpoint",
            lease_id="lease-progress",
            agent_name="codex",
            summary="Mapped shorthand.",
            done=("Finish response envelope",),
            open=("Implement focus resolver",),
            blocked=("Wait for user decision",),
            occurred_at="2026-05-28T00:00:00Z",
        )

        payload = request["events"][0]["payload"]
        self.assertNotIn("done", payload)
        self.assertNotIn("open", payload)
        self.assertNotIn("blocked", payload)
        self.assertEqual(
            payload["items_created"],
            [
                {
                    "title": "Finish response envelope",
                    "status": "done",
                    "result_summary": "Finish response envelope",
                },
                {"title": "Implement focus resolver", "status": "todo", "result_summary": None},
                {"title": "Wait for user decision", "status": "blocked", "result_summary": None},
            ],
        )

    def test_checkpoint_items_dedupe_by_title_under_task(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        first = commit(
            self.raw_progress_request(
                lease_id=self.lease_id(intent),
                task_id=task_id,
                run_id=run_id,
                payload={
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Initial checkpoint.",
                    "items_created": [
                        {
                            "title": "Review founder operating plan",
                            "status": "done",
                            "result_summary": "Initial review complete.",
                        }
                    ],
                },
            )
        )
        second = commit(
            self.raw_progress_request(
                lease_id=self.lease_id(first),
                task_id=task_id,
                run_id=run_id,
                payload={
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Refreshed checkpoint.",
                    "items_created": [
                        {
                            "title": "Review founder operating plan",
                            "status": "done",
                            "result_summary": "Review refreshed with risk checkpoint.",
                        }
                    ],
                },
            )
        )

        self.assertEqual(second["result"]["status"], "applied")
        with sqlite3.connect(self.sqlite_path) as conn:
            rows = conn.execute(
                """
                SELECT title, status, result_summary
                FROM task_items
                WHERE workroot_id = 'wr_demo' AND task_id = ?
                """,
                (task_id,),
            ).fetchall()
        self.assertEqual(rows, [("Review founder operating plan", "done", "Review refreshed with risk checkpoint.")])

    def test_checkpoint_items_ignore_empty_placeholders_even_in_raw_payload(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        response = commit(
            self.raw_progress_request(
                lease_id=self.lease_id(intent),
                task_id=task_id,
                run_id=run_id,
                payload={
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Checkpoint with placeholder item values.",
                    "items_created": [
                        {"title": "None.", "status": "blocked", "result_summary": None},
                        {"title": "N/A", "status": "todo", "result_summary": None},
                        {"title": "Keep the real follow-up item", "status": "todo", "result_summary": None},
                    ],
                },
            )
        )

        self.assertEqual(response["result"]["status"], "applied")
        with sqlite3.connect(self.sqlite_path) as conn:
            rows = conn.execute(
                """
                SELECT title, status
                FROM task_items
                WHERE workroot_id = 'wr_demo' AND task_id = ?
                """,
                (task_id,),
            ).fetchall()
        self.assertEqual(rows, [("Keep the real follow-up item", "todo")])

    def test_projection_rejects_progress_shorthand_if_it_bypasses_adapter(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        response = commit(
            self.raw_progress_request(
                lease_id=self.lease_id(intent),
                task_id=task_id,
                run_id=run_id,
                payload={"task_id": task_id, "run_id": run_id, "summary": "Bad shorthand.", "done": ["bad"]},
            )
        )

        self.assertEqual(response["result"]["status"], "quarantined")
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT summary_text FROM task_summaries WHERE summary_text = 'Bad shorthand.'"
            ).fetchone()
        self.assertIsNone(row)

    def test_asset_commit_uses_path_identity_and_indexes_text(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        asset_path = self.user_dir / "results" / "founder-operating-plan.md"
        asset_path.parent.mkdir()
        asset_path.write_text("# Founder Operating Plan\n\nInitial pricing cadence.\n", encoding="utf-8")

        first = commit(
            self.asset_request(
                lease_id=self.lease_id(intent),
                event_id="evt-asset-first",
                task_id=task_id,
                run_id=run_id,
                path="results/founder-operating-plan.md",
                summary="Initial founder operating plan.",
            )
        )
        asset_path.write_text(
            "# Founder Operating Plan\n\nUpdated pricing cadence and onboarding risk.\n", encoding="utf-8"
        )
        second = commit(
            self.asset_request(
                lease_id=self.lease_id(first),
                event_id="evt-asset-second",
                task_id=task_id,
                run_id=run_id,
                path="results/founder-operating-plan.md",
                summary="Updated founder operating plan.",
            )
        )

        self.assertEqual(second["result"]["status"], "applied")
        with sqlite3.connect(self.sqlite_path) as conn:
            assets = conn.execute(
                "SELECT asset_id, current_path, content_hash FROM assets WHERE workroot_id = 'wr_demo'"
            ).fetchall()
            indexed_files = conn.execute("SELECT relative_path, source_type, source_id FROM indexed_files").fetchall()
            indexed_chunks = conn.execute("SELECT body FROM indexed_chunks").fetchall()
            fts_count = conn.execute("SELECT COUNT(*) FROM indexed_chunks_fts").fetchone()[0]

        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0][1], "results/founder-operating-plan.md")
        self.assertTrue(assets[0][2])
        self.assertEqual(indexed_files, [("results/founder-operating-plan.md", "asset", assets[0][0])])
        self.assertEqual(len(indexed_chunks), 1)
        self.assertIn("Updated pricing cadence", indexed_chunks[0][0])
        self.assertEqual(fts_count, 1)

    def test_asset_commit_rejects_existing_path_owner_conflict_without_relinking(self) -> None:
        first = self.create_task(title="Service Month Plan")
        task_a = self.task_id(first)
        run_a = self.run_id(first)
        asset_path = self.user_dir / "results" / "service-month-plan.md"
        asset_path.parent.mkdir()
        asset_path.write_text("# Service Month Plan\n\nMain operating plan.\n", encoding="utf-8")
        first_asset = commit(
            self.asset_request(
                lease_id=self.lease_id(first),
                event_id="evt-asset-owner-original",
                task_id=task_a,
                run_id=run_a,
                path="results/service-month-plan.md",
                summary="Main service operating plan.",
            )
        )
        second = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-owner-conflict-task-b",
                "exchange_lease_id": self.create_workroot_intent_lease("lease-owner-conflict-task-b"),
                "idempotency_key": "idem-owner-conflict-task-b",
                "events": [
                    {
                        "event_id": "evt-owner-conflict-task-b",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-28T03:00:00Z",
                        "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-2"},
                        "confirmation": {"status": "agent_observed", "confirmed_by": None},
                        "payload": {
                            "intent_text": "Prepare a separate hiring checklist.",
                            "classification": {"persistence": "normal", "process_level": "L1"},
                            "task_hint": {
                                "title": "Hiring Checklist",
                                "task_id": None,
                                "parent_task_id": None,
                            },
                            "source_refs": [],
                        },
                        "evidence": [],
                    }
                ],
            }
        )
        task_b = self.task_id(second)
        run_b = self.run_id(second)

        conflict = commit(
            self.asset_request(
                lease_id=self.lease_id(second),
                event_id="evt-asset-owner-conflict",
                task_id=task_b,
                run_id=run_b,
                path="results/service-month-plan.md",
                summary="This commit carries the wrong task lease.",
            )
        )

        self.assertEqual(first_asset["result"]["status"], "applied")
        self.assertEqual(conflict["result"]["status"], "rejected")
        self.assertIn("asset_owner_conflict", conflict["result"]["warnings"])
        with sqlite3.connect(self.sqlite_path) as conn:
            asset_id = conn.execute(
                "SELECT asset_id FROM assets WHERE current_path = 'results/service-month-plan.md'"
            ).fetchone()[0]
            owners = conn.execute(
                """
                SELECT task_node.target_id
                FROM relationship_edges edge
                JOIN relationship_nodes task_node
                  ON task_node.workroot_id = edge.workroot_id
                 AND task_node.node_id = edge.from_node_id
                 AND task_node.target_type = 'task'
                JOIN relationship_nodes asset_node
                  ON asset_node.workroot_id = edge.workroot_id
                 AND asset_node.node_id = edge.to_node_id
                 AND asset_node.target_type = 'asset'
                 AND asset_node.target_id = ?
                WHERE edge.workroot_id = 'wr_demo'
                  AND edge.relationship_type = 'produced_asset'
                  AND COALESCE(edge.status, 'active') = 'active'
                ORDER BY task_node.target_id
                """,
                (asset_id,),
            ).fetchall()
        self.assertEqual(owners, [(task_a,)])
        self.assertNotIn((task_b,), owners)
        friction_log = Path(self.registration.state_directory) / "logs/protocol-friction.jsonl"
        friction_events = [json.loads(line) for line in friction_log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(friction_events[-1]["code"], "asset_owner_conflict")
        self.assertEqual(friction_events[-1]["stage"], "projection")
        self.assertEqual(friction_events[-1]["shape"], "asset")

    def test_asset_commit_indexes_text_with_explicit_ai_workroot_home(self) -> None:
        explicit_home = Path(self.tmp.name) / "explicit-home"
        explicit_user_dir = Path(self.tmp.name) / "explicit-workspace"
        explicit_user_dir.mkdir()
        initialize_environment(explicit_home)
        explicit_registration = register_workroot(
            explicit_home,
            workroot_id="wr_explicit",
            name="Explicit",
            user_directory=explicit_user_dir,
        )
        explicit_sqlite_path = workroot_sqlite_path(Path(explicit_registration.state_directory))
        initialize_workroot_sqlite(explicit_sqlite_path)
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-explicit-asset",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(explicit_user_dir),
                "reason": "before_work",
                "query": "Create explicit asset task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            },
            ai_workroot_home=explicit_home,
        )
        intent = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-intent-explicit-asset",
                "exchange_lease_id": self.lease_id(sync_response),
                "idempotency_key": "idem-intent-explicit-asset",
                "events": [
                    {
                        "event_id": "evt-intent-explicit-asset",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-28T00:00:00Z",
                        "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                        "confirmation": {"status": "agent_observed", "confirmed_by": None},
                        "payload": {
                            "intent_text": "Create explicit asset task.",
                            "classification": {"persistence": "normal", "process_level": "L1"},
                            "task_hint": {"title": "Explicit Asset Task", "task_id": None, "parent_task_id": None},
                            "source_refs": [],
                        },
                        "evidence": [],
                    }
                ],
            },
            ai_workroot_home=explicit_home,
        )
        asset_path = explicit_user_dir / "results" / "explicit-asset.md"
        asset_path.parent.mkdir()
        asset_path.write_text("# Explicit Asset\n\nIndexed through explicit home.\n", encoding="utf-8")

        response = commit(
            self.asset_request(
                lease_id=self.lease_id(intent),
                event_id="evt-explicit-asset",
                task_id=self.task_id(intent),
                run_id=self.run_id(intent),
                path="results/explicit-asset.md",
                summary="Explicit asset indexed.",
            ),
            ai_workroot_home=explicit_home,
        )

        self.assertEqual(response["result"]["status"], "applied")
        with sqlite3.connect(explicit_sqlite_path) as conn:
            indexed_files = conn.execute("SELECT relative_path, source_type FROM indexed_files").fetchall()
            indexed_chunks = conn.execute("SELECT body FROM indexed_chunks").fetchall()
        self.assertEqual(indexed_files, [("results/explicit-asset.md", "asset")])
        self.assertEqual(len(indexed_chunks), 1)
        self.assertIn("Indexed through explicit home", indexed_chunks[0][0])

    def test_asset_commit_rejects_path_escape_without_recording_asset(self) -> None:
        intent = self.create_task()
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)

        response = commit(
            self.asset_request(
                lease_id=self.lease_id(intent),
                event_id="evt-asset-escape",
                task_id=task_id,
                run_id=run_id,
                path="../outside.md",
                summary="Escaping path must not become a durable asset.",
            )
        )

        self.assertEqual(response["result"]["status"], "quarantined")
        self.assertIn("projection_failed", response["result"]["warnings"])
        with sqlite3.connect(self.sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM indexed_files").fetchone()[0], 0)

    def test_workroot_scope_asset_commit_indexes_without_task_relationship(self) -> None:
        lease_id = self.create_workroot_asset_lease("lease-workroot-asset")
        asset_path = self.user_dir / "results" / "executive-summary.md"
        asset_path.parent.mkdir()
        asset_path.write_text("# Executive Summary\n\nCross-task synthesis.\n", encoding="utf-8")

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-workroot-asset",
                "exchange_lease_id": lease_id,
                "idempotency_key": "idem-workroot-asset",
                "events": [
                    {
                        "event_id": "evt-workroot-asset",
                        "kind": "asset",
                        "schema_version": "asset.v1",
                        "occurred_at": "2026-05-28T02:00:00Z",
                        "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                        "confirmation": {"status": "agent_observed", "confirmed_by": None},
                        "payload": {
                            "title": "Executive Summary",
                            "asset_kind": "document",
                            "path": "results/executive-summary.md",
                            "summary": "Cross-task synthesis asset.",
                            "status": "current",
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertEqual(response["result"]["status"], "applied")
        self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)
        with sqlite3.connect(self.sqlite_path) as conn:
            assets = conn.execute("SELECT title, current_path FROM assets").fetchall()
            candidates = conn.execute("SELECT source_type, title, domains FROM context_candidates").fetchall()
            indexed_files = conn.execute("SELECT relative_path, source_type FROM indexed_files").fetchall()
            relationship_count = conn.execute("SELECT COUNT(*) FROM relationship_edges").fetchone()[0]
        self.assertEqual(assets, [("Executive Summary", "results/executive-summary.md")])
        self.assertEqual(candidates, [("asset", "Executive Summary", "workroot asset:document")])
        self.assertEqual(indexed_files, [("results/executive-summary.md", "asset")])
        self.assertEqual(relationship_count, 0)

    def create_task(self, *, persistence: str = "normal", title: str = "Protocol Task") -> dict[str, object]:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": f"req-sync-{persistence}-{title}",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": f"Design {title}",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        return commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": f"req-intent-{persistence}-{title}",
                "exchange_lease_id": self.lease_id(sync_response),
                "idempotency_key": f"idem-intent-{persistence}-{title}",
                "events": [
                    {
                        "event_id": f"evt-intent-{persistence}-{title}",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-28T00:00:00Z",
                        "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                        "confirmation": {"status": "agent_observed", "confirmed_by": None},
                        "payload": {
                            "intent_text": f"Implement {title}.",
                            "classification": {"persistence": persistence, "process_level": "L1"},
                            "task_hint": {"title": title, "task_id": None, "parent_task_id": None},
                            "source_refs": [],
                        },
                        "evidence": [],
                    }
                ],
            }
        )

    def progress_request(
        self,
        *,
        lease_id: str,
        task_id: str,
        run_id: str,
        summary: str,
        run_status: str,
    ) -> dict[str, object]:
        return self.raw_progress_request(
            lease_id=lease_id,
            task_id=task_id,
            run_id=run_id,
            payload={"task_id": task_id, "run_id": run_id, "summary": summary, "run_status": run_status},
        )

    def raw_progress_request(
        self,
        *,
        lease_id: str,
        task_id: str,
        run_id: str,
        payload: dict[str, object],
    ) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-progress-{payload.get('summary')}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"idem-progress-{payload.get('summary')}",
            "events": [
                {
                    "event_id": f"evt-progress-{payload.get('summary')}",
                    "kind": "progress",
                    "schema_version": "progress.v1",
                    "occurred_at": "2026-05-28T00:30:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": payload,
                    "evidence": [],
                }
            ],
        }

    def state_request(self, *, lease_id: str, event_id: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-{event_id}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"idem-{event_id}",
            "events": [
                {
                    "event_id": event_id,
                    "kind": "state",
                    "schema_version": "state.v1",
                    "occurred_at": "2026-05-28T01:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": payload,
                    "evidence": [],
                }
            ],
        }

    def asset_request(
        self,
        *,
        lease_id: str,
        event_id: str,
        task_id: str,
        run_id: str,
        path: str,
        summary: str,
    ) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-{event_id}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"idem-{event_id}",
            "events": [
                {
                    "event_id": event_id,
                    "kind": "asset",
                    "schema_version": "asset.v1",
                    "occurred_at": "2026-05-28T02:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": {
                        "task_id": task_id,
                        "run_id": run_id,
                        "title": "Founder Operating Plan",
                        "asset_kind": "document",
                        "path": path,
                        "summary": summary,
                        "status": "current",
                    },
                    "evidence": [],
                }
            ],
        }

    def count_rows(self, table: str) -> int:
        with sqlite3.connect(self.sqlite_path) as conn:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def create_workroot_intent_lease(self, lease_id: str) -> str:
        with sqlite3.connect(self.sqlite_path) as conn:
            create_lease(
                conn,
                workroot_id="wr_demo",
                scope="workroot",
                task_id=None,
                run_id=None,
                allowed_events=["intent"],
                lease_id=lease_id,
            )
            conn.commit()
        return lease_id

    def create_workroot_asset_lease(self, lease_id: str) -> str:
        with sqlite3.connect(self.sqlite_path) as conn:
            create_lease(
                conn,
                workroot_id="wr_demo",
                scope="workroot",
                task_id=None,
                run_id=None,
                allowed_events=["asset"],
                lease_id=lease_id,
            )
            conn.commit()
        return lease_id

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])


if __name__ == "__main__":
    unittest.main()
