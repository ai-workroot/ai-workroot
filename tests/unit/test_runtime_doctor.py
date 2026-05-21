from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.indexing.providers.candidate_provider import upsert_context_candidate
from ai_workroot.indexing.providers.context_recall_hint_provider import ContextRecallHint, upsert_context_recall_hint
from ai_workroot.indexing.providers.sqlite_fts import index_file_chunk
from ai_workroot.runtime.doctor import run_doctor
from ai_workroot.runtime.init import initialize_workroot


class RuntimeDoctorTest(unittest.TestCase):
    def test_doctor_fails_logic_integrity_orphans_and_missing_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(
                name="Integrity Workroot",
                directory=user_dir,
                native_agent_entry=False,
                ai_workroot_home=home,
            )
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO relationship_edges (
                      edge_id, workroot_id, from_node_id, to_node_id, relationship_type, confidence, status
                    )
                    VALUES ('edge-orphan', ?, 'missing-a', 'missing-b', 'supports', 1.0, 'active')
                    """,
                    (workroot_id,),
                )
                conn.execute(
                    """
                    INSERT INTO relationship_evidence (evidence_id, edge_id, evidence_type, source_ref)
                    VALUES ('evidence-orphan', 'missing-edge', 'context_trace', 'ctxtrace-missing')
                    """
                )
                conn.execute(
                    """
                    INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                    VALUES ('release-missing-asset', ?, 'asset', 'asset-missing', 'quiet', 'default')
                    """,
                    (workroot_id,),
                )
                conn.execute(
                    """
                    INSERT INTO context_packages (package_id, workroot_id, mode, rendered)
                    VALUES ('ctxpkg-orphan', ?, 'standard', '# package')
                    """,
                    (workroot_id,),
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-missing-task",
                        "workroot_id": workroot_id,
                        "source_type": "task",
                        "source_id": "task-missing",
                        "title": "Missing task candidate",
                        "summary": "Candidate source does not exist.",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO context_recall_hints (
                      hint_id, workroot_id, target_type, target_id, title, summary, lifecycle_status
                    )
                    VALUES ('hint-missing-asset', ?, 'asset', 'asset-missing-hint', 'Missing hint target', 'missing', 'active')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            result = run_doctor(cwd=user_dir, ai_workroot_home=home)

            self.assertEqual(result.status, "FAIL")
            rendered = result.render_text()
            self.assertIn("relationship edge edge-orphan references missing from_node missing-a", rendered)
            self.assertIn("relationship evidence evidence-orphan references missing edge missing-edge", rendered)
            self.assertIn("release target asset:asset-missing is missing", rendered)
            self.assertIn("context candidate cand-missing-task source task:task-missing is missing", rendered)
            self.assertIn("context recall hint hint-missing-asset target asset:asset-missing-hint is missing", rendered)
            self.assertIn("context package ctxpkg-orphan has no trace", rendered)

    def test_doctor_fails_when_redacted_target_leaks_in_derived_candidate_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(
                name="Leaky Workroot",
                directory=user_dir,
                native_agent_entry=False,
                ai_workroot_home=home,
            )
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-leaky",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-leaky",
                        "title": "Leaky payroll candidate",
                        "summary": "LEAKEDPAYROLLTEXT must not survive a redaction.",
                        "importance": "critical",
                    },
                )
                conn.execute(
                    """
                    INSERT INTO redactions (
                      redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason
                    )
                    VALUES ('redact-leaky', ?, 'asset', 'asset-leaky', 'summary', 'test leak')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            result = run_doctor(cwd=user_dir, ai_workroot_home=home)

            self.assertEqual(result.status, "FAIL")
            rendered = result.render_text()
            self.assertIn("release-derived index safety", rendered)
            self.assertIn("context_candidates:cand-leaky", rendered)

    def test_doctor_fails_when_deleted_target_leaks_in_fts_derived_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(
                name="Leaky FTS Workroot",
                directory=user_dir,
                native_agent_entry=False,
                ai_workroot_home=home,
            )
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-leaky",
                    chunk_id="chunk-leaky",
                    relative_path="leaky.md",
                    body="[deleted]",
                    source_type="asset",
                    source_id="asset-deleted",
                )
                conn.execute("DELETE FROM indexed_chunks_fts WHERE chunk_id = 'chunk-leaky'")
                conn.execute(
                    "INSERT INTO indexed_chunks_fts (chunk_id, body) VALUES ('chunk-leaky', 'LEAKEDCHUNKFTSTEXT')"
                )
                conn.execute(
                    """
                    INSERT INTO deletion_records (deletion_id, workroot_id, target_type, target_id, minimum_audit_note)
                    VALUES ('delete-leaky', ?, 'asset', 'asset-deleted', 'test leak')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            result = run_doctor(cwd=user_dir, ai_workroot_home=home)

            self.assertEqual(result.status, "FAIL")
            rendered = result.render_text()
            self.assertIn("release-derived index safety", rendered)
            self.assertIn("indexed_chunks_fts:chunk-leaky", rendered)

    def test_doctor_fails_when_direct_context_recall_hint_target_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(
                name="Leaky Direct Hint Workroot",
                directory=user_dir,
                native_agent_entry=False,
                ai_workroot_home=home,
            )
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-direct",
                        workroot_id=workroot_id,
                        target_type="asset",
                        target_id="asset-sensitive",
                        title="Direct leaked hint",
                        summary="SECRETDIRECTDOCTOR must be detected.",
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO redactions (
                      redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason
                    )
                    VALUES ('redact-direct-hint', ?, 'context_recall_hint', 'hint-direct', 'summary', 'sensitive')
                    """,
                    (workroot_id,),
                )
                conn.commit()

            result = run_doctor(cwd=user_dir, ai_workroot_home=home)

            self.assertEqual(result.status, "FAIL")
            rendered = result.render_text()
            self.assertIn("release-derived index safety", rendered)
            self.assertIn("context_recall_hints:hint-direct", rendered)


if __name__ == "__main__":
    unittest.main()
