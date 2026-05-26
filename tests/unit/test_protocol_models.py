from __future__ import annotations

import unittest

from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.events import validate_event_envelope
from ai_workroot.protocol.model import CommitRequest, SyncRequest


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


if __name__ == "__main__":
    unittest.main()
