from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.time import query_time_events, record_time_event
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class RuntimeTimeTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_record_and_query_time_event(self) -> None:
        conn = self.open_db()

        event = record_time_event(
            conn,
            workroot_id="wr_demo",
            event_id="time-task-closed",
            subject_type="task",
            subject_id="task-1",
            event_type="task_closed",
            occurred_at="2026-05-21T10:00:00Z",
            source_ref="runtime/work.py",
        )
        events = query_time_events(conn, "wr_demo", subject_type="task", subject_id="task-1")

        self.assertEqual(event.event_id, "time-task-closed")
        self.assertEqual(event.subject_type, "task")
        self.assertEqual(event.occurred_at, "2026-05-21T10:00:00Z")
        self.assertEqual([item.event_id for item in events], ["time-task-closed"])
        self.assertEqual(events[0].source_ref, "runtime/work.py")

    def test_query_time_events_filters_workroot_and_subject(self) -> None:
        conn = self.open_db()
        record_time_event(
            conn,
            workroot_id="wr_demo",
            event_id="time-demo",
            subject_type="asset",
            subject_id="asset-1",
            event_type="asset_published",
            occurred_at="2026-05-21T11:00:00Z",
        )
        record_time_event(
            conn,
            workroot_id="wr_other",
            event_id="time-other",
            subject_type="asset",
            subject_id="asset-1",
            event_type="asset_published",
            occurred_at="2026-05-21T12:00:00Z",
        )

        events = query_time_events(conn, "wr_demo", subject_type="asset")

        self.assertEqual([item.event_id for item in events], ["time-demo"])


if __name__ == "__main__":
    unittest.main()
