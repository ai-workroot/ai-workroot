"""Release Control lookup, target resolution, and recall protection."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3
from typing import Iterable

from ai_workroot.release.evaluation import evaluate_release_targets
from ai_workroot.release.model import ReleaseTargetRef


CANONICAL_SOURCE_TYPES = {
    "asset",
    "task",
    "work_action",
    "agent_run",
    "checkpoint",
    "handoff",
    "retrieval_card",
}


@dataclass(frozen=True)
class ReleaseFilterReport:
    protected_source_ids: frozenset[str]
    tombstone_source_ids: frozenset[str]
    dropped: tuple[tuple[str, str], ...]
    protected_candidate_ids: frozenset[str] = frozenset()
    tombstone_candidate_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class FtsReleaseFilterReport:
    matches: tuple[object, ...]
    dropped: tuple[tuple[str, str], ...]
    tombstones: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class RelationshipReleaseFilterReport:
    signals: tuple[object, ...]
    dropped: tuple[tuple[str, str], ...]
    tombstones: tuple[tuple[str, str], ...]


class CandidateReleaseTargetResolver:
    """Resolve recall candidates to canonical Release Control targets."""

    def __init__(self, conn: sqlite3.Connection, workroot_id: str):
        self.conn = conn
        self.workroot_id = workroot_id

    def resolve_candidate(self, candidate: object) -> tuple[ReleaseTargetRef, ...]:
        source_type = str(getattr(candidate, "source_type", "") or "")
        source_id = str(getattr(candidate, "source_id", "") or "")
        if not source_type or not source_id:
            return ()
        if source_type == "context_candidate":
            return self._resolve_context_candidate(source_id)
        if source_type == "context_recall_hint":
            return self._resolve_context_recall_hint(source_id)
        if source_type in CANONICAL_SOURCE_TYPES:
            return (self._target_ref(source_type, source_id),)
        if source_type in {"indexed_chunk", "fts_match"}:
            return self._resolve_indexed_chunk(source_id)
        if source_type == "relationship_edge":
            return self._resolve_relationship_edge(source_id)
        return (self._target_ref(source_type, source_id),)

    def resolve_fts_match(self, match: object) -> tuple[ReleaseTargetRef, ...]:
        chunk_id = str(getattr(match, "chunk_id", "") or "")
        if not chunk_id:
            return ()
        return self._resolve_indexed_chunk(chunk_id)

    def resolve_relationship_signal(self, signal: object) -> tuple[ReleaseTargetRef, ...]:
        refs = [self._target_ref("relationship_edge", str(getattr(signal, "edge_id", "") or ""))]
        refs.extend(self._resolve_relationship_node(str(getattr(signal, "from_node_id", "") or "")))
        refs.extend(self._resolve_relationship_node(str(getattr(signal, "to_node_id", "") or "")))
        return tuple(_dedupe_refs(ref for ref in refs if ref.target_id))

    def _resolve_context_candidate(self, candidate_id: str) -> tuple[ReleaseTargetRef, ...]:
        try:
            row = self.conn.execute(
                """
                SELECT source_type, source_id
                FROM context_candidates
                WHERE workroot_id = ? AND candidate_id = ?
                """,
                (self.workroot_id, candidate_id),
            ).fetchone()
        except sqlite3.OperationalError:
            return ()
        if not row:
            return ()
        proxy = _SourceProxy(str(row[0] or ""), str(row[1] or ""))
        return self.resolve_candidate(proxy)

    def _resolve_context_recall_hint(self, hint_id: str) -> tuple[ReleaseTargetRef, ...]:
        refs = [self._target_ref("context_recall_hint", hint_id)]
        try:
            row = self.conn.execute(
                """
                SELECT target_type, target_id
                FROM context_recall_hints
                WHERE workroot_id = ? AND hint_id = ?
                """,
                (self.workroot_id, hint_id),
            ).fetchone()
        except sqlite3.OperationalError:
            row = None
        if row:
            target_type = str(row[0] or "")
            target_id = str(row[1] or "")
            if target_type and target_id:
                refs.extend(self.resolve_candidate(_SourceProxy(target_type, target_id)))
        return tuple(_dedupe_refs(ref for ref in refs if ref.target_id))

    def _resolve_indexed_chunk(self, chunk_id: str) -> tuple[ReleaseTargetRef, ...]:
        try:
            row = self.conn.execute(
                """
                SELECT c.chunk_id, c.file_id, f.source_type, f.source_id, f.relative_path
                FROM indexed_chunks c
                JOIN indexed_files f ON f.file_id = c.file_id
                WHERE c.workroot_id = ? AND c.chunk_id = ?
                """,
                (self.workroot_id, chunk_id),
            ).fetchone()
        except sqlite3.OperationalError:
            return (self._target_ref("indexed_chunk", chunk_id),)
        if not row:
            return (self._target_ref("indexed_chunk", chunk_id),)
        _, file_id, source_type, source_id, relative_path = row
        refs = [
            self._target_ref("indexed_chunk", chunk_id),
            self._target_ref("indexed_file", str(file_id or "")),
        ]
        if source_type and source_id:
            refs.extend(self.resolve_candidate(_SourceProxy(str(source_type), str(source_id))))
        elif relative_path:
            refs.append(self._target_ref("asset", str(relative_path)))
        return tuple(_dedupe_refs(ref for ref in refs if ref.target_id))

    def _resolve_relationship_edge(self, edge_id: str) -> tuple[ReleaseTargetRef, ...]:
        try:
            row = self.conn.execute(
                """
                SELECT from_node_id, to_node_id
                FROM relationship_edges
                WHERE workroot_id = ? AND edge_id = ?
                """,
                (self.workroot_id, edge_id),
            ).fetchone()
        except sqlite3.OperationalError:
            return (self._target_ref("relationship_edge", edge_id),)
        refs = [self._target_ref("relationship_edge", edge_id)]
        if row:
            refs.extend(self._resolve_relationship_node(str(row[0] or "")))
            refs.extend(self._resolve_relationship_node(str(row[1] or "")))
        return tuple(_dedupe_refs(ref for ref in refs if ref.target_id))

    def _resolve_relationship_node(self, node_id: str) -> tuple[ReleaseTargetRef, ...]:
        if not node_id:
            return ()
        try:
            row = self.conn.execute(
                """
                SELECT node_type, target_type, target_id
                FROM relationship_nodes
                WHERE workroot_id = ? AND node_id = ?
                """,
                (self.workroot_id, node_id),
            ).fetchone()
        except sqlite3.OperationalError:
            row = None
        node_type = str(row[0] or "") if row else ""
        target_type = str(row[1] or "") if row else ""
        target_id = str(row[2] or "") if row else ""
        if target_type and target_id:
            return (self._target_ref(target_type, target_id),)
        if node_type in CANONICAL_SOURCE_TYPES:
            return (self._target_ref(node_type, node_id),)
        return (self._target_ref("relationship_node", node_id),)

    def _target_ref(self, target_type: str, target_id: str) -> ReleaseTargetRef:
        return ReleaseTargetRef(target_type=target_type, target_id=target_id, workroot_id=self.workroot_id)


@dataclass(frozen=True)
class _SourceProxy:
    source_type: str
    source_id: str


def load_release_filter_report(
    conn: sqlite3.Connection,
    workroot_id: str,
    candidates: list[object],
) -> ReleaseFilterReport:
    resolver = CandidateReleaseTargetResolver(conn, workroot_id)
    protected_source_ids: set[str] = set()
    tombstone_source_ids: set[str] = set()
    protected_candidate_ids: set[str] = set()
    tombstone_candidate_ids: set[str] = set()
    dropped: list[tuple[str, str]] = []

    for candidate in candidates:
        candidate_id = str(getattr(candidate, "candidate_id", "") or "")
        source_id = str(getattr(candidate, "source_id", "") or "")
        evaluation = evaluate_release_targets(conn, workroot_id, resolver.resolve_candidate(candidate))
        if evaluation.strictly_protected:
            if source_id:
                protected_source_ids.add(source_id)
            if candidate_id:
                protected_candidate_ids.add(candidate_id)
                dropped.append((candidate_id, evaluation.level))
        elif evaluation.tombstone:
            if source_id:
                tombstone_source_ids.add(source_id)
            if candidate_id:
                tombstone_candidate_ids.add(candidate_id)

    return ReleaseFilterReport(
        protected_source_ids=frozenset(protected_source_ids),
        tombstone_source_ids=frozenset(tombstone_source_ids),
        dropped=tuple(dropped),
        protected_candidate_ids=frozenset(protected_candidate_ids),
        tombstone_candidate_ids=frozenset(tombstone_candidate_ids),
    )


def filter_fts_matches_for_release(
    conn: sqlite3.Connection,
    workroot_id: str,
    matches: list[object],
) -> FtsReleaseFilterReport:
    resolver = CandidateReleaseTargetResolver(conn, workroot_id)
    kept: list[object] = []
    dropped: list[tuple[str, str]] = []
    tombstones: list[tuple[str, str]] = []
    for match in matches:
        chunk_id = str(getattr(match, "chunk_id", "") or "")
        evaluation = evaluate_release_targets(conn, workroot_id, resolver.resolve_fts_match(match))
        if evaluation.strictly_protected:
            dropped.append((chunk_id, evaluation.level))
            continue
        if evaluation.tombstone:
            tombstones.append((chunk_id, evaluation.level))
        kept.append(match)
    return FtsReleaseFilterReport(tuple(kept), tuple(dropped), tuple(tombstones))


def filter_relationship_signals_for_release(
    conn: sqlite3.Connection,
    workroot_id: str,
    signals: list[object],
) -> RelationshipReleaseFilterReport:
    resolver = CandidateReleaseTargetResolver(conn, workroot_id)
    kept: list[object] = []
    dropped: list[tuple[str, str]] = []
    tombstones: list[tuple[str, str]] = []
    for signal in signals:
        edge_id = str(getattr(signal, "edge_id", "") or "")
        evaluation = evaluate_release_targets(conn, workroot_id, resolver.resolve_relationship_signal(signal))
        if evaluation.strictly_protected:
            dropped.append((edge_id, evaluation.level))
            continue
        if evaluation.tombstone:
            tombstones.append((edge_id, evaluation.level))
        kept.append(signal)
    return RelationshipReleaseFilterReport(tuple(kept), tuple(dropped), tuple(tombstones))


def _dedupe_refs(refs: Iterable[ReleaseTargetRef]) -> list[ReleaseTargetRef]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ReleaseTargetRef] = []
    for ref in refs:
        key = (ref.target_type, ref.target_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(ref)
    return deduped
