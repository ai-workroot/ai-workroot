"""Release Control read provider for recall protection."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3


@dataclass(frozen=True)
class ReleaseFilterReport:
    protected_source_ids: frozenset[str]
    tombstone_source_ids: frozenset[str]
    dropped: tuple[tuple[str, str], ...]


def load_release_filter_report(
    conn: sqlite3.Connection,
    workroot_id: str,
    candidates: list[object],
) -> ReleaseFilterReport:
    source_by_id = {str(getattr(candidate, "source_id")): str(getattr(candidate, "candidate_id")) for candidate in candidates}
    protected: set[str] = set()
    tombstones: set[str] = set()
    dropped: list[tuple[str, str]] = []

    redacted = _target_ids(conn, "redactions", "redaction_id", workroot_id)
    deleted = _target_ids(conn, "deletion_records", "deletion_id", workroot_id)
    tombstone_ids = _target_ids(conn, "tombstones", "tombstone_id", workroot_id)

    for source_id in redacted:
        if source_id in source_by_id:
            protected.add(source_id)
            dropped.append((source_by_id[source_id], "redacted"))
    for source_id in deleted:
        if source_id in source_by_id:
            protected.add(source_id)
            dropped.append((source_by_id[source_id], "deleted"))
    for source_id in tombstone_ids:
        if source_id in source_by_id:
            tombstones.add(source_id)

    return ReleaseFilterReport(
        protected_source_ids=frozenset(protected),
        tombstone_source_ids=frozenset(tombstones),
        dropped=tuple(dropped),
    )


def _target_ids(conn: sqlite3.Connection, table: str, id_column: str, workroot_id: str) -> set[str]:
    try:
        rows = conn.execute(
            f"SELECT target_id FROM {table} WHERE workroot_id = ? AND target_type = 'asset'",
            (workroot_id,),
        ).fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}
