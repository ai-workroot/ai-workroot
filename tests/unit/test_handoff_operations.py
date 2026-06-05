from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.handoff.model import HandoffPackage
from ai_workroot.capabilities.handoff.operations import create_handoff
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class HandoffOperationsTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_create_handoff_package_persists_transfer_fields(self) -> None:
        conn = self.open_db()

        handoff = create_handoff(
            conn,
            workroot_id="wr_demo",
            handoff_id="handoff-1",
            title="Continue architecture review",
            target="codex",
            body="Next agent should continue from release filtering.",
        )

        self.assertIsInstance(handoff, HandoffPackage)
        self.assertEqual(handoff.handoff_id, "handoff-1")
        self.assertEqual(handoff.workroot_id, "wr_demo")
        self.assertEqual(handoff.title, "Continue architecture review")
        self.assertEqual(handoff.target, "codex")
        self.assertEqual(handoff.body, "Next agent should continue from release filtering.")
        self.assertEqual(
            conn.execute(
                """
                SELECT title, target, body
                FROM handoffs
                WHERE handoff_id = 'handoff-1'
                """
            ).fetchone(),
            ("Continue architecture review", "codex", "Next agent should continue from release filtering."),
        )
        self.assertEqual(
            conn.execute(
                """
                SELECT index_id, reason
                FROM index_invalidations
                WHERE invalidation_id = 'idxinv:wr_demo:handoff:handoff-1'
                """
            ).fetchone(),
            ("handoffs", "handoff-changed:handoff-1"),
        )


if __name__ == "__main__":
    unittest.main()
