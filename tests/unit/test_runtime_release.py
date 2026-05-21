from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.core.release import ReleaseTargetRef
from ai_workroot.runtime.release import (
    create_deletion_record,
    create_redaction,
    create_release_record,
    create_tombstone,
    resolve_release_state_for_target,
)
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class RuntimeReleaseTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_release_runtime_creates_release_tombstone_redaction_and_deletion_records(self) -> None:
        conn = self.open_db()
        target = ReleaseTargetRef(target_type="asset", target_id="asset-1", workroot_id="wr_demo")

        release = create_release_record(
            conn,
            release_id="rel-1",
            workroot_id="wr_demo",
            target=target,
            release_level="quiet",
            recall_rule="ordinary-context-allowed",
        )
        tombstone = create_tombstone(
            conn,
            tombstone_id="tomb-1",
            workroot_id="wr_demo",
            target=target,
            title="Old asset",
            symbolic_note="Keep the lesson.",
        )
        redaction = create_redaction(
            conn,
            redaction_id="redact-1",
            workroot_id="wr_demo",
            target=target,
            redacted_fields=("summary", "body"),
            redaction_reason="contains sensitive detail",
        )
        deletion = create_deletion_record(
            conn,
            deletion_id="delete-1",
            workroot_id="wr_demo",
            target=target,
            minimum_audit_note="deleted by test",
        )

        self.assertEqual(release.release_level, "quiet")
        self.assertEqual(tombstone.symbolic_note, "Keep the lesson.")
        self.assertEqual(redaction.redacted_fields, ("summary", "body"))
        self.assertEqual(deletion.minimum_audit_note, "deleted by test")
        self.assertEqual(conn.execute("SELECT release_level FROM release_records").fetchone(), ("quiet",))
        self.assertEqual(conn.execute("SELECT symbolic_note FROM tombstones").fetchone(), ("Keep the lesson.",))
        self.assertEqual(conn.execute("SELECT redacted_fields FROM redactions").fetchone(), ("summary,body",))
        self.assertEqual(conn.execute("SELECT minimum_audit_note FROM deletion_records").fetchone(), ("deleted by test",))

    def test_resolve_release_state_uses_most_protective_level(self) -> None:
        conn = self.open_db()
        target = ReleaseTargetRef(target_type="task", target_id="task-1", workroot_id="wr_demo")
        create_release_record(
            conn,
            release_id="rel-quiet",
            workroot_id="wr_demo",
            target=target,
            release_level="quiet",
        )
        create_tombstone(
            conn,
            tombstone_id="tomb-task",
            workroot_id="wr_demo",
            target=target,
            title="Old task",
            symbolic_note="Tombstone but visible.",
        )
        create_redaction(
            conn,
            redaction_id="redact-task",
            workroot_id="wr_demo",
            target=target,
            redacted_fields=("summary",),
            redaction_reason="sensitive",
        )

        result = resolve_release_state_for_target(conn, workroot_id="wr_demo", target=target)

        self.assertEqual(result.level, "redacted")
        self.assertTrue(result.strictly_protected)
        self.assertIn(target, result.matched_targets)


if __name__ == "__main__":
    unittest.main()
