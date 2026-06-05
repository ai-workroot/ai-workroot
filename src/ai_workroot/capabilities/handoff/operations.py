"""Handoff package authoring services."""

from __future__ import annotations

import sqlite3

from ai_workroot.capabilities.handoff.model import HandoffPackage
from ai_workroot.state.sqlite import record_index_invalidation


def create_handoff(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    handoff_id: str,
    title: str,
    target: str = "generic",
    body: str = "",
) -> HandoffPackage:
    conn.execute(
        """
        INSERT INTO handoffs (handoff_id, workroot_id, title, target, body)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(handoff_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          title=excluded.title,
          target=excluded.target,
          body=excluded.body
        """,
        (handoff_id, workroot_id, title, target, body),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="handoffs",
        subject_type="handoff",
        subject_id=handoff_id,
        reason=f"handoff-changed:{handoff_id}",
    )
    conn.commit()
    return HandoffPackage(
        handoff_id=handoff_id,
        workroot_id=workroot_id,
        title=title,
        target=target,
        body=body,
    )
