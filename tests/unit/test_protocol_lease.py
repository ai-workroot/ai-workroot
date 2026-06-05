from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol.lease import create_lease, validate_lease
from ai_workroot.state.sqlite import initialize_workroot_sqlite
from ai_workroot.state.versions import bump_state_version


class ProtocolLeaseTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_create_lease_contains_state_vector(self) -> None:
        conn = self.open_db()
        bump_state_version(conn, "wr_demo", "workroot")
        bump_state_version(conn, "wr_demo", "task:task-1")

        lease = create_lease(
            conn,
            workroot_id="wr_demo",
            scope="task",
            task_id="task-1",
            run_id=None,
            allowed_events=["progress"],
            issued_at="2026-05-26T10:00:00Z",
            expires_at="2026-05-26T11:00:00Z",
        )

        self.assertEqual(lease["observed_versions"]["workroot"], 1)
        self.assertEqual(lease["observed_versions"]["task:task-1"], 1)
        self.assertEqual(lease["allowed_events"], ["progress"])

    def test_commit_without_lease_rejected(self) -> None:
        conn = self.open_db()

        result = validate_lease(conn, "missing", events=[{"kind": "progress"}], now="2026-05-26T10:30:00Z")

        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "lease_not_found")
        self.assertEqual(result.directive["type"], "resync_required")

    def test_expired_lease_rejected(self) -> None:
        conn = self.open_db()
        lease = create_lease(
            conn,
            workroot_id="wr_demo",
            scope="workroot",
            task_id=None,
            run_id=None,
            allowed_events=["intent"],
            issued_at="2026-05-26T10:00:00Z",
            expires_at="2026-05-26T10:01:00Z",
        )

        result = validate_lease(conn, lease["lease_id"], events=[{"kind": "intent"}], now="2026-05-26T10:30:00Z")

        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "lease_expired")
        self.assertEqual(result.directive["type"], "resync_required")

    def test_inactive_lease_rejected(self) -> None:
        conn = self.open_db()
        lease = create_lease(
            conn,
            workroot_id="wr_demo",
            scope="workroot",
            task_id=None,
            run_id=None,
            allowed_events=["intent"],
        )
        conn.execute("UPDATE exchange_leases SET status = 'superseded' WHERE lease_id = ?", (lease["lease_id"],))

        result = validate_lease(conn, lease["lease_id"], events=[{"kind": "intent"}])

        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "lease_not_active")
        self.assertEqual(result.directive["type"], "resync_required")

    def test_event_not_allowed_by_lease_rejected(self) -> None:
        conn = self.open_db()
        lease = create_lease(
            conn,
            workroot_id="wr_demo",
            scope="task",
            task_id="task-1",
            run_id=None,
            allowed_events=["progress"],
        )

        result = validate_lease(conn, lease["lease_id"], events=[{"kind": "asset"}])

        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "event_not_allowed")
        self.assertEqual(result.directive["type"], "resync_required")

    def test_state_version_conflict_rejected(self) -> None:
        conn = self.open_db()
        bump_state_version(conn, "wr_demo", "task:task-1")
        lease = create_lease(
            conn,
            workroot_id="wr_demo",
            scope="task",
            task_id="task-1",
            run_id=None,
            allowed_events=["progress"],
        )
        bump_state_version(conn, "wr_demo", "task:task-1")

        result = validate_lease(conn, lease["lease_id"], events=[{"kind": "progress"}])

        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "state_conflict")
        self.assertEqual(result.directive["type"], "resync_required")


if __name__ == "__main__":
    unittest.main()
