from __future__ import annotations

import sqlite3
import unittest

from ai_workroot.core.release import ReleaseTargetRef
from ai_workroot.indexing.providers.candidate_provider import CandidateMatch, upsert_context_candidate
from ai_workroot.indexing.providers.relationship_provider import (
    RelationshipSignal,
    upsert_relationship_edge,
    upsert_relationship_node,
)
from ai_workroot.indexing.providers.release_provider import (
    CandidateReleaseTargetResolver,
    evaluate_release_targets,
)
from ai_workroot.indexing.providers.sqlite_fts import index_file_chunk, search_fts
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


class ReleaseTargetResolverTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        conn = sqlite3.connect(":memory:")
        initialize_workroot_sqlite_for_connection(conn)
        return conn

    def test_candidate_resolver_maps_recallable_sources_to_canonical_targets(self) -> None:
        conn = self.open_db()
        with conn:
            resolver = CandidateReleaseTargetResolver(conn, "wr_demo")

            for source_type, source_id in (
                ("asset", "asset-1"),
                ("task", "task-1"),
                ("work_action", "action-1"),
                ("agent_run", "run-1"),
                ("checkpoint", "checkpoint-1"),
                ("handoff", "handoff-1"),
                ("retrieval_card", "card-1"),
            ):
                with self.subTest(source_type=source_type):
                    match = candidate(source_type, source_id)
                    refs = resolver.resolve_candidate(match)
                    self.assertIn(ref(source_type, source_id), refs)

    def test_context_candidate_resolver_uses_underlying_candidate_source(self) -> None:
        conn = self.open_db()
        with conn:
            upsert_context_candidate(
                conn,
                {
                    "candidate_id": "cand-underlying",
                    "workroot_id": "wr_demo",
                    "source_type": "asset",
                    "source_id": "asset-underlying",
                    "title": "Underlying",
                    "summary": "Underlying summary.",
                },
            )
            resolver = CandidateReleaseTargetResolver(conn, "wr_demo")

            refs = resolver.resolve_candidate(candidate("context_candidate", "cand-underlying"))

            self.assertIn(ref("asset", "asset-underlying"), refs)
            self.assertNotIn(ref("context_candidate", "cand-underlying"), refs)

    def test_context_recall_hint_resolver_includes_hint_and_target_refs(self) -> None:
        conn = self.open_db()
        with conn:
            conn.execute(
                """
                INSERT INTO context_recall_hints (
                  hint_id, workroot_id, target_type, target_id, title, lifecycle_status
                )
                VALUES ('hint-action', 'wr_demo', 'work_action', 'action-1', 'Action hint', 'active')
                """
            )
            resolver = CandidateReleaseTargetResolver(conn, "wr_demo")

            refs = resolver.resolve_candidate(candidate("context_recall_hint", "hint-action"))

            self.assertIn(ref("context_recall_hint", "hint-action"), refs)
            self.assertIn(ref("work_action", "action-1"), refs)

    def test_fts_match_resolver_uses_chunk_and_owning_asset_targets(self) -> None:
        conn = self.open_db()
        with conn:
            index_file_chunk(
                conn,
                workroot_id="wr_demo",
                file_id="file-1",
                chunk_id="chunk-1",
                relative_path="notes.md",
                body="release resolver needle",
                source_type="asset",
                source_id="asset-1",
            )
            matches, error = search_fts(conn, "wr_demo", "needle")
            self.assertIsNone(error)
            match = matches[0]
            resolver = CandidateReleaseTargetResolver(conn, "wr_demo")

            refs = resolver.resolve_fts_match(match)

            self.assertIn(ref("indexed_chunk", "chunk-1"), refs)
            self.assertIn(ref("asset", "asset-1"), refs)

    def test_relationship_signal_resolver_includes_edge_and_related_node_targets(self) -> None:
        conn = self.open_db()
        with conn:
            upsert_relationship_node(conn, "asset-1", "wr_demo", "asset", "Asset")
            upsert_relationship_node(conn, "task-1", "wr_demo", "task", "Task")
            upsert_relationship_edge(
                conn,
                edge_id="edge-1",
                workroot_id="wr_demo",
                from_node_id="asset-1",
                to_node_id="task-1",
                relationship_type="supports",
                confidence=0.9,
            )
            signal = RelationshipSignal(
                edge_id="edge-1",
                from_node_id="asset-1",
                to_node_id="task-1",
                relationship_type="supports",
                confidence=0.9,
            )
            resolver = CandidateReleaseTargetResolver(conn, "wr_demo")

            refs = resolver.resolve_relationship_signal(signal)

            self.assertIn(ref("relationship_edge", "edge-1"), refs)
            self.assertIn(ref("asset", "asset-1"), refs)
            self.assertIn(ref("task", "task-1"), refs)

    def test_relationship_signal_resolver_uses_explicit_node_canonical_target(self) -> None:
        conn = self.open_db()
        with conn:
            upsert_relationship_node(
                conn,
                "graph-asset-node-1",
                "wr_demo",
                "asset",
                "Asset node",
                target_type="asset",
                target_id="asset-1",
            )
            upsert_relationship_node(
                conn,
                "graph-task-node-1",
                "wr_demo",
                "task",
                "Task node",
                target_type="task",
                target_id="task-1",
            )
            upsert_relationship_edge(
                conn,
                edge_id="edge-canonical",
                workroot_id="wr_demo",
                from_node_id="graph-asset-node-1",
                to_node_id="graph-task-node-1",
                relationship_type="supports",
                confidence=0.9,
            )
            signal = RelationshipSignal(
                edge_id="edge-canonical",
                from_node_id="graph-asset-node-1",
                to_node_id="graph-task-node-1",
                relationship_type="supports",
                confidence=0.9,
            )
            resolver = CandidateReleaseTargetResolver(conn, "wr_demo")

            refs = resolver.resolve_relationship_signal(signal)

            self.assertIn(ref("relationship_edge", "edge-canonical"), refs)
            self.assertIn(ref("asset", "asset-1"), refs)
            self.assertIn(ref("task", "task-1"), refs)
            self.assertNotIn(ref("asset", "graph-asset-node-1"), refs)
            self.assertNotIn(ref("task", "graph-task-node-1"), refs)

    def test_release_evaluator_uses_most_protective_level_across_all_refs(self) -> None:
        conn = self.open_db()
        with conn:
            conn.executemany(
                """
                INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
                VALUES (?, 'wr_demo', ?, ?, ?, ?)
                """,
                [
                    ("rel-quiet", "asset", "asset-1", "quiet", "ordinary-context-allowed"),
                    ("rel-redacted", "task", "task-1", "redacted", "ordinary-context-excluded"),
                ],
            )
            conn.execute(
                """
                INSERT INTO deletion_records (deletion_id, workroot_id, target_type, target_id, minimum_audit_note)
                VALUES ('del-1', 'wr_demo', 'work_action', 'action-1', 'deleted')
                """
            )

            result = evaluate_release_targets(
                conn,
                "wr_demo",
                (
                    ref("asset", "asset-1"),
                    ref("task", "task-1"),
                    ref("work_action", "action-1"),
                ),
            )

            self.assertEqual(result.level, "deleted")
            self.assertTrue(result.strictly_protected)
            self.assertIn(ref("work_action", "action-1"), result.matched_targets)


def candidate(source_type: str, source_id: str) -> CandidateMatch:
    return CandidateMatch(
        candidate_id=f"cand-{source_type}-{source_id}",
        source_type=source_type,
        source_id=source_id,
        title=f"{source_type} title",
        summary=f"{source_type} summary",
        importance="normal",
        context_policy="task-related",
        safety_policy="",
        score=0.5,
        reasons=("test",),
    )


def ref(target_type: str, target_id: str) -> ReleaseTargetRef:
    return ReleaseTargetRef(target_type=target_type, target_id=target_id, workroot_id="wr_demo")


def initialize_workroot_sqlite_for_connection(conn: sqlite3.Connection) -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        disk = sqlite3.connect(db_path)
        try:
            disk.backup(conn)
        finally:
            disk.close()


if __name__ == "__main__":
    unittest.main()
