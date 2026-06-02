from __future__ import annotations

import unittest

from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.events import validate_event_envelope
from ai_workroot.protocol.model import CommitRequest, SyncRequest
from ai_workroot.protocol.work_signal import WorkSignal


class ProtocolModelTest(unittest.TestCase):
    def test_sync_request_requires_protocol_version(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "missing_protocol_version"):
            SyncRequest.from_dict(
                {
                    "request_id": "req-1",
                    "agent": {"name": "codex", "transport": "cli"},
                    "cwd": ".",
                    "reason": "startup",
                }
            )

    def test_sync_request_requires_locator(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "missing_workroot_locator"):
            SyncRequest.from_dict(
                {
                    "protocol_version": "workroot.v1",
                    "request_id": "req-1",
                    "agent": {"name": "codex", "transport": "cli"},
                    "reason": "startup",
                }
            )

    def test_invalid_sync_reason_rejected(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "invalid_sync_reason"):
            SyncRequest.from_dict(
                {
                    "protocol_version": "workroot.v1",
                    "request_id": "req-1",
                    "agent": {"name": "codex", "transport": "cli"},
                    "cwd": ".",
                    "reason": "bad",
                }
            )

    def test_sync_request_accepts_optional_work_signal(self) -> None:
        request = SyncRequest.from_dict(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-work-signal",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": ".",
                "reason": "before_work",
                "work_signal": {
                    "phase": "planning",
                    "work_kind": "task",
                    "intended_action": "plan",
                    "focus": "Plan recovery state handling.",
                    "concerns": ["uncertain_task_boundary"],
                },
            }
        )

        self.assertEqual(request.work_signal["phase"], "planning")
        self.assertEqual(request.work_signal["concerns"], ["uncertain_task_boundary"])

    def test_commit_requires_events(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "empty_event_batch"):
            CommitRequest.from_dict(
                {
                    "protocol_version": "workroot.v1",
                    "request_id": "req-commit",
                    "exchange_lease_id": "lease-1",
                    "idempotency_key": "key-1",
                    "events": [],
                }
            )

    def test_commit_accepts_explicit_locator_without_lease(self) -> None:
        request = CommitRequest.from_dict(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-commit",
                "workroot_id": "wr_demo",
                "idempotency_key": "key-1",
                "events": [{"kind": "progress", "payload": {}}],
            }
        )

        self.assertEqual(request.exchange_lease_id, "")
        self.assertEqual(request.workroot_id, "wr_demo")
        self.assertEqual(request.events, [{"kind": "progress", "payload": {}}])

    def test_unknown_event_kind_rejected(self) -> None:
        with self.assertRaisesRegex(ProtocolError, "invalid_event_kind"):
            validate_event_envelope(
                {
                    "event_id": "evt-1",
                    "kind": "unknown",
                    "schema_version": "unknown.v1",
                    "occurred_at": "2026-05-26T10:00:00Z",
                    "source": {},
                    "confirmation": {},
                    "payload": {},
                    "evidence": [],
                }
            )


class WorkSignalTest(unittest.TestCase):
    def test_work_signal_accepts_stable_high_level_fields(self) -> None:
        signal = WorkSignal.from_dict(
            {
                "phase": "executing",
                "work_kind": "implementation",
                "intended_action": "edit",
                "focus": "Implement non-blocking protocol responses.",
                "concerns": ["may_change_user_assets"],
            }
        )

        self.assertEqual(signal.phase, "executing")
        self.assertEqual(signal.work_kind, "implementation")
        self.assertEqual(signal.intended_action, "edit")
        self.assertEqual(signal.concerns, ("may_change_user_assets",))

    def test_work_signal_accepts_preservation_semantics_without_handoff_protocol_wording(self) -> None:
        signal = WorkSignal.from_dict(
            {
                "phase": "preserving",
                "work_kind": "task",
                "intended_action": "preserve",
                "focus": "Save current state and next action.",
                "concerns": ["uncertain_task_boundary"],
            }
        )

        self.assertEqual(signal.phase, "preserving")
        self.assertEqual(signal.intended_action, "preserve")
        self.assertEqual(signal.concerns, ("uncertain_task_boundary",))

    def test_work_signal_drops_unknown_values_without_failing(self) -> None:
        signal = WorkSignal.from_dict(
            {
                "phase": "too-specific",
                "work_kind": "custom-kind",
                "intended_action": "custom-action",
                "focus": "Still help the user.",
                "concerns": ["unknown", "needs_evidence"],
            }
        )

        self.assertEqual(signal.phase, "")
        self.assertEqual(signal.work_kind, "")
        self.assertEqual(signal.intended_action, "")
        self.assertEqual(signal.focus, "Still help the user.")
        self.assertEqual(signal.concerns, ("needs_evidence",))


if __name__ == "__main__":
    unittest.main()
