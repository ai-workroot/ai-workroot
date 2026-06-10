from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.retrieval.providers.candidate_provider import upsert_context_candidate
from ai_workroot.capabilities.retrieval.providers.sqlite_fts import index_file_chunk
from ai_workroot.capabilities.context.builder import ContextRequest, build_context_package
from ai_workroot.commands.init_workroot import initialize_workroot


class ReleaseProtectionTargetsNegativeTest(unittest.TestCase):
    def test_context_candidate_source_resolves_underlying_asset_not_candidate_itself(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
                ContextRequest(
                    agent="codex",
                    cwd=user_dir,
                    query="needle",
                    debug=True,
                    work_signal={
                        "phase": "orienting",
                        "work_kind": "investigation",
                        "intended_action": "diagnose",
                        "focus": "needle indexed evidence",
                    },
                ),
                ai_workroot_home=home,
            )

            self.assertIn("safe.md: file-fts-match", package)
            self.assertIn("Safe indexed file", package)
            self.assertNotIn("protected.md", package)
            self.assertNotIn("Protected indexed file", package)
            self.assertIn("ftsReleaseFilters", package)
            self.assertIn("chunk-protected:redacted", package)


if __name__ == "__main__":
    unittest.main()
