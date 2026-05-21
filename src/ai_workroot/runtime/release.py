"""Active Release Control authoring services."""

from __future__ import annotations

import sqlite3

from ai_workroot.core.release import DeletionRecord, Redaction, ReleaseRecord, ReleaseTargetRef, Tombstone
from ai_workroot.indexing.providers.release_provider import ReleaseEvaluation, evaluate_release_targets


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
