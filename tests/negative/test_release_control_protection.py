from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.runtime.context import ContextRequest, build_context_package
from ai_workroot.runtime.init import initialize_workroot


class ReleaseControlProtectionNegativeTest(unittest.TestCase):
    def test_redacted_and_deleted_targets_do_not_enter_ordinary_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-redacted",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-redacted",
                        "title": "Redacted payroll secret",
                        "summary": "PAYROLL-SECRET-123 must not leak.",
                        "importance": "critical",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-deleted",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-deleted",
                        "title": "Deleted personal detail",
                        "summary": "DELETED-DETAIL-456 must not leak.",
                        "importance": "critical",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-safe",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-safe",
                        "title": "Safe release note",
                        "summary": "Safe context may be shown.",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO redactions (redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason)
                    VALUES ('red-1', ?, 'asset', 'asset-redacted', 'summary', 'sensitive')
                    """,
                    (workroot_id,),
                )
                conn.execute(
                    """
                    INSERT INTO deletion_records (deletion_id, workroot_id, target_type, target_id, minimum_audit_note)
                    VALUES ('del-1', ?, 'asset', 'asset-deleted', 'deleted')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="secret detail safe", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Safe release note", package)
            self.assertNotIn("PAYROLL-SECRET-123", package)
            self.assertNotIn("DELETED-DETAIL-456", package)
            self.assertNotIn("Redacted payroll secret", package)
            self.assertNotIn("Deleted personal detail", package)
            self.assertIn("releaseFilters", package)
            self.assertIn("redacted", package)
            self.assertIn("deleted", package)

    def test_tombstone_is_visible_and_annotated_not_strictly_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-tombstone",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-tombstone",
                        "title": "Tombstone lesson",
                        "summary": "Remember the retired approach as a lesson.",
                        "importance": "high",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO tombstones (tombstone_id, workroot_id, target_type, target_id, title, symbolic_note)
                    VALUES ('tomb-1', ?, 'asset', 'asset-tombstone', 'Tombstone lesson', 'Visible remembrance')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="lesson", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Tombstone lesson", package)
            self.assertIn("tombstone", package)
            self.assertIn("annotated-release-state", package)


if __name__ == "__main__":
    unittest.main()
