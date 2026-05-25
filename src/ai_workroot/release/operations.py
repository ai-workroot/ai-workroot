"""Active Release Control authoring services."""

from __future__ import annotations

import sqlite3

from ai_workroot.release.evaluation import ReleaseEvaluation, evaluate_release_targets
from ai_workroot.release.model import DeletionRecord, Redaction, ReleaseRecord, ReleaseTargetRef, Tombstone


STRICT_RELEASE_LEVELS = {"deleted", "redacted", "safety-sensitive"}


def create_release_record(
    conn: sqlite3.Connection,
    *,
    release_id: str,
    workroot_id: str,
    target: ReleaseTargetRef,
    release_level: str,
    recall_rule: str = "default",
) -> ReleaseRecord:
    _ensure_same_workroot(workroot_id, target)
    conn.execute(
        """
        INSERT INTO release_records (release_id, workroot_id, target_type, target_id, release_level, recall_rule)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(release_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          target_type=excluded.target_type,
          target_id=excluded.target_id,
          release_level=excluded.release_level,
          recall_rule=excluded.recall_rule
        """,
        (release_id, workroot_id, target.target_type, target.target_id, release_level, recall_rule),
    )
    if _normalize_release_level(release_level) in STRICT_RELEASE_LEVELS:
        sanitize_release_derived_indexes(
            conn,
            workroot_id=workroot_id,
            release_id=release_id,
            target=target,
            level=_normalize_release_level(release_level),
        )
    conn.commit()
    return ReleaseRecord(
        release_id=release_id,
        workroot_id=workroot_id,
        target_ref=target,
        release_level=release_level,
        recall_rule=recall_rule,
    )


def create_tombstone(
    conn: sqlite3.Connection,
    *,
    tombstone_id: str,
    workroot_id: str,
    target: ReleaseTargetRef,
    title: str,
    symbolic_note: str,
) -> Tombstone:
    _ensure_same_workroot(workroot_id, target)
    conn.execute(
        """
        INSERT INTO tombstones (tombstone_id, workroot_id, target_type, target_id, title, symbolic_note)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(tombstone_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          target_type=excluded.target_type,
          target_id=excluded.target_id,
          title=excluded.title,
          symbolic_note=excluded.symbolic_note
        """,
        (tombstone_id, workroot_id, target.target_type, target.target_id, title, symbolic_note),
    )
    conn.commit()
    return Tombstone(
        tombstone_id=tombstone_id,
        workroot_id=workroot_id,
        target_ref=target,
        title=title,
        symbolic_note=symbolic_note,
    )


def create_redaction(
    conn: sqlite3.Connection,
    *,
    redaction_id: str,
    workroot_id: str,
    target: ReleaseTargetRef,
    redacted_fields: tuple[str, ...],
    redaction_reason: str,
) -> Redaction:
    _ensure_same_workroot(workroot_id, target)
    conn.execute(
        """
        INSERT INTO redactions (redaction_id, workroot_id, target_type, target_id, redacted_fields, redaction_reason)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(redaction_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          target_type=excluded.target_type,
          target_id=excluded.target_id,
          redacted_fields=excluded.redacted_fields,
          redaction_reason=excluded.redaction_reason
        """,
        (redaction_id, workroot_id, target.target_type, target.target_id, ",".join(redacted_fields), redaction_reason),
    )
    sanitize_release_derived_indexes(
        conn,
        workroot_id=workroot_id,
        release_id=redaction_id,
        target=target,
        level="redacted",
    )
    conn.commit()
    return Redaction(
        redaction_id=redaction_id,
        workroot_id=workroot_id,
        target_ref=target,
        redacted_fields=redacted_fields,
        redaction_reason=redaction_reason,
    )


def create_deletion_record(
    conn: sqlite3.Connection,
    *,
    deletion_id: str,
    workroot_id: str,
    target: ReleaseTargetRef,
    minimum_audit_note: str,
) -> DeletionRecord:
    _ensure_same_workroot(workroot_id, target)
    conn.execute(
        """
        INSERT INTO deletion_records (deletion_id, workroot_id, target_type, target_id, minimum_audit_note)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(deletion_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          target_type=excluded.target_type,
          target_id=excluded.target_id,
          minimum_audit_note=excluded.minimum_audit_note
        """,
        (deletion_id, workroot_id, target.target_type, target.target_id, minimum_audit_note),
    )
    sanitize_release_derived_indexes(
        conn,
        workroot_id=workroot_id,
        release_id=deletion_id,
        target=target,
        level="deleted",
    )
    conn.commit()
    return DeletionRecord(
        deletion_id=deletion_id,
        workroot_id=workroot_id,
        target_ref=target,
        minimum_audit_note=minimum_audit_note,
    )


def resolve_release_state_for_target(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    target: ReleaseTargetRef,
) -> ReleaseEvaluation:
    _ensure_same_workroot(workroot_id, target)
    return evaluate_release_targets(conn, workroot_id, (target,))


def _ensure_same_workroot(workroot_id: str, target: ReleaseTargetRef) -> None:
    if target.workroot_id != workroot_id:
        raise ValueError(f"release target belongs to {target.workroot_id}, not {workroot_id}")


def sanitize_release_derived_indexes(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    release_id: str,
    target: ReleaseTargetRef,
    level: str,
) -> None:
    normalized = _normalize_release_level(level)
    if normalized not in STRICT_RELEASE_LEVELS:
        return
    placeholder = f"[{normalized}]" if normalized in {"deleted", "redacted"} else "[safety-sensitive]"
    _sanitize_context_candidates(conn, workroot_id, target, placeholder)
    _sanitize_indexed_chunks(conn, workroot_id, target, placeholder)
    _sanitize_context_recall_hints(conn, workroot_id, target, placeholder)
    _record_release_propagation(conn, release_id)
    _record_index_invalidations(conn, release_id, normalized)


def _sanitize_context_candidates(
    conn: sqlite3.Connection,
    workroot_id: str,
    target: ReleaseTargetRef,
    placeholder: str,
) -> None:
    candidate_ids = _rows_for_source(conn, "context_candidates", workroot_id, target)
    for candidate_id in candidate_ids:
        conn.execute(
            """
            UPDATE context_candidates
            SET title = ?, summary = ?
            WHERE workroot_id = ? AND candidate_id = ?
            """,
            (placeholder, placeholder, workroot_id, candidate_id),
        )
        conn.execute("DELETE FROM context_candidates_fts WHERE candidate_id = ?", (candidate_id,))
        conn.execute(
            "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, '')",
            (candidate_id, placeholder, placeholder),
        )


def _sanitize_indexed_chunks(
    conn: sqlite3.Connection,
    workroot_id: str,
    target: ReleaseTargetRef,
    placeholder: str,
) -> None:
    try:
        rows = conn.execute(
            """
            SELECT c.chunk_id
            FROM indexed_chunks c
            JOIN indexed_files f ON f.file_id = c.file_id
            WHERE c.workroot_id = ?
              AND f.workroot_id = ?
              AND f.source_type = ?
              AND f.source_id = ?
            """,
            (workroot_id, workroot_id, target.target_type, target.target_id),
        ).fetchall()
    except sqlite3.OperationalError:
        return
    for (chunk_id,) in rows:
        conn.execute(
            "UPDATE indexed_chunks SET body = ? WHERE workroot_id = ? AND chunk_id = ?",
            (placeholder, workroot_id, chunk_id),
        )
        conn.execute("DELETE FROM indexed_chunks_fts WHERE chunk_id = ?", (chunk_id,))
        conn.execute("INSERT INTO indexed_chunks_fts (chunk_id, body) VALUES (?, ?)", (chunk_id, placeholder))


def _sanitize_context_recall_hints(
    conn: sqlite3.Connection,
    workroot_id: str,
    target: ReleaseTargetRef,
    placeholder: str,
) -> None:
    hint_ids = set(_rows_for_source(conn, "context_recall_hints", workroot_id, target, id_column="hint_id"))
    if target.target_type == "context_recall_hint":
        hint_ids.add(target.target_id)
    for hint_id in hint_ids:
        conn.execute(
            """
            UPDATE context_recall_hints
            SET title = ?, summary = ?
            WHERE workroot_id = ? AND hint_id = ?
            """,
            (placeholder, placeholder, workroot_id, hint_id),
        )
        conn.execute("DELETE FROM context_recall_hints_fts WHERE hint_id = ?", (hint_id,))
        conn.execute(
            "INSERT INTO context_recall_hints_fts (hint_id, title, summary) VALUES (?, ?, ?)",
            (hint_id, placeholder, placeholder),
        )
        materialized_candidate_id = f"hint:{hint_id}"
        conn.execute(
            """
            UPDATE context_candidates
            SET title = ?, summary = ?
            WHERE workroot_id = ? AND candidate_id = ?
            """,
            (placeholder, placeholder, workroot_id, materialized_candidate_id),
        )
        conn.execute("DELETE FROM context_candidates_fts WHERE candidate_id = ?", (materialized_candidate_id,))
        conn.execute(
            "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, '')",
            (materialized_candidate_id, placeholder, placeholder),
        )


def _rows_for_source(
    conn: sqlite3.Connection,
    table: str,
    workroot_id: str,
    target: ReleaseTargetRef,
    *,
    id_column: str = "candidate_id",
) -> list[str]:
    try:
        rows = conn.execute(
            f"""
            SELECT {id_column}
            FROM {table}
            WHERE workroot_id = ? AND source_type = ? AND source_id = ?
            """,
            (workroot_id, target.target_type, target.target_id),
        ).fetchall()
    except sqlite3.OperationalError:
        try:
            rows = conn.execute(
                f"""
                SELECT {id_column}
                FROM {table}
                WHERE workroot_id = ? AND target_type = ? AND target_id = ?
                """,
                (workroot_id, target.target_type, target.target_id),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    return [str(row[0]) for row in rows]


def _record_release_propagation(conn: sqlite3.Connection, release_id: str) -> None:
    conn.execute(
        """
        INSERT INTO release_propagation_events (event_id, release_id, event_type)
        VALUES (?, ?, ?)
        ON CONFLICT(event_id) DO UPDATE SET
          release_id=excluded.release_id,
          event_type=excluded.event_type
        """,
        (f"relprop:{release_id}:derived-safety", release_id, "derived-index-sanitized"),
    )


def _record_index_invalidations(conn: sqlite3.Connection, release_id: str, level: str) -> None:
    for index_id, reason in (
        ("context-candidates", f"release-{level}:context-candidates"),
        ("indexed-chunks", f"release-{level}:indexed-chunks"),
        ("context-recall-hints", f"release-{level}:context-recall-hints"),
    ):
        conn.execute(
            """
            INSERT INTO index_invalidations (invalidation_id, index_id, reason)
            VALUES (?, ?, ?)
            ON CONFLICT(invalidation_id) DO UPDATE SET
              index_id=excluded.index_id,
              reason=excluded.reason
            """,
            (f"idxinv:{release_id}:{index_id}", index_id, reason),
        )


def _normalize_release_level(level: str) -> str:
    value = (level or "").strip().lower().replace("_", "-")
    if value in {"sensitive", "safety-sensitive"}:
        return "safety-sensitive"
    return value
