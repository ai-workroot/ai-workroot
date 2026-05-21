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

    def test_context_runtime_persists_package_trace_selection_and_trim_decisions(self) -> None:
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
                        "candidate_id": "cand-persist",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-persist",
                        "title": "Persisted context candidate",
                        "summary": "Persistence " * 200,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="Persistence", debug=True, hard_token_limit=80, target_tokens=40),
                ai_workroot_home=home,
            )

            with sqlite3.connect(db_path) as conn:
                package_rows = conn.execute("SELECT mode, rendered FROM context_packages").fetchall()
                trace_rows = conn.execute("SELECT debug_json FROM context_traces").fetchall()
                selection_rows = conn.execute("SELECT candidate_id, reason FROM candidate_selections").fetchall()
                trim_rows = conn.execute("SELECT section, reason FROM budget_trim_decisions").fetchall()
                use_count = conn.execute(
                    "SELECT use_count FROM context_candidates WHERE candidate_id = 'cand-persist'"
                ).fetchone()[0]

            self.assertIn("TokenUsage:", package)
            self.assertEqual(len(package_rows), 1)
            self.assertEqual(package_rows[0][0], "standard")
            self.assertIn("# AI Workroot Context Package", package_rows[0][1])
            self.assertEqual(len(trace_rows), 1)
            self.assertIn("final-fallback", trace_rows[0][0])
            self.assertIn(("cand-persist", "selected"), selection_rows)
            self.assertIn(("rendered-package", "final-fallback"), trim_rows)
            self.assertEqual(use_count, 1)

    def test_final_rendered_package_respects_hard_token_limit_after_trim_marker(self) -> None:
        from ai_workroot.runtime.context import estimate_tokens

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
                        "candidate_id": "cand-long-marker",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-long-marker",
                        "title": "Long marker candidate",
                        "summary": "没有空格的中文内容" * 200,
                        "importance": "critical",
                    },
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="中文", debug=True, hard_token_limit=60, target_tokens=30),
                ai_workroot_home=home,
            )

            self.assertLessEqual(estimate_tokens(package), 60)


if __name__ == "__main__":
    unittest.main()
