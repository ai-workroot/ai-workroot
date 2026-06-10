from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workroot.commands.agent_exchange import build_commit_request_from_shape
from ai_workroot.protocol.controller import commit, sync
from ai_workroot.protocol.lease import now_utc
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

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])

    def test_sync_returns_directive_lease_context_contract(self) -> None:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-1",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement the Workroot Agent Protocol P0.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["workroot_view"]["focus"], "new_work")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertIn("intent", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
        self.assertEqual(response["workroot_contract"]["state_refs"]["work_ref"], "wr_demo")
        self.assertNotIn("debug", response["workroot_contract"])
        self.assertEqual(response["workroot_view"]["task_brief"], "Implement the Workroot Agent Protocol P0.")
        self.assertEqual(response["workroot_view"]["refs"], [])
        self.assertEqual(response["workroot_view"]["warnings"], [])

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

    def test_sync_validation_error_returns_protocol_error_response(self) -> None:
        response = sync({"request_id": "req-bad-sync"})

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "missing_protocol_version")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        self.assertEqual(response["result"]["warnings"], [])

    def test_commit_validation_error_returns_protocol_error_response(self) -> None:
        response = commit({"request_id": "req-bad-commit"})

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "missing_protocol_version")
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        self.assertEqual(response["result"]["warnings"], [])
        self.assertTrue(response["agent_may_continue"])

    def test_sync_returns_non_blocking_workroot_guidance(self) -> None:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-control",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Design protocol implementation.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertIn("Workroot Guidance", response["workroot_guidance"])
        self.assertIn("Do not repeat it to the user", response["workroot_guidance"])
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "commit")
        self.assertEqual(response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"], ["intent"])

    def test_commit_uses_explicit_ai_workroot_home_for_lease_location(self) -> None:
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
                "request_id": "req-sync-explicit-home",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(explicit_user_dir),
                "reason": "before_work",
                "query": "Create explicit home task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            },
            ai_workroot_home=explicit_home,
        )
        response = commit(
            build_commit_request_from_shape(
                shape="start_work",
                lease_id=self.lease_id(sync_response),
                agent_name="codex",
                title="Explicit home task",
                summary="Explicit home task.",
            ),
            ai_workroot_home=explicit_home,
        )

        self.assertEqual(response["result"]["status"], "applied")
        with sqlite3.connect(explicit_sqlite_path) as conn:
            explicit_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE workroot_id = 'wr_explicit'").fetchone()[0]
        with sqlite3.connect(workroot_sqlite_path(Path(self.registration.state_directory))) as conn:
            default_tasks = conn.execute("SELECT COUNT(*) FROM tasks WHERE workroot_id = 'wr_explicit'").fetchone()[0]
        self.assertEqual(explicit_tasks, 1)
        self.assertEqual(default_tasks, 0)

    def test_auto_shorthand_retry_ignores_generated_occurred_at_for_idempotency(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-auto-retry",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Implement retry auto shorthand task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        lease_id = self.lease_id(sync_response)
        first_request = build_commit_request_from_shape(
            shape="start_work",
            lease_id=lease_id,
            agent_name="codex",
            title="Retry auto shorthand",
            summary="Retry auto shorthand.",
            occurred_at="2026-05-27T00:00:01Z",
        )
        second_request = build_commit_request_from_shape(
            shape="start_work",
            lease_id=lease_id,
            agent_name="codex",
            title="Retry auto shorthand",
            summary="Retry auto shorthand.",
            occurred_at="2026-05-27T00:00:02Z",
        )

        first = commit(first_request)
        second = commit(second_request)

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(second["result"]["status"], "applied")
        self.assertEqual(second, first)

    def test_commit_without_located_workroot_is_not_recorded_and_non_blocking(self) -> None:
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-no-location",
                "idempotency_key": "idem-no-location",
                "atomic_batch": True,
                "events": [
                    {
                        "event_id": "event-no-location",
                        "kind": "progress",
                        "schema_version": "progress.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {"summary": "Cannot locate Workroot."},
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertFalse(response["result"]["accepted"])
        self.assertEqual(response["result"]["status"], "not_recorded")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_commit_batches").fetchone()[0], 0)

    def test_quick_intent_commit_records_batch_without_durable_projection(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-quick-intent",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create a tracked task if durable work starts.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-quick-intent",
                "exchange_lease_id": self.lease_id(sync_response),
                "idempotency_key": "idem-quick-intent",
                "events": [
                    {
                        "event_id": "event-quick-intent",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {
                            "intent_text": "Answer a quick question.",
                            "classification": {"persistence": "quick", "confidence": 0.9, "reason": "test"},
                            "task_hint": {
                                "title": "Quick answer",
                                "task_id": None,
                                "parent_task_id": None,
                            },
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["ok"])
        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["result"]["status"], "not_recorded")
        self.assertTrue(response["result"]["recorded"])
        self.assertFalse(response["result"]["projected"])
        self.assertFalse(response["result"]["accepted"])
        self.assertEqual(response["workroot_view"]["focus"], "no_persistent_work")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_commit_batches").fetchone()[0], 1)

    def test_non_atomic_commit_batch_is_reserved_and_rejected_without_recording(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-non-atomic",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create non atomic task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-non-atomic",
                "exchange_lease_id": self.lease_id(sync_response),
                "idempotency_key": "idem-non-atomic",
                "atomic_batch": False,
                "events": [
                    {
                        "event_id": "event-non-atomic",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {
                            "intent_text": "Create non atomic task.",
                            "classification": {"persistence": "normal", "confidence": 0.9, "reason": "test"},
                            "task_hint": {
                                "title": "Non atomic task",
                                "task_id": None,
                                "parent_task_id": None,
                            },
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertFalse(response["ok"])
        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["error"]["code"], "unsupported_atomic_batch_mode")
        self.assertEqual(response["result"]["status"], "rejected")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_commit_batches").fetchone()[0], 0)

    def test_minimally_identifiable_malformed_event_is_quarantined(self) -> None:
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-malformed",
                "idempotency_key": "idem-malformed",
                "workroot_id": "wr_demo",
                "atomic_batch": True,
                "events": [
                    {
                        "event_id": "event-malformed",
                        "kind": "progress",
                        "schema_version": "progress.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {"task_id": "missing-task"},
                        "evidence": "not-a-list",
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["result"]["status"], "quarantined")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            row = conn.execute("SELECT status FROM protocol_events WHERE event_id = 'event-malformed'").fetchone()
        self.assertEqual(row, ("quarantined",))

    def test_unidentifiable_malformed_event_is_warning_only(self) -> None:
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-unidentifiable",
                "idempotency_key": "idem-unidentifiable",
                "workroot_id": "wr_demo",
                "atomic_batch": True,
                "events": [{"kind": "progress", "payload": {}}],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["result"]["status"], "quarantined")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 0)

    def test_event_disallowed_by_lease_is_rejected_without_recording_protocol_event(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-disallowed-event",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create a tracked task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-disallowed-event",
                "exchange_lease_id": self.lease_id(first_sync),
                "idempotency_key": "idem-disallowed-event",
                "events": [
                    {
                        "event_id": "event-disallowed-progress",
                        "kind": "progress",
                        "schema_version": "progress.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {"summary": "Progress should not project on a workroot lease."},
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["result"]["status"], "rejected")
        self.assertEqual(response["result"]["warnings"], ["event_not_allowed"])
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 0)
            event_count = conn.execute(
                "SELECT COUNT(*) FROM protocol_events WHERE event_id = 'event-disallowed-progress'"
            ).fetchone()[0]
        self.assertEqual(event_count, 0)

    def test_event_target_mismatch_with_lease_is_rejected_without_recording_protocol_event(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-target-mismatch",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create alpha protocol work.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        first_task = commit(
            build_commit_request_from_shape(
                shape="start_work",
                lease_id=self.lease_id(first_sync),
                agent_name="codex",
                title="Alpha protocol work",
                summary="Alpha protocol work.",
            )
        )
        second_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-second-target",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_task_switch",
                "query": "Create beta audit work.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        second_task = commit(
            build_commit_request_from_shape(
                shape="start_work",
                lease_id=self.lease_id(second_sync),
                agent_name="codex",
                title="Beta audit work",
                summary="Beta audit work.",
            )
        )
        first_progress_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-first-progress-target",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "continue",
                "query": "Continue alpha protocol work.",
                "known_state": {"task_id": self.task_id(first_task), "run_id": self.run_id(first_task)},
                "work_signal": {"phase": "executing", "work_kind": "continuation", "intended_action": "preserve"},
            }
        )

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-target-mismatch-progress",
                "exchange_lease_id": self.lease_id(first_progress_sync),
                "idempotency_key": "idem-target-mismatch-progress",
                "events": [
                    {
                        "event_id": "event-target-mismatch-progress",
                        "kind": "progress",
                        "schema_version": "progress.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {
                            "task_id": self.task_id(second_task),
                            "run_id": self.run_id(second_task),
                            "summary": "Progress should not bind across a mismatched lease.",
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["result"]["status"], "rejected")
        self.assertEqual(response["result"]["warnings"], ["state_conflict"])
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            event_count = conn.execute(
                "SELECT COUNT(*) FROM protocol_events WHERE event_id = 'event-target-mismatch-progress'"
            ).fetchone()[0]
        self.assertEqual(event_count, 0)

    def test_expired_located_lease_degrades_and_preserves_safe_progress(self) -> None:
        first_sync = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-expired-lease",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create a tracked task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        intent = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-intent-expired-lease",
                "exchange_lease_id": self.lease_id(first_sync),
                "idempotency_key": "idem-intent-expired-lease",
                "events": [
                    {
                        "event_id": "event-intent-expired-lease",
                        "kind": "intent",
                        "schema_version": "intent.v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {
                            "intent_text": "Create a tracked task.",
                            "classification": {"persistence": "normal", "confidence": 0.9, "reason": "test"},
                            "task_hint": {
                                "title": "Expired lease task",
                                "task_id": None,
                                "parent_task_id": None,
                            },
                        },
                        "evidence": [],
                    }
                ],
            }
        )
        task_id = self.task_id(intent)
        run_id = self.run_id(intent)
        progress_lease_id = self.lease_id(intent)
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            conn.execute(
                "UPDATE exchange_leases SET expires_at = ? WHERE lease_id = ?",
                ("2026-01-01T00:00:00Z", progress_lease_id),
            )
            conn.commit()

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-progress-expired-lease",
                "exchange_lease_id": progress_lease_id,
                "idempotency_key": "idem-progress-expired-lease",
                "events": [
                    {
                        "event_id": "event-progress-expired-lease",
                        "kind": "progress",
                        "schema_version": "progress.v1",
                        "occurred_at": now_utc(),
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {
                            "task_id": task_id,
                            "run_id": run_id,
                            "summary": "Expired lease progress preserved.",
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["result"]["status"], "applied")
        self.assertEqual(response["result"]["warnings"], ["lease_expired_safe_projection"])
        with sqlite3.connect(sqlite_path) as conn:
            event_status = conn.execute(
                "SELECT status FROM protocol_events WHERE event_id = 'event-progress-expired-lease'"
            ).fetchone()
            row = conn.execute("SELECT summary_text FROM task_summaries WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(event_status, ("applied",))
        self.assertEqual(row, ("Expired lease progress preserved.",))

    def test_runtime_view_refresh_failure_does_not_fail_applied_commit(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-runtime-view-failure",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create a tracked task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )

        request = {
            "protocol_version": "workroot.v1",
            "request_id": "req-runtime-view-failure",
            "exchange_lease_id": self.lease_id(sync_response),
            "idempotency_key": "idem-runtime-view-failure",
            "events": [
                {
                    "event_id": "event-runtime-view-failure",
                    "kind": "intent",
                    "schema_version": "intent.v1",
                    "occurred_at": "2026-05-27T00:00:00Z",
                    "source": {"actor_name": "codex"},
                    "confirmation": {},
                    "payload": {
                        "intent_text": "Create a tracked task.",
                        "classification": {"persistence": "normal", "confidence": 0.9, "reason": "test"},
                        "task_hint": {
                            "title": "Runtime view failure task",
                            "task_id": None,
                            "parent_task_id": None,
                        },
                    },
                    "evidence": [],
                }
            ],
        }

        with patch("ai_workroot.protocol.controller.refresh_runtime_views", side_effect=OSError("view failed")):
            response = commit(request)

        self.assertEqual(response["result"]["status"], "applied")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            row = conn.execute(
                "SELECT status FROM protocol_events WHERE event_id = ?", ("event-runtime-view-failure",)
            ).fetchone()
        self.assertEqual(row, ("applied",))

    def test_unexpected_projection_storage_error_returns_non_blocking_protocol_response(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-unexpected-projection-failure",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Create a tracked task.",
                "work_signal": {"phase": "starting", "work_kind": "task", "intended_action": "plan"},
            }
        )
        request = build_commit_request_from_shape(
            shape="start_work",
            lease_id=self.lease_id(sync_response),
            agent_name="codex",
            title="Unexpected projection failure task",
            summary="Unexpected projection failures should not block the Agent.",
        )

        with patch(
            "ai_workroot.protocol.controller.apply_projection",
            side_effect=sqlite3.OperationalError("database is locked"),
        ):
            response = commit(request)

        self.assertFalse(response["ok"])
        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["error"]["code"], "storage_error")
        self.assertEqual(response["result"]["status"], "rejected")
        self.assertEqual(response["result"]["warnings"], ["storage_error"])
        self.assertEqual(response["workroot_contract"]["next_exchange"]["action"], "sync")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            batch = conn.execute(
                """
                SELECT status, response_json, error_json
                FROM protocol_commit_batches
                WHERE idempotency_key = ?
                """,
                (request["idempotency_key"],),
            ).fetchone()
            task_count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE title = 'Unexpected projection failure task'"
            ).fetchone()[0]
        self.assertIsNotNone(batch)
        self.assertEqual(batch[0], "rejected")
        self.assertIsNotNone(batch[1])
        self.assertIsNotNone(batch[2])
        self.assertEqual(task_count, 0)

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
