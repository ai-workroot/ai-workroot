from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.core.release import ReleaseTargetRef
from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.context_recall_hint_provider import ContextRecallHint, upsert_context_recall_hint
from ai_workroot.indexing.providers.sqlite_fts import index_file_chunk
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
        self.assertEqual(
            conn.execute("SELECT minimum_audit_note FROM deletion_records").fetchone(), ("deleted by test",)
        )

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

    def test_create_redaction_sanitizes_candidate_and_hint_derived_indexes(self) -> None:
        conn = self.open_db()
        target = ReleaseTargetRef(target_type="asset", target_id="asset-sensitive", workroot_id="wr_demo")
        upsert_context_candidate(
            conn,
            {
                "candidate_id": "cand-sensitive",
                "workroot_id": "wr_demo",
                "source_type": "asset",
                "source_id": "asset-sensitive",
                "title": "Sensitive candidate title",
                "summary": "SECRETCANDIDATESUMMARY must be removed.",
                "importance": "critical",
            },
        )
        upsert_context_recall_hint(
            conn,
            ContextRecallHint(
                hint_id="hint-sensitive",
                workroot_id="wr_demo",
                target_type="asset",
                target_id="asset-sensitive",
                title="Sensitive hint title",
                summary="SECRETHINTSUMMARY must be removed.",
                priority="critical",
            ),
        )
        upsert_context_candidate(
            conn,
            {
                "candidate_id": "hint:hint-sensitive",
                "workroot_id": "wr_demo",
                "source_type": "context_recall_hint",
                "source_id": "hint-sensitive",
                "title": "Previously materialized sensitive hint",
                "summary": "SECRETOLDMATERIALIZEDHINT must be removed.",
                "importance": "critical",
            },
        )

        create_redaction(
            conn,
            redaction_id="redact-sensitive",
            workroot_id="wr_demo",
            target=target,
            redacted_fields=("title", "summary"),
            redaction_reason="sensitive",
        )

        candidate = conn.execute(
            "SELECT title, summary FROM context_candidates WHERE candidate_id = 'cand-sensitive'"
        ).fetchone()
        candidate_fts = conn.execute(
            "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH 'SECRETCANDIDATESUMMARY'"
        ).fetchall()
        hint = conn.execute(
            "SELECT title, summary FROM context_recall_hints WHERE hint_id = 'hint-sensitive'"
        ).fetchone()
        hint_fts = conn.execute(
            "SELECT hint_id FROM context_recall_hints_fts WHERE context_recall_hints_fts MATCH 'SECRETHINTSUMMARY'"
        ).fetchall()
        materialized_hint = conn.execute(
            "SELECT title, summary FROM context_candidates WHERE candidate_id = 'hint:hint-sensitive'"
        ).fetchone()
        materialized_hint_fts = conn.execute(
            "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH 'SECRETOLDMATERIALIZEDHINT'"
        ).fetchall()
        propagation = conn.execute(
            "SELECT event_type FROM release_propagation_events WHERE release_id = 'redact-sensitive'"
        ).fetchone()
        invalidations = {
            row[0]
            for row in conn.execute(
                "SELECT reason FROM index_invalidations WHERE invalidation_id LIKE 'idxinv:redact-sensitive:%'"
            ).fetchall()
        }

        self.assertEqual(candidate, ("[redacted]", "[redacted]"))
        self.assertEqual(candidate_fts, [])
        self.assertEqual(hint, ("[redacted]", "[redacted]"))
        self.assertEqual(hint_fts, [])
        self.assertEqual(materialized_hint, ("[redacted]", "[redacted]"))
        self.assertEqual(materialized_hint_fts, [])
        self.assertEqual(propagation, ("derived-index-sanitized",))
        self.assertIn("release-redacted:context-candidates", invalidations)
        self.assertIn("release-redacted:context-recall-hints", invalidations)

    def test_direct_context_recall_hint_redaction_sanitizes_hint_and_materialized_candidate(self) -> None:
        conn = self.open_db()
        hint = ContextRecallHint(
            hint_id="hint-direct",
            workroot_id="wr_demo",
            target_type="asset",
            target_id="asset-sensitive",
            title="Direct sensitive hint",
            summary="SECRETDIRECTHINT must be removed.",
            priority="critical",
        )
        upsert_context_recall_hint(conn, hint)
        upsert_context_candidate(
            conn,
            {
                "candidate_id": "hint:hint-direct",
                "workroot_id": "wr_demo",
                "source_type": "context_recall_hint",
                "source_id": "hint-direct",
                "title": "Direct materialized hint",
                "summary": "SECRETDIRECTMATERIALIZED must be removed.",
                "importance": "critical",
            },
        )

        create_redaction(
            conn,
            redaction_id="redact-direct-hint",
            workroot_id="wr_demo",
            target=ReleaseTargetRef(
                target_type="context_recall_hint",
                target_id="hint-direct",
                workroot_id="wr_demo",
            ),
            redacted_fields=("title", "summary"),
            redaction_reason="sensitive direct hint",
        )

        hint_row = conn.execute(
            "SELECT title, summary FROM context_recall_hints WHERE hint_id = 'hint-direct'"
        ).fetchone()
        hint_fts = conn.execute(
            "SELECT hint_id FROM context_recall_hints_fts WHERE context_recall_hints_fts MATCH 'SECRETDIRECTHINT'"
        ).fetchall()
        candidate = conn.execute(
            "SELECT title, summary FROM context_candidates WHERE candidate_id = 'hint:hint-direct'"
        ).fetchone()
        candidate_fts = conn.execute(
            "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH 'SECRETDIRECTMATERIALIZED'"
        ).fetchall()

        self.assertEqual(hint_row, ("[redacted]", "[redacted]"))
        self.assertEqual(hint_fts, [])
        self.assertEqual(candidate, ("[redacted]", "[redacted]"))
        self.assertEqual(candidate_fts, [])

    def test_direct_context_recall_hint_deletion_sanitizes_hint_and_materialized_candidate(self) -> None:
        conn = self.open_db()
        hint = ContextRecallHint(
            hint_id="hint-delete-direct",
            workroot_id="wr_demo",
            target_type="asset",
            target_id="asset-deleted",
            title="Direct deleted hint",
            summary="SECRETDELETEDHINT must be removed.",
            priority="critical",
        )
        upsert_context_recall_hint(conn, hint)
        upsert_context_candidate(
            conn,
            {
                "candidate_id": "hint:hint-delete-direct",
                "workroot_id": "wr_demo",
                "source_type": "context_recall_hint",
                "source_id": "hint-delete-direct",
                "title": "Direct deleted materialized hint",
                "summary": "SECRETDELETEDMATERIALIZED must be removed.",
                "importance": "critical",
            },
        )

        create_deletion_record(
            conn,
            deletion_id="delete-direct-hint",
            workroot_id="wr_demo",
            target=ReleaseTargetRef(
                target_type="context_recall_hint",
                target_id="hint-delete-direct",
                workroot_id="wr_demo",
            ),
            minimum_audit_note="delete direct hint",
        )

        hint_row = conn.execute(
            "SELECT title, summary FROM context_recall_hints WHERE hint_id = 'hint-delete-direct'"
        ).fetchone()
        hint_fts = conn.execute(
            "SELECT hint_id FROM context_recall_hints_fts WHERE context_recall_hints_fts MATCH 'SECRETDELETEDHINT'"
        ).fetchall()
        candidate = conn.execute(
            "SELECT title, summary FROM context_candidates WHERE candidate_id = 'hint:hint-delete-direct'"
        ).fetchone()
        candidate_fts = conn.execute(
            "SELECT candidate_id FROM context_candidates_fts WHERE context_candidates_fts MATCH 'SECRETDELETEDMATERIALIZED'"
        ).fetchall()

        self.assertEqual(hint_row, ("[deleted]", "[deleted]"))
        self.assertEqual(hint_fts, [])
        self.assertEqual(candidate, ("[deleted]", "[deleted]"))
        self.assertEqual(candidate_fts, [])

    def test_create_deletion_record_removes_indexed_chunk_derived_text(self) -> None:
        conn = self.open_db()
        target = ReleaseTargetRef(target_type="asset", target_id="asset-deleted", workroot_id="wr_demo")
        index_file_chunk(
            conn,
            workroot_id="wr_demo",
            file_id="file-deleted",
            chunk_id="chunk-deleted",
            relative_path="deleted.md",
            body="SECRETCHUNKBODY must be removed.",
            source_type="asset",
            source_id="asset-deleted",
        )

        create_deletion_record(
            conn,
            deletion_id="delete-sensitive",
            workroot_id="wr_demo",
            target=target,
            minimum_audit_note="delete sensitive chunk",
        )

        chunk = conn.execute("SELECT body FROM indexed_chunks WHERE chunk_id = 'chunk-deleted'").fetchone()
        chunk_fts = conn.execute(
            "SELECT chunk_id FROM indexed_chunks_fts WHERE indexed_chunks_fts MATCH 'SECRETCHUNKBODY'"
        ).fetchall()
        propagation = conn.execute(
            "SELECT event_type FROM release_propagation_events WHERE release_id = 'delete-sensitive'"
        ).fetchone()
        invalidations = {
            row[0]
            for row in conn.execute(
                "SELECT reason FROM index_invalidations WHERE invalidation_id LIKE 'idxinv:delete-sensitive:%'"
            ).fetchall()
        }

        self.assertEqual(chunk, ("[deleted]",))
        self.assertEqual(chunk_fts, [])
        self.assertEqual(propagation, ("derived-index-sanitized",))
        self.assertIn("release-deleted:indexed-chunks", invalidations)


if __name__ == "__main__":
    unittest.main()
