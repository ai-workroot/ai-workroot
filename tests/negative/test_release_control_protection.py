from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.relationship_provider import upsert_relationship_edge, upsert_relationship_node
from ai_workroot.indexing.providers.sqlite_fts import index_file_chunk
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

    def test_context_candidate_source_resolves_underlying_asset_not_candidate_itself(self) -> None:
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
                        "candidate_id": "cand-wrapper",
                        "workroot_id": workroot_id,
                        "source_type": "context_candidate",
                        "source_id": "cand-underlying",
                        "title": "Wrapper candidate",
                        "summary": "WRAPPER-SECRET must not leak.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-underlying",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-underlying",
                        "title": "Underlying candidate",
                        "summary": "Underlying candidate summary.",
                        "importance": "normal",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES ('rel-underlying', ?, 'asset', 'asset-underlying', 'deleted', 'ordinary-context-excluded')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="wrapper", debug=True),
                ai_workroot_home=home,
            )

            self.assertNotIn("WRAPPER-SECRET", package)
            self.assertNotIn("Wrapper candidate", package)
            self.assertIn("cand-wrapper:deleted", package)

    def test_indexed_chunk_release_target_suppresses_fts_match_and_candidate_boost(self) -> None:
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
                        "candidate_id": "cand-protected-file",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-protected-file",
                        "title": "Protected indexed file",
                        "summary": "The related indexed file must not be boosted by FTS.",
                        "importance": "low",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-safe-file",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-safe-file",
                        "title": "Safe indexed file",
                        "summary": "Safe indexed file may be shown.",
                        "importance": "normal",
                    },
                )
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-protected",
                    chunk_id="chunk-protected",
                    relative_path="protected.md",
                    body="needle protected secret",
                    source_type="asset",
                    source_id="asset-protected-file",
                )
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-safe",
                    chunk_id="chunk-safe",
                    relative_path="safe.md",
                    body="needle safe context",
                    source_type="asset",
                    source_id="asset-safe-file",
                )
                conn.execute(
                    """
                    INSERT INTO redactions (redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason)
                    VALUES ('red-file', ?, 'asset', 'asset-protected-file', 'body', 'sensitive')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="needle", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("safe.md: file-fts-match", package)
            self.assertIn("Safe indexed file", package)
            self.assertNotIn("protected.md", package)
            self.assertNotIn("Protected indexed file", package)
            self.assertIn("ftsReleaseFilters", package)
            self.assertIn("chunk-protected:redacted", package)

    def test_relationship_edge_release_targets_filter_deleted_edges_and_annotate_tombstones(self) -> None:
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
                        "candidate_id": "cand-seed",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-seed",
                        "title": "Seed asset",
                        "summary": "Seed asset should remain.",
                        "importance": "high",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-deleted-node",
                        "workroot_id": workroot_id,
                        "source_type": "task",
                        "source_id": "task-deleted",
                        "title": "Deleted node",
                        "summary": "DELETED-RELATIONSHIP-NODE must not leak.",
                        "importance": "low",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-tombstone-node",
                        "workroot_id": workroot_id,
                        "source_type": "task",
                        "source_id": "task-tombstone",
                        "title": "Tombstone node",
                        "summary": "Tombstone relationship node can be annotated.",
                        "importance": "low",
                    },
                )
                upsert_relationship_node(conn, "asset-seed", workroot_id, "asset", "Seed asset")
                upsert_relationship_node(conn, "task-deleted", workroot_id, "task", "Deleted node")
                upsert_relationship_node(conn, "task-tombstone", workroot_id, "task", "Tombstone node")
                upsert_relationship_edge(
                    conn,
                    edge_id="edge-deleted",
                    workroot_id=workroot_id,
                    from_node_id="asset-seed",
                    to_node_id="task-deleted",
                    relationship_type="supports",
                    confidence=0.9,
                )
                upsert_relationship_edge(
                    conn,
                    edge_id="edge-tombstone",
                    workroot_id=workroot_id,
                    from_node_id="asset-seed",
                    to_node_id="task-tombstone",
                    relationship_type="documents",
                    confidence=0.8,
                )
                conn.execute(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES ('rel-edge-deleted', ?, 'relationship_edge', 'edge-deleted', 'deleted', 'ordinary-context-excluded')
                    """,
                    (workroot_id,),
                )
                conn.execute(
                    """
                    INSERT INTO deletion_records (deletion_id, workroot_id, target_type, target_id, minimum_audit_note)
                    VALUES ('del-related-task', ?, 'task', 'task-deleted', 'deleted')
                    """,
                    (workroot_id,),
                )
                conn.execute(
                    """
                    INSERT INTO tombstones (tombstone_id, workroot_id, target_type, target_id, title, symbolic_note)
                    VALUES ('tomb-edge', ?, 'relationship_edge', 'edge-tombstone', 'Tombstone edge', 'symbolic only')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="seed", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Seed asset", package)
            relationship_section = package.split("## Relationship Signals", 1)[1].split("## Debug Trace", 1)[0]
            self.assertNotIn("edge-deleted", relationship_section)
            self.assertNotIn("DELETED-RELATIONSHIP-NODE", package)
            self.assertIn("edge-tombstone", package)
            self.assertIn("tombstone", package)
            self.assertIn("relationshipReleaseFilters", package)
            self.assertIn("dropped=edge-deleted:deleted", package)


if __name__ == "__main__":
    unittest.main()
