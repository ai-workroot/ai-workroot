from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.retrieval.providers.candidate_provider import upsert_context_candidate
from ai_workroot.context.builder import ContextRequest, build_context_package
from ai_workroot.commands.init_workroot import initialize_workroot


class ReleaseProtectionContextNegativeTest(unittest.TestCase):
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

    def test_release_records_redacted_and_deleted_targets_do_not_enter_ordinary_context(self) -> None:
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
                        "candidate_id": "cand-release-redacted",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-release-redacted",
                        "title": "Release record redacted asset",
                        "summary": "RELEASE-REDACTED-SECRET must not leak.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-release-deleted",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-release-deleted",
                        "title": "Release record deleted asset",
                        "summary": "RELEASE-DELETED-SECRET must not leak.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-release-safe",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-release-safe",
                        "title": "Release safe asset",
                        "summary": "Release safe context may be shown.",
                        "context_policy": "always",
                    },
                )
                conn.executemany(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES (?, ?, 'asset', ?, ?, ?)
                    """,
                    [
                        (
                            "rel-redacted",
                            workroot_id,
                            "asset-release-redacted",
                            "redacted",
                            "ordinary-context-excluded",
                        ),
                        (
                            "rel-deleted",
                            workroot_id,
                            "asset-release-deleted",
                            "deleted",
                            "ordinary-context-excluded",
                        ),
                    ],
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="release safe secret", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Release safe asset", package)
            self.assertNotIn("RELEASE-REDACTED-SECRET", package)
            self.assertNotIn("RELEASE-DELETED-SECRET", package)
            self.assertNotIn("Release record redacted asset", package)
            self.assertNotIn("Release record deleted asset", package)
            self.assertIn("releaseFilters", package)
            self.assertIn("redacted", package)
            self.assertIn("deleted", package)

    def test_release_records_keep_most_protective_level_for_duplicate_targets(self) -> None:
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
                        "candidate_id": "cand-duplicate-release",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-duplicate-release",
                        "title": "Duplicate release target",
                        "summary": "DUPLICATE-RELEASE-SECRET must not leak.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                conn.executemany(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES (?, ?, 'asset', 'asset-duplicate-release', ?, ?)
                    """,
                    [
                        ("rel-redacted", workroot_id, "redacted", "ordinary-context-excluded"),
                        ("rel-active", workroot_id, "active", "ordinary-context-allowed"),
                    ],
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="duplicate release", debug=True),
                ai_workroot_home=home,
            )

            self.assertNotIn("DUPLICATE-RELEASE-SECRET", package)
            self.assertNotIn("Duplicate release target", package)
            self.assertIn("redacted", package)

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

    def test_redacted_task_and_deleted_work_action_candidates_are_resolved_and_dropped(self) -> None:
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
                        "candidate_id": "cand-task-redacted",
                        "workroot_id": workroot_id,
                        "source_type": "task",
                        "source_id": "task-redacted",
                        "title": "Redacted task",
                        "summary": "TASK-REDACTED-SECRET must not leak.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-action-deleted",
                        "workroot_id": workroot_id,
                        "source_type": "work_action",
                        "source_id": "action-deleted",
                        "title": "Deleted action",
                        "summary": "ACTION-DELETED-SECRET must not leak.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-safe-task",
                        "workroot_id": workroot_id,
                        "source_type": "task",
                        "source_id": "task-safe",
                        "title": "Safe task",
                        "summary": "Safe task context may be shown.",
                        "context_policy": "always",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES ('rel-task-redacted', ?, 'task', 'task-redacted', 'redacted', 'ordinary-context-excluded')
                    """,
                    (workroot_id,),
                )
                conn.execute(
                    """
                    INSERT INTO deletion_records (deletion_id, workroot_id, target_type, target_id, minimum_audit_note)
                    VALUES ('del-action', ?, 'work_action', 'action-deleted', 'deleted')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="task action safe", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Safe task", package)
            self.assertNotIn("TASK-REDACTED-SECRET", package)
            self.assertNotIn("ACTION-DELETED-SECRET", package)
            self.assertNotIn("Redacted task", package)
            self.assertNotIn("Deleted action", package)
            self.assertIn("cand-task-redacted:redacted", package)
            self.assertIn("cand-action-deleted:deleted", package)


if __name__ == "__main__":
    unittest.main()
