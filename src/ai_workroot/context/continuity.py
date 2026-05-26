"""Minimal task continuity package for protocol sync."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ContinuityPackage:
    brief: str
    refs: list[dict[str, str]]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {"brief": self.brief, "refs": self.refs, "warnings": self.warnings}


def load_continuity_package(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: Optional[str],
) -> ContinuityPackage:
    if not task_id:
        return ContinuityPackage(brief="", refs=[], warnings=[])

    summary = conn.execute(
        """
        SELECT summary_id, summary_text, status
        FROM task_summaries
        WHERE workroot_id = ? AND task_id = ?
        ORDER BY generated_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    handoff = conn.execute(
        """
        SELECT handoff_id, current_state, next_action
        FROM handoffs
        WHERE workroot_id = ? AND task_id = ? AND status = 'current'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()

    refs: list[dict[str, str]] = []
    brief = ""
    if summary:
        brief = str(summary[1] or "")
        refs.append(
            {
                "type": "task_summary",
                "id": str(summary[0]),
                "role": "primary",
                "summary": brief,
            }
        )
    if handoff:
        handoff_summary = str(handoff[2] or handoff[1] or "")
        refs.append(
            {
                "type": "handoff",
                "id": str(handoff[0]),
                "role": "next_step",
                "summary": handoff_summary,
            }
        )
    return ContinuityPackage(brief=brief, refs=refs, warnings=[])
