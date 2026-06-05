from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.capabilities.retrieval.providers.candidate_provider import upsert_context_candidate
from ai_workroot.capabilities.retrieval.providers.context_recall_hint_provider import (
    ContextRecallHint,
    upsert_context_recall_hint,
)
from ai_workroot.capabilities.relationships.operations import create_relationship_edge, create_relationship_node
from ai_workroot.capabilities.retrieval.providers.sqlite_fts import index_file_chunk
from ai_workroot.capabilities.context.builder import ContextRequest, build_context_package
from ai_workroot.commands.init_workroot import initialize_workroot


class ContextRetrievalSelectionTest(unittest.TestCase):
    def test_query_fts_and_relationships_influence_selected_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            user_dir.mkdir()
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
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
                create_relationship_node(
                    conn, node_id="node-task", workroot_id=workroot_id, node_type="task", title="Clean Mode task"
                )
                create_relationship_node(
                    conn, node_id="asset-clean", workroot_id=workroot_id, node_type="asset", title="Clean Mode Design"
                )
                create_relationship_node(
                    conn, node_id="asset-weak", workroot_id=workroot_id, node_type="asset", title="Weak query-only node"
                )
                create_relationship_edge(
                    conn,
                    edge_id="edge-clean",
                    workroot_id=workroot_id,
                    from_node_id="node-task",
                    to_node_id="asset-clean",
                    relationship_type="supports",
                    created_by="test",
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

    def test_context_recall_hint_affects_active_context_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            home = base / "home"
            user_dir = base / "project"
            init = initialize_workroot(name="Demo", directory=user_dir, ai_workroot_home=home)
            workroot_id = init.registration.workroot_id
            db_path = next((home / "workroots").glob("*/cache/workroot.sqlite"))
            with sqlite3.connect(db_path) as conn:
                upsert_context_recall_hint(
                    conn,
                    ContextRecallHint(
                        hint_id="hint-context-card",
                        workroot_id=workroot_id,
                        target_type="task",
                        target_id="task-context-card",
                        title="Context Card parity anchor",
                        summary="Recall this Context Card when parity is discussed.",
                        priority="critical",
                        recall_rule="always",
                    ),
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="parity", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Context Card parity anchor", package)
            self.assertIn("context_recall_hint", package)
            self.assertIn("candidate-fts-match", package)
            with sqlite3.connect(db_path) as conn:
                selection = conn.execute(
                    """
                    SELECT candidate_id, reason
                    FROM candidate_selections
                    WHERE candidate_id = 'hint:hint-context-card'
                    """
                ).fetchone()
                use_count = conn.execute(
                    """
                    SELECT use_count
                    FROM context_candidates
                    WHERE candidate_id = 'hint:hint-context-card'
                    """
                ).fetchone()[0]

            self.assertEqual(selection, ("hint:hint-context-card", "selected"))
            self.assertEqual(use_count, 1)

    def test_context_relationship_signals_resolve_canonical_target_nodes(self) -> None:
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
                        "candidate_id": "cand-canonical-asset",
                        "workroot_id": workroot_id,
                        "source_type": "asset",
                        "source_id": "asset-clean",
                        "title": "Canonical asset context",
                        "summary": "This candidate should collect relationship signals through target refs.",
                        "importance": "critical",
                        "context_policy": "always",
                    },
                )
                create_relationship_node(
                    conn,
                    node_id="node-task",
                    workroot_id=workroot_id,
                    node_type="task",
                    title="Related task",
                )
                create_relationship_node(
                    conn,
                    node_id="node-asset-clean",
                    workroot_id=workroot_id,
                    node_type="asset",
                    title="Clean asset node",
                    target_type="asset",
                    target_id="asset-clean",
                )
                create_relationship_edge(
                    conn,
                    edge_id="edge-canonical-asset",
                    workroot_id=workroot_id,
                    from_node_id="node-task",
                    to_node_id="node-asset-clean",
                    relationship_type="supports",
                    created_by="test",
                    confidence=0.9,
                )

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="canonical", debug=True),
                ai_workroot_home=home,
            )

            self.assertIn("Canonical asset context", package)
            self.assertIn("relationship-edge", package)
            self.assertIn("Relationship Signals", package)
            self.assertIn("edge-canonical-asset", package)


if __name__ == "__main__":
    unittest.main()
