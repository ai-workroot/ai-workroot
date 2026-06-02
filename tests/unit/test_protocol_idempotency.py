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


class ProtocolIdempotencyTest(unittest.TestCase):
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

    def create_workroot_lease(self) -> str:
        with sqlite3.connect(self.sqlite_path) as conn:
            lease = create_lease(
                conn,
                workroot_id="wr_demo",
                scope="workroot",
                task_id=None,
                run_id=None,
                allowed_events=["intent"],
            )
            return lease["lease_id"]

    def test_same_idempotency_key_same_hash_returns_previous_response(self) -> None:
        lease_id = self.create_workroot_lease()
        request = self.intent_request(lease_id, "codex-key-1", "evt-1", "Implement protocol P0")

        first = commit(request)
        second = commit(request)

        self.assertTrue(first["ok"])
        self.assertEqual(second, first)
        self.assertEqual(self.count_protocol_events(), 1)

    def test_same_idempotency_key_different_hash_rejected(self) -> None:
        lease_id = self.create_workroot_lease()
        first = self.intent_request(lease_id, "codex-key-2", "evt-1", "Implement protocol P0")
        second = self.intent_request(lease_id, "codex-key-2", "evt-2", "Implement a different task")

        self.assertTrue(commit(first)["ok"])
        conflict = commit(second)

        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["error"]["code"], "idempotency_key_conflict")
        self.assertEqual(self.count_protocol_events(), 1)

    def intent_request(self, lease_id: str, key: str, event_id: str, text: str) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-{event_id}",
            "exchange_lease_id": lease_id,
            "idempotency_key": key,
            "events": [
                {
                    "event_id": event_id,
                    "kind": "intent",
                    "schema_version": "intent.v1",
                    "occurred_at": "2026-05-26T10:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "session-1"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": {
                        "intent_text": text,
                        "classification": {"persistence": "normal", "confidence": 0.9, "reason": "test"},
                        "task_hint": {"title": "Protocol P0", "task_id": None, "parent_task_id": None},
                    },
                    "evidence": [],
                }
            ],
        }

    def count_protocol_events(self) -> int:
        with sqlite3.connect(self.sqlite_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0]


if __name__ == "__main__":
    unittest.main()
