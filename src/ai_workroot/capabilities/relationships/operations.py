"""Active Relationship Network authoring services."""

from __future__ import annotations

import sqlite3

from ai_workroot.capabilities.relationships.model import (
    RelationshipEdge,
    RelationshipEvidence,
    RelationshipNode,
    RelationshipSignal,
    SourceRef,
)
from ai_workroot.state.sqlite import record_index_invalidation


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


def relationship_signals_for_sources(
    conn: sqlite3.Connection,
    workroot_id: str,
    source_ids: set[str],
    *,
    limit: int = 10,
) -> list[RelationshipSignal]:
    return _relationship_signals_for_node_ids(conn, workroot_id, source_ids, limit=limit)


def relationship_signals_for_source_refs(
    conn: sqlite3.Connection,
    workroot_id: str,
    source_refs: set[tuple[str, str]],
    *,
    limit: int = 10,
) -> list[RelationshipSignal]:
    normalized_refs = {
        SourceRef(source_type=str(source_type), source_id=str(source_id))
        for source_type, source_id in source_refs
        if source_type and source_id
    }
    if not normalized_refs:
        return []

    node_ids = {source_ref.source_id for source_ref in normalized_refs}
    refs_by_node_id: dict[str, set[SourceRef]] = {}
    for source_ref in normalized_refs:
        refs_by_node_id.setdefault(source_ref.source_id, set()).add(source_ref)
    target_clause = " OR ".join("(target_type = ? AND target_id = ?)" for _ in normalized_refs)
    target_params: list[str] = [workroot_id]
    for source_ref in sorted(normalized_refs, key=lambda ref: (ref.source_type, ref.source_id)):
        target_params.extend([source_ref.source_type, source_ref.source_id])
    rows = conn.execute(
        f"""
        SELECT node_id, target_type, target_id
        FROM relationship_nodes
        WHERE workroot_id = ?
          AND ({target_clause})
        """,
        target_params,
    ).fetchall()
    ref_by_target = {(source_ref.source_type, source_ref.source_id): source_ref for source_ref in normalized_refs}
    for row in rows:
        node_id = str(row[0])
        source_ref = ref_by_target.get((str(row[1] or ""), str(row[2] or "")))
        if source_ref is None:
            continue
        node_ids.add(node_id)
        refs_by_node_id.setdefault(node_id, set()).add(source_ref)

    return _relationship_signals_for_node_ids(
        conn,
        workroot_id,
        node_ids,
        limit=limit,
        refs_by_node_id=refs_by_node_id,
    )


def _relationship_signals_for_node_ids(
    conn: sqlite3.Connection,
    workroot_id: str,
    node_ids: set[str],
    *,
    limit: int = 10,
    refs_by_node_id: dict[str, set[SourceRef]] | None = None,
) -> list[RelationshipSignal]:
    if not node_ids:
        return []
    sorted_node_ids = sorted(node_ids)
    placeholders = ",".join("?" for _ in sorted_node_ids)
    params = [workroot_id, *sorted_node_ids, *sorted_node_ids, limit]
    rows = conn.execute(
        f"""
        SELECT edge_id, from_node_id, to_node_id, relationship_type, confidence
        FROM relationship_edges
        WHERE workroot_id = ?
          AND COALESCE(status, 'active') = 'active'
          AND (from_node_id IN ({placeholders}) OR to_node_id IN ({placeholders}))
        ORDER BY COALESCE(confidence, 0) DESC, edge_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [
        RelationshipSignal(
            edge_id=str(row[0]),
            from_node_id=str(row[1]),
            to_node_id=str(row[2]),
            relationship_type=str(row[3]),
            confidence=float(row[4] or 0.0),
            matched_source_refs=_matched_source_refs(
                refs_by_node_id,
                (str(row[1]), str(row[2])),
            ),
        )
        for row in rows
    ]


def _matched_source_refs(
    refs_by_node_id: dict[str, set[SourceRef]] | None,
    node_ids: tuple[str, str],
) -> tuple[SourceRef, ...]:
    if refs_by_node_id is None:
        return ()
    refs: set[SourceRef] = set()
    for node_id in node_ids:
        refs.update(refs_by_node_id.get(node_id, set()))
    return tuple(sorted(refs, key=lambda ref: (ref.source_type, ref.source_id)))


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
