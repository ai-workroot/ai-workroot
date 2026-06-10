from __future__ import annotations

import inspect
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol import controller
from ai_workroot.protocol.controller import commit, sync
from ai_workroot.protocol.events import request_hash, semantic_commit_hash
from ai_workroot.protocol.lease import now_utc
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolCommitReliabilityV2Test(unittest.TestCase):
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

    def test_protocol_commit_batch_schema_has_v2_columns(self) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            batch_columns = {row[1] for row in conn.execute("PRAGMA table_info(protocol_commit_batches)")}
            version_columns = {row[1] for row in conn.execute("PRAGMA table_info(state_versions)")}
            markers = {row[0] for row in conn.execute("SELECT migration_id FROM schema_migrations").fetchall()}

        self.assertTrue(
            {"semantic_hash", "normalized_request_json", "created_at", "error_json"}.issubset(batch_columns)
        )
        self.assertTrue({"updated_by_event_id", "reason"}.issubset(version_columns))
        self.assertIn("009-agent-protocol-task-continuity", markers)

    def test_commit_uses_begin_immediate_transaction(self) -> None:
        source = inspect.getsource(controller.commit)

        self.assertIn("BEGIN IMMEDIATE", source)
        self.assertNotIn('conn.execute("BEGIN")', source)

    def test_same_key_same_semantic_hash_replays_exact_response_even_if_request_id_changes(self) -> None:
        lease_id = self.sync_for_intent_lease()
        first_request = self.intent_request(
            lease_id=lease_id,
            request_id="req-intent-first",
            idempotency_key="idem-semantic-same",
            event_id="evt-intent-generated-a",
        )
        second_request = self.intent_request(
            lease_id=lease_id,
            request_id="req-intent-second",
            idempotency_key="idem-semantic-same",
            event_id="evt-intent-generated-b",
        )

        first = commit(first_request)
        second = commit(second_request)

        self.assertEqual(second, first)
        with sqlite3.connect(self.sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 1)

    def test_commit_batch_stores_raw_request_hash_separately_from_semantic_hash(self) -> None:
        lease_id = self.sync_for_intent_lease()
        request = self.intent_request(
            lease_id=lease_id,
            request_id="req-intent-hash-separation",
            idempotency_key="idem-hash-separation",
            event_id="evt-intent-hash-separation",
        )
        expected_request_hash = request_hash(request)
        expected_semantic_hash, expected_normalized = semantic_commit_hash(request, workroot_id="wr_demo")

        self.assertTrue(commit(request)["ok"])

        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                """
                SELECT request_hash, semantic_hash, normalized_request_json
                FROM protocol_commit_batches
                WHERE idempotency_key = 'idem-hash-separation'
                """
            ).fetchone()
        self.assertEqual(row, (expected_request_hash, expected_semantic_hash, expected_normalized))
        self.assertNotEqual(expected_request_hash, expected_semantic_hash)

    def test_same_key_different_semantic_hash_returns_idempotency_conflict(self) -> None:
        lease_id = self.sync_for_intent_lease()
        first = self.intent_request(lease_id=lease_id, idempotency_key="idem-conflict", intent_text="Build one task")
        second = self.intent_request(
            lease_id=lease_id, idempotency_key="idem-conflict", intent_text="Build another task"
        )

        self.assertTrue(commit(first)["ok"])
        conflict = commit(second)

        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["error"]["code"], "idempotency_key_conflict")
        self.assertEqual(conflict["result"]["status"], "rejected")

    def test_expired_lease_versions_unchanged_safe_progress_applies_with_warning(self) -> None:
        intent = commit(self.intent_request(lease_id=self.sync_for_intent_lease()))
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        progress_lease = self.lease_id(intent)
        self.expire_lease(progress_lease)

        response = commit(
            self.progress_request(
                lease_id=progress_lease,
                task_id=task_id,
                run_id=run_id,
                summary="Expired lease progress safely applied.",
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "applied")
        self.assertTrue(response["result"]["accepted"])
        self.assertTrue(response["result"]["projected"])
        self.assertIn("lease_expired_safe_projection", response["result"]["warnings"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute("SELECT summary_text FROM task_summaries WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(row, ("Expired lease progress safely applied.",))

    def test_expired_lease_versions_changed_requires_resync_without_projection(self) -> None:
        intent = commit(self.intent_request(lease_id=self.sync_for_intent_lease()))
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        progress_lease = self.lease_id(intent)
        self.expire_lease(progress_lease)
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """
                INSERT INTO state_versions(workroot_id, scope, version, updated_at)
                VALUES ('wr_demo', ?, 99, ?)
                ON CONFLICT(workroot_id, scope) DO UPDATE SET version = 99, updated_at = excluded.updated_at
                """,
                (f"task:{task_id}", now_utc()),
            )
            conn.commit()

        response = commit(
            self.progress_request(
                lease_id=progress_lease,
                task_id=task_id,
                run_id=run_id,
                summary="This should not project.",
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        self.assertEqual(response["result"]["status"], "resync_required")
        self.assertFalse(response["result"]["projected"])
        with sqlite3.connect(self.sqlite_path) as conn:
            row = conn.execute(
                "SELECT summary_text FROM task_summaries WHERE summary_text = 'This should not project.'"
            ).fetchone()
        self.assertIsNone(row)

    def test_event_not_allowed_rejection_returns_sync_not_stale_commit(self) -> None:
        intent_lease = self.sync_for_intent_lease()

        response = commit(
            self.progress_request(
                lease_id=intent_lease,
                task_id="task-missing",
                run_id="run-missing",
                summary="This event shape is not allowed by an intent lease.",
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "rejected")
        self.assertEqual(response["result"]["warnings"], ["event_not_allowed"])
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        self.assertEqual(response["workroot_contract"]["commit_contract"]["lease_id"], None)
        self.assertFalse(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
        self.assertEqual(response["workroot_contract"]["commit_contract"]["accepted_shapes"], [])

    def test_missing_lease_rejected_commit_records_protocol_friction(self) -> None:
        request = self.progress_request(
            lease_id="",
            task_id="task-missing",
            run_id="run-missing",
            summary="This locatable durable commit has no lease.",
        )
        request["cwd"] = str(self.user_dir)

        response = commit(request)

        self.assertEqual(response["result"]["status"], "rejected")
        self.assertIn("missing_exchange_lease_id", response["result"]["warnings"])
        friction_log = Path(self.registration.state_directory) / "logs/protocol-friction.jsonl"
        events = [json.loads(line) for line in friction_log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["code"], "missing_exchange_lease_id")
        self.assertEqual(events[0]["action"], "commit")
        self.assertEqual(events[0]["stage"], "lease_guard")
        self.assertEqual(events[0]["resultStatus"], "rejected")
        self.assertEqual(events[0]["requestId"], "req-progress-This locatable durable commit has no lease.")
        self.assertEqual(events[0]["shape"], "checkpoint")

    def test_state_versions_use_local_scopes_and_context_task_scope(self) -> None:
        intent = commit(self.intent_request(lease_id=self.sync_for_intent_lease()))
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        progress = commit(
            self.progress_request(
                lease_id=self.lease_id(intent),
                task_id=task_id,
                run_id=run_id,
                summary="State version scopes should be local.",
            )
        )
        self.assertTrue(progress["ok"])

        with sqlite3.connect(self.sqlite_path) as conn:
            scopes = {row[0] for row in conn.execute("SELECT scope FROM state_versions").fetchall()}

        self.assertIn("event_log", scopes)
        self.assertIn("workroot", scopes)
        self.assertIn(f"task:{task_id}", scopes)
        self.assertIn(f"run:{run_id}", scopes)
        self.assertIn(f"context:task:{task_id}", scopes)
        self.assertNotIn("context", scopes)
        self.assertFalse(any(scope.endswith(":wr_demo") for scope in scopes))

    def sync_for_intent_lease(self) -> str:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-intent",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Design a reliable protocol implementation plan.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])

    def intent_request(
        self,
        *,
        lease_id: str,
        request_id: str = "req-intent",
        idempotency_key: str = "idem-intent",
        event_id: str = "evt-intent-generated",
        intent_text: str = "Design reliable protocol implementation.",
    ) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": request_id,
            "exchange_lease_id": lease_id,
            "idempotency_key": idempotency_key,
            "events": [
                {
                    "event_id": event_id,
                    "kind": "intent",
                    "schema_version": "intent.v1",
                    "occurred_at": "2026-05-28T00:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": {
                        "intent_text": intent_text,
                        "classification": {"persistence": "normal", "process_level": "L1"},
                        "task_hint": {"title": "Protocol Reliability", "task_id": None, "parent_task_id": None},
                        "source_refs": [],
                    },
                    "evidence": [],
                }
            ],
        }

    def progress_request(self, *, lease_id: str, task_id: str, run_id: str, summary: str) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-progress-{summary}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"idem-progress-{summary}",
            "events": [
                {
                    "event_id": f"evt-progress-{abs(hash(summary))}",
                    "kind": "progress",
                    "schema_version": "progress.v1",
                    "occurred_at": "2026-05-28T00:30:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": {"task_id": task_id, "run_id": run_id, "summary": summary},
                    "evidence": [],
                }
            ],
        }

    def expire_lease(self, lease_id: str) -> None:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                "UPDATE exchange_leases SET expires_at = ? WHERE lease_id = ?", ("2026-01-01T00:00:00Z", lease_id)
            )
            conn.commit()


if __name__ == "__main__":
    unittest.main()
