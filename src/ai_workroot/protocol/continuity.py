"""Minimal task continuity package for protocol sync."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from ai_workroot.protocol.recovery import derive_run_recovery_state
from ai_workroot.state.environment import utc_now


@dataclass(frozen=True)
class ContinuityPackage:
    brief: str
    current_state: str
    next_action: str
    open_items: list[dict[str, str]]
    recent_done_items: list[dict[str, str]]
    refs: list[dict[str, str]]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "brief": self.brief,
            "summary": self.brief,
            "current_state": self.current_state,
            "next_action": self.next_action,
            "open_items": self.open_items,
            "recent_done_items": self.recent_done_items,
            "refs": self.refs,
            "warnings": self.warnings,
        }


def load_continuity_package(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: Optional[str],
) -> ContinuityPackage:
    if not task_id:
        return ContinuityPackage(
            brief="",
            current_state="",
            next_action="",
            open_items=[],
            recent_done_items=[],
            refs=[],
            warnings=[],
        )

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
    task = conn.execute(
        """
        SELECT task_id, title, status, task_kind, process_level
        FROM tasks
        WHERE workroot_id = ? AND task_id = ?
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
    if handoff is None:
        handoff = conn.execute(
            """
            SELECT handoff_id, body, title
            FROM handoffs
            WHERE workroot_id = ? AND task_id IS NULL
            ORDER BY created_at DESC, rowid DESC
            LIMIT 1
            """,
            (workroot_id,),
        ).fetchone()
    checkpoint = conn.execute(
        """
        SELECT checkpoint_id, current_status
        FROM work_checkpoints
        WHERE workroot_id = ? AND task_id = ?
        ORDER BY rowid DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    task_items = conn.execute(
        """
        SELECT item_id, title, status, result_summary
        FROM task_items
        WHERE workroot_id = ? AND task_id = ?
          AND status IN ('todo', 'doing', 'blocked')
        ORDER BY item_order ASC, updated_at DESC
        LIMIT 10
        """,
        (workroot_id, task_id),
    ).fetchall()
    done_items = conn.execute(
        """
        SELECT item_id, title, result_summary
        FROM task_items
        WHERE workroot_id = ? AND task_id = ? AND status = 'done'
        ORDER BY completed_at DESC, updated_at DESC
        LIMIT 5
        """,
        (workroot_id, task_id),
    ).fetchall()
    latest_run = conn.execute(
        """
        SELECT run_id, status, started_at
        FROM task_runs
        WHERE workroot_id = ? AND task_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()

    refs: list[dict[str, str]] = []
    warnings: list[str] = []
    open_items: list[dict[str, str]] = []
    recent_done_items: list[dict[str, str]] = []
    brief = ""
    current_state = ""
    next_action = ""
    if task:
        task_title = str(task[1] or "")
        brief = task_title
        refs.append(
            {
                "type": "task",
                "id": str(task[0]),
                "role": "active",
                "summary": task_title,
                "status": str(task[2] or ""),
                "task_kind": str(task[3] or ""),
                "process_level": str(task[4] or ""),
            }
        )
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
        current_state = str(handoff[1] or "")
        next_action = str(handoff[2] or "")
        handoff_summary = str(next_action or current_state or "")
        refs.append(
            {
                "type": "handoff",
                "id": str(handoff[0]),
                "role": "next_step",
                "summary": handoff_summary,
            }
        )
    if checkpoint:
        checkpoint_status = str(checkpoint[1] or "")
        if not current_state:
            current_state = checkpoint_status
        refs.append(
            {
                "type": "checkpoint",
                "id": str(checkpoint[0]),
                "role": "latest_checkpoint",
                "summary": checkpoint_status,
            }
        )
    if latest_run:
        run_status = str(latest_run[1] or "")
        has_summary = summary is not None
        has_handoff = handoff is not None
        if run_status == "completed" and not has_handoff:
            warnings.append("Previous run has no current handoff; continuity may be degraded.")
        recovery_state = derive_run_recovery_state(
            run_status=run_status,
            started_at=str(latest_run[2] or utc_now()),
            now=utc_now(),
            has_summary=has_summary,
            has_handoff=has_handoff,
        )
        if recovery_state == "stale_active_run":
            warnings.append("Previous active run appears stale; continue if this is still the same work.")
        if recovery_state == "old_incomplete_run":
            warnings.append("Previous incomplete run is old and should be treated as a low-confidence clue.")
    for item_id, title, _status, _result_summary in task_items:
        open_item = {"item_id": str(item_id), "title": str(title or ""), "status": str(_status or "")}
        open_items.append(open_item)
        refs.append(
            {
                "type": "task_item",
                "id": str(item_id),
                "role": "open",
                "summary": str(title or ""),
            }
        )
    for item_id, title, result_summary in done_items:
        summary_text = str(title or "")
        if result_summary:
            summary_text = f"{summary_text}: {result_summary}"
        recent_done_items.append(
            {
                "item_id": str(item_id),
                "title": str(title or ""),
                "result_summary": str(result_summary or ""),
            }
        )
        refs.append(
            {
                "type": "task_item",
                "id": str(item_id),
                "role": "recent_done",
                "summary": summary_text,
            }
        )
    return ContinuityPackage(
        brief=brief,
        current_state=current_state,
        next_action=next_action,
        open_items=open_items,
        recent_done_items=recent_done_items,
        refs=refs,
        warnings=warnings,
    )
