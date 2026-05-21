"""Relationship Network traversal provider."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class RelationshipSignal:
    edge_id: str
    from_node_id: str
    to_node_id: str
    relationship_type: str
    confidence: float
    reason: str = "relationship-edge"


def upsert_relationship_node(
    conn: sqlite3.Connection,
    node_id: str,
    workroot_id: str,
    node_type: str,
    title: str,
    *,
    target_type: str = "",
    target_id: str = "",
) -> None:
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
    conn.commit()


def upsert_relationship_edge(
    conn: sqlite3.Connection,
    *,
    edge_id: str,
    workroot_id: str,
    from_node_id: str,
    to_node_id: str,
    relationship_type: str,
    confidence: float,
    status: str = "active",
) -> None:
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
    conn.commit()


def relationship_signals_for_sources(
    conn: sqlite3.Connection,
    workroot_id: str,
    source_ids: set[str],
    *,
    limit: int = 10,
) -> list[RelationshipSignal]:
    if not source_ids:
        return []
    placeholders = ",".join("?" for _ in source_ids)
    params = [workroot_id, *sorted(source_ids), *sorted(source_ids), limit]
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
        )
        for row in rows
    ]


def _validate_node_target(target_type: str, target_id: str) -> None:
    if bool(target_type) != bool(target_id):
        raise ValueError("relationship node canonical target requires both target_type and target_id")
