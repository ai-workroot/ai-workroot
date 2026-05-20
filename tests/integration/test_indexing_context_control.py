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


class IndexingContextControlTest(unittest.TestCase):
    def test_query_fts_and_relationships_influence_selected_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            init = initialize_workroot(name="Demo", directory=user_dir, native_agent_entry=False, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-always",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-always",
                        "title": "General notes",
                        "summary": "Always visible but unrelated.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-clean",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-clean",
                        "title": "Clean Mode Design",
                        "summary": "Managed state stays outside user directories.",
                        "importance": "normal",
                    },
                )
                upsert_context_candidate(
                    conn,
                    {
                        "candidate_id": "cand-blocked",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-blocked",
                        "title": "Sensitive blocked note",
                        "summary": "This should not enter ordinary context.",
                        "importance": "critical",
                        "safety_policy": "sensitive",
                    },
                )
                index_file_chunk(
                    conn,
                    workroot_id=workroot_id,
                    file_id="file-clean",
                    chunk_id="chunk-clean",
                    relative_path="design.md",
                    body="Clean Mode keeps managed state outside user directories.",
                )
                upsert_relationship_node(conn, "node-task", workroot_id, "task", "Clean Mode task")
                upsert_relationship_node(conn, "asset-clean", workroot_id, "asset", "Clean Mode Design")
                upsert_relationship_node(conn, "asset-weak", workroot_id, "asset", "Weak query-only node")
                upsert_relationship_edge(
                    conn,
                    edge_id="edge-clean",
                    workroot_id=workroot_id,
                    from_node_id="node-task",
                    to_node_id="asset-clean",
                    relationship_type="supports",
                    confidence=0.9,
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Clean Mode", debug=True, hard_token_limit=900),
                ai_workroot_home=home,
            )

            self.assertIn("Clean Mode Design", package)
            self.assertIn("candidate-fts-match", package)
            self.assertIn("file-fts-match", package)
            self.assertIn("Relationship Signals", package)
            self.assertIn("edge-clean", package)
            self.assertNotIn("Weak query-only node", package)
            self.assertNotIn("Sensitive blocked note", package)
            self.assertIn("candidateSources", package)
            self.assertIn("tokenUsage", package)
            self.assertIn("hard=900", package)

    def test_hard_token_limit_uses_final_fallback_and_records_trim(self) -> None:
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
                        "candidate_id": "cand-long",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-long",
                        "title": "Long candidate",
                        "summary": "Clean Mode " * 300,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Clean Mode", debug=True, hard_token_limit=80, target_tokens=40),
                ai_workroot_home=home,
            )

            self.assertIn("trimSteps", package)
            self.assertIn("final-fallback", package)
            self.assertLessEqual(len(package), 80 * 6)


if __name__ == "__main__":
    unittest.main()
