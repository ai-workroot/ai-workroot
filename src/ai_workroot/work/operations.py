"""Active Work runtime services."""

from __future__ import annotations

import sqlite3
import time

from ai_workroot.state.sqlite import record_index_invalidation
from ai_workroot.work.model import (
    TASK_ITEM_STATUSES,
    AgentRun,
    InvalidationRecord,
    Task,
    TaskItem,
    WorkAction,
    WorkCheckpoint,
)


def create_task(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    title: str,
    status: str = "active",
    task_kind: str = "project",
    process_level: str = "L1",
) -> Task:
    task = Task(task_id=task_id, title=title, status=status, task_kind=task_kind, process_level=process_level)
    conn.execute(
        """
        INSERT INTO tasks (task_id, workroot_id, title, status, task_kind, process_level)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          title=excluded.title,
          status=excluded.status,
          task_kind=excluded.task_kind,
          process_level=excluded.process_level
        """,
        (task_id, workroot_id, title, status, task_kind, process_level),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="tasks",
        subject_type="task",
        subject_id=task_id,
        reason=f"task-changed:{task_id}",
    )
    conn.commit()
    return task


def record_agent_run(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    run_id: str,
    task_id: str,
    status: str,
    validity: str = "unknown",
) -> AgentRun:
    _ensure_task_exists(conn, workroot_id, task_id)
    conn.execute(
        """
        INSERT INTO agent_runs (run_id, task_id, workroot_id, status, validity)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
          task_id=excluded.task_id,
          workroot_id=excluded.workroot_id,
          status=excluded.status,
          validity=excluded.validity
        """,
        (run_id, task_id, workroot_id, status, validity),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="agent-runs",
        subject_type="agent-run",
        subject_id=run_id,
        reason=f"agent-run-changed:{run_id}",
    )
    conn.commit()
    return AgentRun(run_id=run_id, task_id=task_id, status=status, validity=validity)


def record_work_action(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    action_id: str,
    task_id: str,
    action_type: str,
    risk_level: str = "normal",
) -> WorkAction:
    _ensure_task_exists(conn, workroot_id, task_id)
    conn.execute(
        """
        INSERT INTO work_actions (action_id, task_id, workroot_id, action_type, risk_level)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(action_id) DO UPDATE SET
          task_id=excluded.task_id,
          workroot_id=excluded.workroot_id,
          action_type=excluded.action_type,
          risk_level=excluded.risk_level
        """,
        (action_id, task_id, workroot_id, action_type, risk_level),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="work-actions",
        subject_type="work-action",
        subject_id=action_id,
        reason=f"work-action-changed:{action_id}",
    )
    conn.commit()
    return WorkAction(action_id=action_id, task_id=task_id, action_type=action_type, risk_level=risk_level)


def create_checkpoint(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    checkpoint_id: str,
    task_id: str,
    current_status: str,
) -> WorkCheckpoint:
    _ensure_task_exists(conn, workroot_id, task_id)
    conn.execute(
        """
        INSERT INTO work_checkpoints (checkpoint_id, task_id, workroot_id, current_status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(checkpoint_id) DO UPDATE SET
          task_id=excluded.task_id,
          workroot_id=excluded.workroot_id,
          current_status=excluded.current_status
        """,
        (checkpoint_id, task_id, workroot_id, current_status),
    )
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="work-checkpoints",
        subject_type="checkpoint",
        subject_id=checkpoint_id,
        reason=f"checkpoint-changed:{checkpoint_id}",
    )
    conn.commit()
    return WorkCheckpoint(checkpoint_id=checkpoint_id, task_id=task_id, current_status=current_status)


def create_task_item(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    item_id: str,
    title: str,
    run_id: str = "",
    status: str = "todo",
    item_order: int = 0,
    detail: str = "",
    result_summary: str = "",
    source_event_id: str = "",
) -> TaskItem:
    _ensure_task_exists(conn, workroot_id, task_id)
    _validate_task_item_status(status)
    now = _now_utc()
    completed_at = now if status == "done" else None
    conn.execute(
        """
        INSERT INTO task_items (
          item_id, workroot_id, task_id, run_id, title, status, item_order,
          detail, result_summary, source_event_id, created_at, updated_at,
          completed_at, metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '{}')
        ON CONFLICT(item_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          task_id=excluded.task_id,
          run_id=excluded.run_id,
          title=excluded.title,
          status=excluded.status,
          item_order=excluded.item_order,
          detail=excluded.detail,
          result_summary=excluded.result_summary,
          source_event_id=excluded.source_event_id,
          updated_at=excluded.updated_at,
          completed_at=excluded.completed_at
        """,
        (
            item_id,
            workroot_id,
            task_id,
            run_id,
            title,
            status,
            item_order,
            detail,
            result_summary,
            source_event_id,
            now,
            now,
            completed_at,
        ),
    )
    _record_task_item_invalidation(conn, workroot_id, item_id)
    conn.commit()
    return TaskItem(
        item_id=item_id,
        task_id=task_id,
        title=title,
        status=status,
        item_order=item_order,
        run_id=run_id,
        result_summary=result_summary,
    )


def update_task_item(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    item_id: str,
    title: str | None = None,
    status: str | None = None,
    item_order: int | None = None,
    detail: str | None = None,
    result_summary: str | None = None,
) -> TaskItem:
    _ensure_task_exists(conn, workroot_id, task_id)
    row = conn.execute(
        """
        SELECT title, status, item_order, run_id, result_summary
        FROM task_items
        WHERE workroot_id = ? AND task_id = ? AND item_id = ?
        """,
        (workroot_id, task_id, item_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"task item does not exist for Workroot {workroot_id}: {item_id}")

    next_title = title if title is not None else str(row[0])
    next_status = status if status is not None else str(row[1])
    _validate_task_item_status(next_status)
    next_order = item_order if item_order is not None else int(row[2])
    next_result = result_summary if result_summary is not None else str(row[4] or "")
    now = _now_utc()
    completed_at = now if next_status == "done" else None
    conn.execute(
        """
        UPDATE task_items
        SET title = ?,
            status = ?,
            item_order = ?,
            detail = COALESCE(?, detail),
            result_summary = ?,
            updated_at = ?,
            completed_at = COALESCE(?, completed_at)
        WHERE workroot_id = ? AND task_id = ? AND item_id = ?
        """,
        (
            next_title,
            next_status,
            next_order,
            detail,
            next_result,
            now,
            completed_at,
            workroot_id,
            task_id,
            item_id,
        ),
    )
    _record_task_item_invalidation(conn, workroot_id, item_id)
    conn.commit()
    return TaskItem(
        item_id=item_id,
        task_id=task_id,
        title=next_title,
        status=next_status,
        item_order=next_order,
        run_id=str(row[3] or ""),
        result_summary=next_result,
    )


def record_invalidation(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    invalidation_id: str,
    invalidated_claim: str,
    reason: str,
) -> InvalidationRecord:
    conn.execute(
        """
        INSERT INTO invalidation_records (invalidation_id, workroot_id, invalidated_claim, reason)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(invalidation_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          invalidated_claim=excluded.invalidated_claim,
          reason=excluded.reason
        """,
        (invalidation_id, workroot_id, invalidated_claim, reason),
    )
    conn.commit()
    return InvalidationRecord(invalidation_id=invalidation_id, invalidated_claim=invalidated_claim, reason=reason)


def _ensure_task_exists(conn: sqlite3.Connection, workroot_id: str, task_id: str) -> None:
    row = conn.execute(
        """
        SELECT 1
        FROM tasks
        WHERE workroot_id = ? AND task_id = ?
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    if row is None:
        raise ValueError(f"task does not exist for Workroot {workroot_id}: {task_id}")


def _validate_task_item_status(status: str) -> None:
    if status not in TASK_ITEM_STATUSES:
        raise ValueError(f"invalid task item status: {status}")


def _record_task_item_invalidation(conn: sqlite3.Connection, workroot_id: str, item_id: str) -> None:
    record_index_invalidation(
        conn,
        workroot_id=workroot_id,
        index_id="task-items",
        subject_type="task-item",
        subject_id=item_id,
        reason=f"task-item-changed:{item_id}",
    )


def _now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
