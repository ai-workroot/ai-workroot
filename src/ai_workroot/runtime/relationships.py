"""Active Relationship Network authoring services."""

from __future__ import annotations

import sqlite3

from ai_workroot.core.common import SourceRef
from ai_workroot.core.relationships import RelationshipEdge, RelationshipEvidence, RelationshipNode
from ai_workroot.indexing.providers.relationship_provider import RelationshipSignal, relationship_signals_for_sources
from ai_workroot.storage.sqlite import record_index_invalidation


def create_relationship_node(
    conn: sqlite3.Connection,
    *,
    node_id: str,
    workroot_id: str,
    node_type: str,
    title: str = "",
    target_type: str = "",
    target_id: str = "",
) -> RelationshipNode:
    _validate_node_target(target_type, target_id)
    conn.execute(
        """
        INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          node_type=excluded.node_type,
          title=excluded.title,
          target_type=excluded.target_type,
          target_id=excluded.target_id
        """,
        (node_id, workroot_id, node_type, title, target_type or None, target_id or None),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="relationship-network",
        subject_type="relationship",
        subject_id=f"node:{node_id}",
        reason=f"relationship-node-changed:{node_id}",
    )
    conn.commit()
    return RelationshipNode(
        node_id=node_id,
        workroot_id=workroot_id,
        node_type=node_type,
        title=title,
        target_type=target_type,
        target_id=target_id,
    )


def create_relationship_edge(
    conn: sqlite3.Connection,
    *,
    edge_id: str,
    workroot_id: str,
    from_node_id: str,
    to_node_id: str,
    relationship_type: str,
    created_by: str,
    confidence: float = 1.0,
    status: str = "active",
) -> RelationshipEdge:
    _ensure_node_exists(conn, workroot_id, from_node_id)
    _ensure_node_exists(conn, workroot_id, to_node_id)
    edge = RelationshipEdge(
        edge_id=edge_id,
        workroot_id=workroot_id,
        from_node_id=from_node_id,
        to_node_id=to_node_id,
        relationship_type=relationship_type,
        created_by=created_by,
        confidence=confidence,
        status=status,
    )
    conn.execute(
        """
        INSERT INTO relationship_edges (
          edge_id, workroot_id, from_node_id, to_node_id, relationship_type, confidence, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(edge_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          from_node_id=excluded.from_node_id,
          to_node_id=excluded.to_node_id,
          relationship_type=excluded.relationship_type,
          confidence=excluded.confidence,
          status=excluded.status
        """,
        (edge_id, workroot_id, from_node_id, to_node_id, relationship_type, confidence, status),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="relationship-network",
        subject_type="relationship",
        subject_id=f"edge:{edge_id}",
        reason=f"relationship-edge-changed:{edge_id}",
    )
    conn.commit()
    return edge


def attach_relationship_evidence(
    conn: sqlite3.Connection,
    *,
    evidence_id: str,
    edge_id: str,
    evidence_type: str,
    source_ref: str,
) -> RelationshipEvidence:
    row = conn.execute("SELECT 1 FROM relationship_edges WHERE edge_id = ? LIMIT 1", (edge_id,)).fetchone()
    if row is None:
        raise ValueError(f"relationship edge does not exist: {edge_id}")
    conn.execute(
        """
        INSERT INTO relationship_evidence (evidence_id, edge_id, evidence_type, source_ref)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(evidence_id) DO UPDATE SET
          edge_id=excluded.edge_id,
          evidence_type=excluded.evidence_type,
          source_ref=excluded.source_ref
        """,
        (evidence_id, edge_id, evidence_type, source_ref),
    )
    workroot_row = conn.execute(
        "SELECT workroot_id FROM relationship_edges WHERE edge_id = ? LIMIT 1",
        (edge_id,),
    ).fetchone()
    workroot_id = str(workroot_row[0]) if workroot_row else ""
    if workroot_id:
        record_index_invalidation(
            conn,
            workroot_id=workroot_id,
            index_id="relationship-network",
            subject_type="relationship",
            subject_id=f"evidence:{evidence_id}",
            reason=f"relationship-evidence-changed:{evidence_id}",
        )
    conn.commit()
    return RelationshipEvidence(
        evidence_id=evidence_id,
        edge_id=edge_id,
        evidence_type=evidence_type,
        source_ref=SourceRef(source_type=evidence_type, source_id=source_ref),
    )


def query_relationships(
    conn: sqlite3.Connection,
    workroot_id: str,
    *,
    source_ids: set[str],
    limit: int = 10,
) -> list[RelationshipSignal]:
    return relationship_signals_for_sources(conn, workroot_id, source_ids, limit=limit)


def _ensure_node_exists(conn: sqlite3.Connection, workroot_id: str, node_id: str) -> None:
    row = conn.execute(
        """
        SELECT 1
        FROM relationship_nodes
        WHERE workroot_id = ? AND node_id = ?
        LIMIT 1
        """,
        (workroot_id, node_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"relationship node does not exist for Workroot {workroot_id}: {node_id}")


def _validate_node_target(target_type: str, target_id: str) -> None:
    if bool(target_type) != bool(target_id):
        raise ValueError("relationship node canonical target requires both target_type and target_id")
