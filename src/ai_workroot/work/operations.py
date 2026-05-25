"""Active Work runtime services."""

from __future__ import annotations

import sqlite3

from ai_workroot.work.model import AgentRun, InvalidationRecord, Task, WorkAction, WorkCheckpoint
from ai_workroot.state.sqlite import record_index_invalidation


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


def create_handoff(conn: sqlite3.Connection, *, workroot_id: str, handoff_id: str, title: str) -> dict[str, str]:
    conn.execute(
        """
        INSERT INTO handoffs (handoff_id, workroot_id, title)
        VALUES (?, ?, ?)
        ON CONFLICT(handoff_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          title=excluded.title
        """,
        (handoff_id, workroot_id, title),
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
    return {"handoff_id": handoff_id, "workroot_id": workroot_id, "title": title}


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
