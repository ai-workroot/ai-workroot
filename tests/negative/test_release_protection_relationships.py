from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.retrieval.providers.candidate_provider import upsert_context_candidate
from ai_workroot.relationships.operations import create_relationship_edge, create_relationship_node
from ai_workroot.context.builder import ContextRequest, build_context_package
from ai_workroot.commands.init_workroot import initialize_workroot


class ReleaseProtectionRelationshipsNegativeTest(unittest.TestCase):
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
                create_relationship_node(
                    conn, node_id="asset-seed", workroot_id=workroot_id, node_type="asset", title="Seed asset"
                )
                create_relationship_node(
                    conn, node_id="task-deleted", workroot_id=workroot_id, node_type="task", title="Deleted node"
                )
                create_relationship_node(
                    conn,
                    node_id="task-tombstone",
                    workroot_id=workroot_id,
                    node_type="task",
                    title="Tombstone node",
                )
                create_relationship_edge(
                    conn,
                    edge_id="edge-deleted",
                    workroot_id=workroot_id,
                    from_node_id="asset-seed",
                    to_node_id="task-deleted",
                    relationship_type="supports",
                    created_by="test",
                    confidence=0.9,
                )
                create_relationship_edge(
                    conn,
                    edge_id="edge-tombstone",
                    workroot_id=workroot_id,
                    from_node_id="asset-seed",
                    to_node_id="task-tombstone",
                    relationship_type="references",
                    created_by="test",
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
