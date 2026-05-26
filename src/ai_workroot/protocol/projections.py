"""P0 protocol event projections."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any, Optional

from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.lease import bump_state_version, now_utc


TASK_LEASE_EVENTS = ["progress", "handoff", "state"]

TASK_TRANSITIONS = {
    "active": {"paused", "blocked", "closed", "released"},
    "paused": {"active", "blocked", "closed"},
    "blocked": {"active", "paused", "closed"},
    "released": {"closed", "archived"},
    "closed": {"archived"},
    "archived": set(),
}


@dataclass(frozen=True)
class ProjectionResult:
    effects: list[dict[str, str]]
    directive_type: str
    directive_goal: Optional[str]
    directive_next_action: Optional[str]
    lease_scope: str
    task_id: Optional[str]
    run_id: Optional[str]
    allowed_events: list[str]
    required_before_stop: list[str]


def apply_projection(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    kind = event["kind"]
    if kind == "intent":
        return project_intent(conn, workroot_id=workroot_id, lease=lease, event=event)
    if kind == "progress":
        return project_progress(conn, workroot_id=workroot_id, lease=lease, event=event)
    if kind == "handoff":
        return project_handoff(conn, workroot_id=workroot_id, lease=lease, event=event)
    if kind == "state":
        return project_state(conn, workroot_id=workroot_id, lease=lease, event=event)
    raise ProtocolError("event_not_allowed", f"projection not implemented for event kind: {kind}")


def project_intent(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    classification = _dict_value(payload, "classification")
    persistence = str(classification.get("persistence") or "")
    if persistence == "quick":
        bump_state_version(conn, workroot_id, "context")
        return ProjectionResult(
            effects=[],
            directive_type="no_persistent_work",
            directive_goal=None,
            directive_next_action="Answer directly without creating persistent Workroot facts.",
            lease_scope="workroot",
            task_id=None,
            run_id=None,
            allowed_events=[],
            required_before_stop=[],
        )
    if persistence != "normal":
        raise ProtocolError("event_not_allowed", f"persistence is not implemented in P0: {persistence}")

    task_hint = _dict_value(payload, "task_hint")
    event_id = str(event["event_id"])
    occurred_at = str(event["occurred_at"])
    task_id = _text_or_none(task_hint.get("task_id")) or _stable_id("task", event_id)
    parent_task_id = _text_or_none(task_hint.get("parent_task_id"))
    root_task_id = parent_task_id or task_id
    title = _text_or_none(task_hint.get("title")) or _text_or_none(payload.get("intent_text")) or "Workroot Task"
    goal = _text_or_none(payload.get("intent_text")) or title
    run_id = _stable_id("run", event_id)
    source = _dict_value(event, "source")
    agent_name = _text_or_none(source.get("actor_name")) or "agent"
    session_id = _text_or_none(source.get("session_id"))
    now = now_utc()

    task_exists = _task_exists(conn, workroot_id, task_id)
    if task_exists:
        conn.execute(
            """
            UPDATE tasks
            SET updated_at = ?, title = COALESCE(NULLIF(title, ''), ?)
            WHERE workroot_id = ? AND task_id = ?
            """,
            (now, title, workroot_id, task_id),
        )
        task_effect = "task_attached"
    else:
        conn.execute(
            """
            INSERT INTO tasks (
              task_id, workroot_id, title, status, task_kind, process_level, role,
              parent_task_id, root_task_id, retention_policy, visibility,
              created_at, updated_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                workroot_id,
                title,
                "active",
                "task",
                "L1",
                "normal",
                parent_task_id,
                root_task_id,
                "until_closed",
                "normal",
                occurred_at,
                now,
                json.dumps({"source_event_id": event_id}, sort_keys=True),
            ),
        )
        task_effect = "task_created"

    conn.execute(
        """
        INSERT INTO task_runs (
          run_id, task_id, workroot_id, agent_name, agent_instance_id, status,
          goal, input_summary, output_summary, detail_body_ref, source_lease_id,
          started_at, ended_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, NULL)
        """,
        (
            run_id,
            task_id,
            workroot_id,
            agent_name,
            session_id,
            "active",
            goal,
            _text_or_none(payload.get("intent_text")),
            str(lease.get("lease_id") or ""),
            occurred_at,
        ),
    )

    _bump_task_run_context(conn, workroot_id, task_id, run_id, include_workroot=True)
    return _continue_result(
        effects=[
            {"type": task_effect, "target_type": "task", "target_id": task_id},
            {"type": "task_run_created", "target_type": "task_run", "target_id": run_id},
        ],
        task_id=task_id,
        run_id=run_id,
    )


def project_progress(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    task_id, run_id = _task_run_from_payload_or_lease(payload, lease)
    _require_matching_lease(lease, task_id=task_id, run_id=run_id)
    _require_run(conn, workroot_id, task_id, run_id)
    summary = _text_or_none(payload.get("summary")) or ""
    now = now_utc()

    conn.execute(
        """
        UPDATE task_runs
        SET output_summary = ?
        WHERE workroot_id = ? AND task_id = ? AND run_id = ?
        """,
        (summary, workroot_id, task_id, run_id),
    )

    summary_id = _stable_id("summary", str(event["event_id"]))
    _supersede_current_summaries(conn, workroot_id, task_id, superseded_by=summary_id)
    conn.execute(
        """
        INSERT INTO task_summaries (
          summary_id, task_id, workroot_id, status, summary_text,
          open_questions_json, next_actions_json, source_refs_json,
          generated_by, generated_at, superseded_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            summary_id,
            task_id,
            workroot_id,
            "current",
            summary,
            json.dumps(payload.get("open_questions") or [], ensure_ascii=False, sort_keys=True),
            json.dumps([], ensure_ascii=False, sort_keys=True),
            json.dumps(payload.get("source_refs") or [], ensure_ascii=False, sort_keys=True),
            "agent",
            now,
        ),
    )
    conn.execute(
        """
        UPDATE tasks
        SET summary_id = ?, updated_at = ?
        WHERE workroot_id = ? AND task_id = ?
        """,
        (summary_id, now, workroot_id, task_id),
    )

    _bump_task_run_context(conn, workroot_id, task_id, run_id)
    return _continue_result(
        effects=[
            {"type": "task_run_updated", "target_type": "task_run", "target_id": run_id},
            {"type": "task_summary_created", "target_type": "task_summary", "target_id": summary_id},
        ],
        task_id=task_id,
        run_id=run_id,
    )


def project_handoff(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    task_id, run_id = _task_run_from_payload_or_lease(payload, lease)
    _require_matching_lease(lease, task_id=task_id, run_id=run_id)
    _require_run(conn, workroot_id, task_id, run_id)
    handoff_id = _stable_id("handoff", str(event["event_id"]))
    now = now_utc()

    conn.execute(
        """
        UPDATE handoffs
        SET status = 'superseded', superseded_by = ?
        WHERE workroot_id = ? AND task_id = ? AND status = 'current'
        """,
        (handoff_id, workroot_id, task_id),
    )
    current_state = _text_or_none(payload.get("current_state")) or ""
    next_action = _text_or_none(payload.get("next_action"))
    conn.execute(
        """
        INSERT INTO handoffs (
          handoff_id, workroot_id, title, target, body, task_id, run_id, status,
          current_state, next_action, open_items_json, open_questions_json,
          important_refs_json, source_refs_json, created_at, superseded_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            handoff_id,
            workroot_id,
            f"Handoff for {task_id}",
            "task",
            current_state,
            task_id,
            run_id,
            "current",
            current_state,
            next_action,
            json.dumps(payload.get("open_items") or [], ensure_ascii=False, sort_keys=True),
            json.dumps(payload.get("open_questions") or [], ensure_ascii=False, sort_keys=True),
            json.dumps(payload.get("important_refs") or [], ensure_ascii=False, sort_keys=True),
            json.dumps(payload.get("source_refs") or [], ensure_ascii=False, sort_keys=True),
            now,
        ),
    )
    if next_action:
        _update_current_summary_next_actions(conn, workroot_id, task_id, [next_action])

    _bump_task_run_context(conn, workroot_id, task_id, run_id)
    return ProjectionResult(
        effects=[{"type": "handoff_created", "target_type": "handoff", "target_id": handoff_id}],
        directive_type="safe_to_stop",
        directive_goal="The current checkpoint has been preserved.",
        directive_next_action="Stop safely or call sync before continuing.",
        lease_scope="task",
        task_id=task_id,
        run_id=run_id,
        allowed_events=[],
        required_before_stop=[],
    )


def project_state(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    if payload.get("target_type") != "task":
        raise ProtocolError("event_not_allowed", "P0 state projection only supports task targets")
    task_id = _required_text(payload, "target_id")
    from_status = _required_text(payload, "from_status")
    to_status = _required_text(payload, "to_status")
    lease_task_id = _text_or_none(lease.get("task_id"))
    if lease_task_id and lease_task_id != task_id:
        raise ProtocolError("state_conflict", "state event targets a different task than the lease")

    row = conn.execute(
        """
        SELECT status
        FROM tasks
        WHERE workroot_id = ? AND task_id = ?
        """,
        (workroot_id, task_id),
    ).fetchone()
    if row is None:
        raise ProtocolError("projection_failed", f"task not found: {task_id}")
    current_status = str(row[0])
    if current_status != from_status:
        raise ProtocolError(
            "invalid_state_transition",
            f"current task status is {current_status}, not {from_status}",
            {"current_status": current_status},
        )
    if to_status not in TASK_TRANSITIONS.get(from_status, set()):
        raise ProtocolError("invalid_state_transition", f"cannot transition task from {from_status} to {to_status}")

    now = now_utc()
    closed_at = now if to_status == "closed" else None
    archived_at = now if to_status == "archived" else None
    conn.execute(
        """
        UPDATE tasks
        SET status = ?, updated_at = ?, closed_at = COALESCE(?, closed_at), archived_at = COALESCE(?, archived_at)
        WHERE workroot_id = ? AND task_id = ?
        """,
        (to_status, now, closed_at, archived_at, workroot_id, task_id),
    )
    bump_state_version(conn, workroot_id, f"task:{task_id}", now)
    bump_state_version(conn, workroot_id, "context", now)
    return _continue_result(
        effects=[{"type": "task_state_updated", "target_type": "task", "target_id": task_id}],
        task_id=task_id,
        run_id=_text_or_none(lease.get("run_id")),
    )


def _continue_result(
    *,
    effects: list[dict[str, str]],
    task_id: str,
    run_id: Optional[str],
) -> ProjectionResult:
    return ProjectionResult(
        effects=effects,
        directive_type="continue_task",
        directive_goal="Continue the current Workroot task.",
        directive_next_action="Commit progress or handoff when a checkpoint is reached.",
        lease_scope="task",
        task_id=task_id,
        run_id=run_id,
        allowed_events=list(TASK_LEASE_EVENTS),
        required_before_stop=["handoff"],
    )


def _bump_task_run_context(
    conn: sqlite3.Connection,
    workroot_id: str,
    task_id: str,
    run_id: Optional[str],
    *,
    include_workroot: bool = False,
) -> None:
    now = now_utc()
    if include_workroot:
        bump_state_version(conn, workroot_id, "workroot", now)
    bump_state_version(conn, workroot_id, f"task:{task_id}", now)
    if run_id:
        bump_state_version(conn, workroot_id, f"run:{run_id}", now)
    bump_state_version(conn, workroot_id, "context", now)


def _task_run_from_payload_or_lease(payload: dict[str, Any], lease: dict[str, Any]) -> tuple[str, str]:
    task_id = _text_or_none(payload.get("task_id")) or _text_or_none(lease.get("task_id"))
    run_id = _text_or_none(payload.get("run_id")) or _text_or_none(lease.get("run_id"))
    if not task_id:
        raise ProtocolError("projection_failed", "missing task_id")
    if not run_id:
        raise ProtocolError("projection_failed", "missing run_id")
    return task_id, run_id


def _require_matching_lease(lease: dict[str, Any], *, task_id: str, run_id: str) -> None:
    lease_task_id = _text_or_none(lease.get("task_id"))
    lease_run_id = _text_or_none(lease.get("run_id"))
    if lease_task_id and lease_task_id != task_id:
        raise ProtocolError("state_conflict", "event task_id does not match lease task_id")
    if lease_run_id and lease_run_id != run_id:
        raise ProtocolError("state_conflict", "event run_id does not match lease run_id")


def _require_run(conn: sqlite3.Connection, workroot_id: str, task_id: str, run_id: str) -> None:
    row = conn.execute(
        """
        SELECT 1
        FROM task_runs
        WHERE workroot_id = ? AND task_id = ? AND run_id = ?
        LIMIT 1
        """,
        (workroot_id, task_id, run_id),
    ).fetchone()
    if row is None:
        raise ProtocolError("projection_failed", f"task run not found: {run_id}")


def _task_exists(conn: sqlite3.Connection, workroot_id: str, task_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM tasks
        WHERE workroot_id = ? AND task_id = ?
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    return row is not None


def _supersede_current_summaries(
    conn: sqlite3.Connection,
    workroot_id: str,
    task_id: str,
    *,
    superseded_by: str,
) -> None:
    conn.execute(
        """
        UPDATE task_summaries
        SET status = 'superseded', superseded_by = ?
        WHERE workroot_id = ? AND task_id = ? AND status = 'current'
        """,
        (superseded_by, workroot_id, task_id),
    )


def _update_current_summary_next_actions(
    conn: sqlite3.Connection,
    workroot_id: str,
    task_id: str,
    next_actions: list[str],
) -> None:
    conn.execute(
        """
        UPDATE task_summaries
        SET next_actions_json = ?
        WHERE workroot_id = ? AND task_id = ? AND status = 'current'
        """,
        (json.dumps(next_actions, ensure_ascii=False, sort_keys=True), workroot_id, task_id),
    )


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        return {}
    return value


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _text_or_none(data.get(key))
    if not value:
        raise ProtocolError("projection_failed", f"missing {key}")
    return value


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _stable_id(prefix: str, event_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in event_id)
    return f"{prefix}-{cleaned}"
