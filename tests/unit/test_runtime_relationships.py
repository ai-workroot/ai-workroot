from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.runtime.relationships import (
    attach_relationship_evidence,
    create_relationship_edge,
    create_relationship_node,
    query_relationships,
)
from ai_workroot.storage.sqlite import initialize_workroot_sqlite


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
        target = create_relationship_node(conn, node_id="asset-1", workroot_id="wr_demo", node_type="asset", title="Asset")
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
            conn.execute("SELECT evidence_type, source_ref FROM relationship_evidence WHERE evidence_id = 'evidence-1'").fetchone(),
            ("context_trace", "ctxtrace-1"),
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
