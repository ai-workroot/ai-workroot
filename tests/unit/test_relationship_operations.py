from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.relationships.operations import (
    attach_relationship_evidence,
    create_relationship_edge,
    create_relationship_node,
    query_relationships,
)
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class RuntimeRelationshipsTest(unittest.TestCase):
    def open_db(self) -> sqlite3.Connection:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "workroot.sqlite"
        initialize_workroot_sqlite(db_path)
        return sqlite3.connect(db_path)

    def test_create_node_edge_evidence_and_query_relationships(self) -> None:
        conn = self.open_db()

        source = create_relationship_node(conn, node_id="task-1", workroot_id="wr_demo", node_type="task", title="Task")
        target = create_relationship_node(
            conn, node_id="asset-1", workroot_id="wr_demo", node_type="asset", title="Asset"
        )
        edge = create_relationship_edge(
            conn,
            edge_id="edge-1",
            workroot_id="wr_demo",
            from_node_id=source.node_id,
            to_node_id=target.node_id,
            relationship_type="supports",
            confidence=0.9,
            created_by="test",
        )
        evidence = attach_relationship_evidence(
            conn,
            evidence_id="evidence-1",
            edge_id=edge.edge_id,
            evidence_type="context_trace",
            source_ref="ctxtrace-1",
        )

        relationships = query_relationships(conn, "wr_demo", source_ids={"task-1"})

        self.assertEqual(source.node_type, "task")
        self.assertEqual(target.node_type, "asset")
        self.assertEqual(edge.relationship_type, "supports")
        self.assertEqual(evidence.edge_id, "edge-1")
        self.assertEqual([item.edge_id for item in relationships], ["edge-1"])
        self.assertEqual(
            conn.execute(
                "SELECT evidence_type, source_ref FROM relationship_evidence WHERE evidence_id = 'evidence-1'"
            ).fetchone(),
            ("context_trace", "ctxtrace-1"),
        )
        invalidations = {
            row
            for row in conn.execute(
                """
                SELECT index_id, reason
                FROM index_invalidations
                WHERE invalidation_id LIKE 'idxinv:wr_demo:relationship:%'
                """
            ).fetchall()
        }
        self.assertIn(("relationship-network", "relationship-node-changed:task-1"), invalidations)
        self.assertIn(("relationship-network", "relationship-node-changed:asset-1"), invalidations)
        self.assertIn(("relationship-network", "relationship-edge-changed:edge-1"), invalidations)
        self.assertIn(("relationship-network", "relationship-evidence-changed:evidence-1"), invalidations)

    def test_create_node_accepts_explicit_canonical_target(self) -> None:
        conn = self.open_db()

        node = create_relationship_node(
            conn,
            node_id="graph-asset-node-1",
            workroot_id="wr_demo",
            node_type="asset",
            title="Asset node",
            target_type="asset",
            target_id="asset-1",
        )

        row = conn.execute(
            """
            SELECT node_type, title, target_type, target_id
            FROM relationship_nodes
            WHERE workroot_id = 'wr_demo' AND node_id = 'graph-asset-node-1'
            """
        ).fetchone()
        self.assertEqual(node.target_type, "asset")
        self.assertEqual(node.target_id, "asset-1")
        self.assertEqual(row, ("asset", "Asset node", "asset", "asset-1"))

    def test_create_node_rejects_partial_canonical_target(self) -> None:
        conn = self.open_db()

        with self.assertRaises(ValueError):
            create_relationship_node(
                conn,
                node_id="graph-asset-node-1",
                workroot_id="wr_demo",
                node_type="asset",
                target_type="asset",
            )

    def test_create_relationship_edge_rejects_missing_nodes(self) -> None:
        conn = self.open_db()

        with self.assertRaises(ValueError):
            create_relationship_edge(
                conn,
                edge_id="edge-missing",
                workroot_id="wr_demo",
                from_node_id="missing-a",
                to_node_id="missing-b",
                relationship_type="supports",
                created_by="test",
            )


if __name__ == "__main__":
    unittest.main()
