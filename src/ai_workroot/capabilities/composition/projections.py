"""P0 protocol event projections."""

from __future__ import annotations

import json
import hashlib
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ai_workroot.state.versions import bump_state_version, now_utc


TASK_LEASE_EVENTS = ["progress", "handoff", "state", "asset", "decision"]
TASK_ITEM_STATUSES = {"todo", "doing", "done", "blocked", "canceled"}
TASK_ITEM_TRANSITIONS = {
    "todo": {"doing", "done", "blocked", "canceled"},
    "doing": {"todo", "done", "blocked", "canceled"},
    "blocked": {"doing", "done", "canceled"},
    "done": set(),
    "canceled": set(),
}

TASK_TRANSITIONS = {
    "active": {"paused", "blocked", "closed", "archived", "released"},
    "paused": {"active", "closed", "archived", "released"},
    "blocked": {"active", "paused", "closed", "released"},
    "closed": {"archived", "released"},
    "archived": {"released"},
    "released": set(),
}
TASK_ROLES = {"inbox", "normal"}
TASK_PROCESS_LEVELS = {"L0", "L1", "L2", "L3"}
TASK_RETENTION_POLICIES = {"transient", "rolling_7d", "until_closed", "long_term"}
TASK_VISIBILITIES = {"implicit", "normal", "pinned"}


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


class ProjectionError(ValueError):
    def __init__(self, code: str, message: str = "", details: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message or code)
        self.code = code
        self.details = details or {}


def apply_projection(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
    user_directory: Optional[Path] = None,
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
    if kind == "asset":
        return project_asset(conn, workroot_id=workroot_id, lease=lease, event=event, user_directory=user_directory)
    if kind == "decision":
        return project_decision(conn, workroot_id=workroot_id, lease=lease, event=event)
    raise ProjectionError("event_not_allowed", f"projection not implemented for event kind: {kind}")


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
    if persistence not in {"normal", "temporary"}:
        raise ProjectionError("event_not_allowed", f"persistence is not implemented in P0: {persistence}")

    task_hint = _dict_value(payload, "task_hint")
    event_id = str(event["event_id"])
    occurred_at = str(event["occurred_at"])
    title = _text_or_none(task_hint.get("title")) or _text_or_none(payload.get("intent_text")) or "Workroot Task"
    goal = _text_or_none(payload.get("intent_text")) or title
    explicit_task_id = _text_or_none(task_hint.get("task_id"))
    parent_task_id = _text_or_none(task_hint.get("parent_task_id"))
    attached = _resolve_intent_attach_target(
        conn,
        workroot_id=workroot_id,
        lease=lease,
        explicit_task_id=explicit_task_id,
        parent_task_id=parent_task_id,
        title=title,
        goal=goal,
        persistence=persistence,
    )
    task_id = attached[0] if attached else explicit_task_id or _stable_id("task", event_id)
    root_task_id = parent_task_id or task_id
    run_id = attached[1] if attached and attached[1] else _stable_id("run", event_id)
    source = _dict_value(event, "source")
    agent_name = _text_or_none(source.get("actor_name")) or "agent"
    session_id = _text_or_none(source.get("session_id"))
    now = now_utc()
    if persistence == "temporary":
        task_kind = "inbox"
        process_level = "L0"
        role = "inbox"
        retention_policy = "rolling_7d"
        visibility = "implicit"
    else:
        task_kind = "task"
        process_level = "L1"
        role = "normal"
        retention_policy = "until_closed"
        visibility = "normal"

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
                task_kind,
                process_level,
                role,
                parent_task_id,
                root_task_id,
                retention_policy,
                visibility,
                occurred_at,
                now,
                json.dumps({"source_event_id": event_id}, sort_keys=True),
            ),
        )
        task_effect = "task_created"

    run_exists = _run_exists(conn, workroot_id, task_id, run_id)
    if run_exists:
        conn.execute(
            """
            UPDATE task_runs
            SET goal = COALESCE(NULLIF(goal, ''), ?),
                input_summary = COALESCE(NULLIF(input_summary, ''), ?),
                source_lease_id = COALESCE(NULLIF(source_lease_id, ''), ?)
            WHERE workroot_id = ? AND task_id = ? AND run_id = ?
            """,
            (
                goal,
                _text_or_none(payload.get("intent_text")),
                str(lease.get("lease_id") or ""),
                workroot_id,
                task_id,
                run_id,
            ),
        )
        run_effect = "task_run_attached"
    else:
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
        run_effect = "task_run_created"

    _bump_task_run_context(conn, workroot_id, task_id, run_id, include_workroot=True)
    return _continue_result(
        effects=[
            {"type": task_effect, "target_type": "task", "target_id": task_id},
            {"type": run_effect, "target_type": "task_run", "target_id": run_id},
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
    run_status = _text_or_none(payload.get("run_status")) or _text_or_none(payload.get("status"))
    if run_status not in {"active", "completed", "incomplete", None}:
        run_status = None
    now = now_utc()
    ended_at = now if run_status == "completed" else None

    conn.execute(
        """
        UPDATE task_runs
        SET output_summary = ?,
            status = COALESCE(?, status),
            ended_at = COALESCE(?, ended_at)
        WHERE workroot_id = ? AND task_id = ? AND run_id = ?
        """,
        (summary, run_status, ended_at, workroot_id, task_id, run_id),
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

    item_effects = _project_task_items(
        conn,
        workroot_id=workroot_id,
        task_id=task_id,
        run_id=run_id,
        event=event,
        now=now,
    )
    _bump_task_run_context(conn, workroot_id, task_id, run_id)
    if run_status == "completed":
        return ProjectionResult(
            effects=[
                {"type": "task_run_completed", "target_type": "task_run", "target_id": run_id},
                {"type": "task_summary_created", "target_type": "task_summary", "target_id": summary_id},
                *item_effects,
            ],
            directive_type="safe_to_stop",
            directive_goal="The current run has been completed.",
            directive_next_action="Stop safely or call sync before continuing.",
            lease_scope="task",
            task_id=task_id,
            run_id=run_id,
            allowed_events=[],
            required_before_stop=[],
        )
    if run_status == "incomplete":
        return _continue_result(
            effects=[
                {"type": "task_run_incomplete", "target_type": "task_run", "target_id": run_id},
                {"type": "task_summary_created", "target_type": "task_summary", "target_id": summary_id},
                *item_effects,
            ],
            task_id=task_id,
            run_id=run_id,
        )
    return _continue_result(
        effects=[
            {"type": "task_run_updated", "target_type": "task_run", "target_id": run_id},
            {"type": "task_summary_created", "target_type": "task_summary", "target_id": summary_id},
            *item_effects,
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
        raise ProjectionError("event_not_allowed", "P0 state projection only supports task targets")
    task_id = _required_text(payload, "target_id")
    lease_task_id = _text_or_none(lease.get("task_id"))
    if lease_task_id and lease_task_id != task_id:
        raise ProjectionError("state_conflict", "state event targets a different task than the lease")

    if _has_task_metadata_transition(payload):
        return _project_task_metadata_state(
            conn,
            workroot_id=workroot_id,
            task_id=task_id,
            run_id=_text_or_none(lease.get("run_id")),
            payload=payload,
        )

    from_status = _required_text(payload, "from_status")
    to_status = _required_text(payload, "to_status")

    row = conn.execute(
        """
        SELECT status, metadata_json
        FROM tasks
        WHERE workroot_id = ? AND task_id = ?
        """,
        (workroot_id, task_id),
    ).fetchone()
    if row is None:
        raise ProjectionError("projection_failed", f"task not found: {task_id}")
    current_status = str(row[0])
    if current_status != from_status:
        raise ProjectionError(
            "invalid_state_transition",
            f"current task status is {current_status}, not {from_status}",
            {"current_status": current_status},
        )
    if to_status not in TASK_TRANSITIONS.get(from_status, set()):
        raise ProjectionError("invalid_state_transition", f"cannot transition task from {from_status} to {to_status}")

    now = now_utc()
    closed_at = now if to_status == "closed" else None
    archived_at = now if to_status == "archived" else None
    metadata = _json_object(row[1])
    close_reason = _text_or_none(payload.get("close_reason"))
    if close_reason:
        metadata["close_reason"] = close_reason
    conn.execute(
        """
        UPDATE tasks
        SET status = ?,
            updated_at = ?,
            closed_at = COALESCE(?, closed_at),
            archived_at = COALESCE(?, archived_at),
            metadata_json = ?
        WHERE workroot_id = ? AND task_id = ?
        """,
        (
            to_status,
            now,
            closed_at,
            archived_at,
            json.dumps(metadata, ensure_ascii=False, sort_keys=True),
            workroot_id,
            task_id,
        ),
    )
    bump_state_version(conn, workroot_id, f"task:{task_id}", now)
    bump_state_version(conn, workroot_id, f"context:task:{task_id}", now)
    return _continue_result(
        effects=[{"type": "task_state_updated", "target_type": "task", "target_id": task_id}],
        task_id=task_id,
        run_id=_text_or_none(lease.get("run_id")),
    )


def project_asset(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
    user_directory: Optional[Path] = None,
) -> ProjectionResult:
    payload = event["payload"]
    task_id, run_id = _optional_task_run_from_payload_or_lease(payload, lease)
    if task_id and run_id:
        _require_matching_lease(lease, task_id=task_id, run_id=run_id)
        _require_run(conn, workroot_id, task_id, run_id)

    event_id = str(event["event_id"])
    title = _required_text(payload, "title")
    asset_kind = _text_or_none(payload.get("asset_kind")) or _text_or_none(payload.get("kind")) or "artifact"
    path = _required_text(payload, "path")
    normalized_path = _normalize_relative_path(path)
    if not normalized_path:
        raise ProjectionError("projection_failed", "invalid asset path")
    asset_id = (
        _text_or_none(payload.get("asset_id"))
        or _path_asset_id(workroot_id, normalized_path)
        or _stable_id("asset", event_id)
    )
    summary = _text_or_none(payload.get("summary")) or ""
    status = _text_or_none(payload.get("status")) or "current"
    now = now_utc()
    content_hash, indexed = _index_asset_file_if_text(
        conn,
        workroot_id=workroot_id,
        asset_id=asset_id,
        relative_path=normalized_path,
        user_directory=user_directory,
    )

    conn.execute(
        """
        INSERT INTO assets (
          asset_id, workroot_id, asset_type, title, lifecycle_status,
          publication_status, surface_id, current_path, content_hash, updatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          asset_type=excluded.asset_type,
          title=excluded.title,
          lifecycle_status=excluded.lifecycle_status,
          publication_status=excluded.publication_status,
          current_path=excluded.current_path,
          content_hash=excluded.content_hash,
          updatedAt=excluded.updatedAt
        """,
        (asset_id, workroot_id, asset_kind, title, status, "user_space", normalized_path, content_hash, now),
    )
    conn.execute(
        """
        INSERT INTO asset_path_history (history_id, asset_id, path, observedAt)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(history_id) DO UPDATE SET
          asset_id=excluded.asset_id,
          path=excluded.path,
          observedAt=excluded.observedAt
        """,
        (_stable_id("asset_path", event_id), asset_id, normalized_path, now),
    )
    conn.execute(
        """
        INSERT INTO asset_provenance (provenance_id, asset_id, source_ref)
        VALUES (?, ?, ?)
        ON CONFLICT(provenance_id) DO UPDATE SET
          asset_id=excluded.asset_id,
          source_ref=excluded.source_ref
        """,
        (_stable_id("asset_provenance", event_id), asset_id, f"protocol_event:{event_id}"),
    )
    _upsert_context_candidate(
        conn,
        workroot_id=workroot_id,
        candidate_id=f"asset:{asset_id}",
        source_type="asset",
        source_id=asset_id,
        title=title,
        summary=summary,
        domains=f"task:{task_id} asset:{asset_kind}" if task_id else f"workroot asset:{asset_kind}",
        importance="normal",
        context_policy="task-related",
        updated_at=now,
    )
    if task_id and run_id:
        _link_task_to_target(
            conn,
            workroot_id=workroot_id,
            task_id=task_id,
            target_type="asset",
            target_id=asset_id,
            target_title=title,
            relationship_type="produced_asset",
        )
        _bump_task_run_context(conn, workroot_id, task_id, run_id)
    else:
        bump_state_version(conn, workroot_id, "workroot", now)
    bump_state_version(conn, workroot_id, f"asset:{asset_id}", now)
    if indexed:
        bump_state_version(conn, workroot_id, "index:assets", now)
    effects = [{"type": "asset_recorded", "target_type": "asset", "target_id": asset_id}]
    if task_id:
        return _continue_result(effects=effects, task_id=task_id, run_id=run_id)
    return _workroot_capture_result(effects=effects)


def project_decision(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    task_id, run_id = _optional_task_run_from_payload_or_lease(payload, lease)
    if task_id and run_id:
        _require_matching_lease(lease, task_id=task_id, run_id=run_id)
        _require_run(conn, workroot_id, task_id, run_id)

    event_id = str(event["event_id"])
    decision_id = _text_or_none(payload.get("decision_id")) or _stable_id("decision", event_id)
    decision_text = _required_text(payload, "decision")
    title = _text_or_none(payload.get("title")) or decision_text[:80]
    reason = _text_or_none(payload.get("reason")) or ""
    scope = _text_or_none(payload.get("scope")) or "task"
    summary = decision_text if not reason else f"{decision_text}\nReason: {reason}"
    now = now_utc()

    _upsert_context_candidate(
        conn,
        workroot_id=workroot_id,
        candidate_id=f"decision:{decision_id}",
        source_type="decision",
        source_id=decision_id,
        title=title,
        summary=summary,
        domains=f"task:{task_id} scope:{scope}" if task_id else f"workroot scope:{scope}",
        importance="high",
        context_policy="task-related",
        updated_at=now,
    )
    if task_id and run_id:
        _link_task_to_target(
            conn,
            workroot_id=workroot_id,
            task_id=task_id,
            target_type="decision",
            target_id=decision_id,
            target_title=title,
            relationship_type="made_decision",
        )
        _bump_task_run_context(conn, workroot_id, task_id, run_id)
    else:
        bump_state_version(conn, workroot_id, "workroot", now)
    bump_state_version(conn, workroot_id, f"decision:{decision_id}", now)
    effects = [{"type": "decision_recorded", "target_type": "decision", "target_id": decision_id}]
    if task_id:
        return _continue_result(effects=effects, task_id=task_id, run_id=run_id)
    return _workroot_capture_result(effects=effects)


def _project_task_metadata_state(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    run_id: Optional[str],
    payload: dict[str, Any],
) -> ProjectionResult:
    row = conn.execute(
        """
        SELECT role, process_level, visibility, retention_policy, task_kind
        FROM tasks
        WHERE workroot_id = ? AND task_id = ?
        """,
        (workroot_id, task_id),
    ).fetchone()
    if row is None:
        raise ProjectionError("projection_failed", f"task not found: {task_id}")

    role = _validate_choice(_text_or_none(payload.get("to_role")) or str(row[0]), TASK_ROLES, "to_role")
    process_level = _validate_choice(
        _text_or_none(payload.get("to_process_level")) or str(row[1]),
        TASK_PROCESS_LEVELS,
        "to_process_level",
    )
    visibility = _validate_choice(
        _text_or_none(payload.get("to_visibility")) or str(row[2]),
        TASK_VISIBILITIES,
        "to_visibility",
    )
    retention_policy = _validate_choice(
        _text_or_none(payload.get("to_retention_policy")) or str(row[3]),
        TASK_RETENTION_POLICIES,
        "to_retention_policy",
    )
    task_kind = _text_or_none(payload.get("to_task_kind")) or ("task" if role == "normal" else str(row[4] or "inbox"))
    now = now_utc()
    conn.execute(
        """
        UPDATE tasks
        SET role = ?,
            process_level = ?,
            visibility = ?,
            retention_policy = ?,
            task_kind = ?,
            updated_at = ?
        WHERE workroot_id = ? AND task_id = ?
        """,
        (role, process_level, visibility, retention_policy, task_kind, now, workroot_id, task_id),
    )
    bump_state_version(conn, workroot_id, "workroot", now)
    bump_state_version(conn, workroot_id, f"task:{task_id}", now)
    bump_state_version(conn, workroot_id, f"context:task:{task_id}", now)
    effect_type = "task_promoted" if row[0] == "inbox" and role == "normal" else "task_metadata_updated"
    return _continue_result(
        effects=[{"type": effect_type, "target_type": "task", "target_id": task_id}],
        task_id=task_id,
        run_id=run_id,
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


def _workroot_capture_result(*, effects: list[dict[str, str]]) -> ProjectionResult:
    return ProjectionResult(
        effects=effects,
        directive_type="capture_workroot",
        directive_goal="Workroot-level durable fact was captured without a task owner.",
        directive_next_action="Continue user-visible work. Sync with clearer task focus before committing task progress.",
        lease_scope="workroot",
        task_id=None,
        run_id=None,
        allowed_events=[],
        required_before_stop=[],
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
    _touch_task_activity(conn, workroot_id, task_id, now)
    if include_workroot:
        bump_state_version(conn, workroot_id, "workroot", now)
    bump_state_version(conn, workroot_id, f"task:{task_id}", now)
    if run_id:
        bump_state_version(conn, workroot_id, f"run:{run_id}", now)
    bump_state_version(conn, workroot_id, f"context:task:{task_id}", now)


def _touch_task_activity(conn: sqlite3.Connection, workroot_id: str, task_id: str, updated_at: str) -> None:
    conn.execute(
        """
        UPDATE tasks
        SET updated_at = ?
        WHERE workroot_id = ? AND task_id = ?
        """,
        (updated_at, workroot_id, task_id),
    )


def _task_run_from_payload_or_lease(payload: dict[str, Any], lease: dict[str, Any]) -> tuple[str, str]:
    task_id = _text_or_none(payload.get("task_id")) or _text_or_none(lease.get("task_id"))
    run_id = _text_or_none(payload.get("run_id")) or _text_or_none(lease.get("run_id"))
    if not task_id:
        raise ProjectionError("projection_failed", "missing task_id")
    if not run_id:
        raise ProjectionError("projection_failed", "missing run_id")
    return task_id, run_id


def _optional_task_run_from_payload_or_lease(
    payload: dict[str, Any], lease: dict[str, Any]
) -> tuple[Optional[str], Optional[str]]:
    task_id = _text_or_none(payload.get("task_id")) or _text_or_none(lease.get("task_id"))
    run_id = _text_or_none(payload.get("run_id")) or _text_or_none(lease.get("run_id"))
    if task_id and not run_id:
        raise ProjectionError("projection_failed", "missing run_id")
    if run_id and not task_id:
        raise ProjectionError("projection_failed", "missing task_id")
    return task_id, run_id


def _require_matching_lease(lease: dict[str, Any], *, task_id: str, run_id: str) -> None:
    lease_task_id = _text_or_none(lease.get("task_id"))
    lease_run_id = _text_or_none(lease.get("run_id"))
    if lease_task_id and lease_task_id != task_id:
        raise ProjectionError("state_conflict", "event task_id does not match lease task_id")
    if lease_run_id and lease_run_id != run_id:
        raise ProjectionError("state_conflict", "event run_id does not match lease run_id")


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
        raise ProjectionError("projection_failed", f"task run not found: {run_id}")


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


def _run_exists(conn: sqlite3.Connection, workroot_id: str, task_id: str, run_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1
        FROM task_runs
        WHERE workroot_id = ? AND task_id = ? AND run_id = ?
        LIMIT 1
        """,
        (workroot_id, task_id, run_id),
    ).fetchone()
    return row is not None


def _resolve_intent_attach_target(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    explicit_task_id: Optional[str],
    parent_task_id: Optional[str],
    title: str,
    goal: str,
    persistence: str,
) -> Optional[tuple[str, Optional[str]]]:
    if persistence not in {"normal", "temporary"}:
        return None
    for task_id in (explicit_task_id, _text_or_none(lease.get("task_id")), parent_task_id):
        if task_id and _task_exists(conn, workroot_id, task_id):
            return task_id, _latest_usable_run_id(conn, workroot_id, task_id)

    candidates: list[tuple[int, str, Optional[str]]] = []
    query_text = f"{title} {goal}"
    for row in conn.execute(
        """
        SELECT t.task_id, t.title, COALESCE(s.summary_text, r.output_summary, ''), r.run_id, t.role
        FROM tasks t
        LEFT JOIN task_runs r ON r.workroot_id = t.workroot_id AND r.task_id = t.task_id
        LEFT JOIN task_summaries s ON s.workroot_id = t.workroot_id AND s.task_id = t.task_id AND s.status = 'current'
        WHERE t.workroot_id = ?
          AND COALESCE(t.status, 'active') IN ('active', 'paused', 'blocked')
        ORDER BY t.updated_at DESC, r.started_at DESC
        LIMIT 20
        """,
        (workroot_id,),
    ).fetchall():
        task_id = str(row[0])
        role = str(row[4] or "normal")
        if persistence == "temporary" and role != "inbox":
            continue
        if persistence == "normal" and role == "inbox":
            continue
        score = _intent_similarity_score(query_text, f"{row[1] or ''} {row[2] or ''}")
        if score >= 60:
            candidates.append(
                (score, task_id, _text_or_none(row[3]) or _latest_usable_run_id(conn, workroot_id, task_id))
            )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], item[2] or ""))
    if len(candidates) > 1 and candidates[0][0] - candidates[1][0] < 10:
        return None
    return candidates[0][1], candidates[0][2]


def _latest_usable_run_id(conn: sqlite3.Connection, workroot_id: str, task_id: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT run_id
        FROM task_runs
        WHERE workroot_id = ? AND task_id = ? AND status IN ('active', 'incomplete')
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (workroot_id, task_id),
    ).fetchone()
    return _text_or_none(row[0]) if row else None


def _intent_similarity_score(left: str, right: str) -> int:
    left_norm = _normalize_for_match(left)
    right_norm = _normalize_for_match(right)
    if not left_norm or not right_norm:
        return 0
    if left_norm == right_norm:
        return 100
    if left_norm in right_norm or right_norm in left_norm:
        return 90
    left_tokens = set(left_norm.split())
    right_tokens = set(right_norm.split())
    if not left_tokens or not right_tokens:
        return 0
    overlap = len(left_tokens & right_tokens)
    return int(100 * overlap / max(len(left_tokens), len(right_tokens)))


def _normalize_for_match(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]+", value.lower()))


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


def _project_task_items(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    run_id: str,
    event: dict[str, Any],
    now: str,
) -> list[dict[str, str]]:
    payload = event["payload"]
    effects: list[dict[str, str]] = []
    for index, item in enumerate(_list_of_dicts(payload.get("items_created")), start=1):
        status = _task_item_status(item.get("status"), default="todo")
        completed_at = now if status == "done" else None
        raw_title = _text_or_none(item.get("title"))
        if _is_empty_item_value(raw_title):
            continue
        title = raw_title or f"Task item {index}"
        explicit_item_id = _text_or_none(item.get("item_id"))
        existing_item_id = None if explicit_item_id else _find_task_item_by_title(conn, workroot_id, task_id, title)
        item_id = explicit_item_id or existing_item_id or _stable_id("item", f"{event['event_id']}-{index}")
        if existing_item_id:
            row = conn.execute(
                """
                SELECT status, completed_at
                FROM task_items
                WHERE workroot_id = ? AND task_id = ? AND item_id = ?
                """,
                (workroot_id, task_id, existing_item_id),
            ).fetchone()
            if row is not None:
                _require_task_item_transition(str(row[0]), status)
                completed_at = now if status == "done" and row[1] is None else row[1]
        conn.execute(
            """
            INSERT INTO task_items (
              item_id, workroot_id, task_id, run_id, title, status, item_order,
              detail, result_summary, source_event_id, created_at, updated_at,
              completed_at, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
              completed_at=excluded.completed_at,
              metadata_json=excluded.metadata_json
            """,
            (
                item_id,
                workroot_id,
                task_id,
                run_id,
                title,
                status,
                int(item.get("order") or item.get("item_order") or 0),
                _text_or_none(item.get("detail")),
                _text_or_none(item.get("result_summary")),
                str(event["event_id"]),
                now,
                now,
                completed_at,
                json.dumps({"source_event_id": event["event_id"]}, sort_keys=True),
            ),
        )
        effect_type = "task_item_updated" if existing_item_id else "task_item_created"
        effects.append({"type": effect_type, "target_type": "task_item", "target_id": item_id})

    for item in _list_of_dicts(payload.get("items_updated")):
        item_id = _text_or_none(item.get("item_id"))
        if not item_id:
            continue
        row = conn.execute(
            """
            SELECT title, status, item_order, detail, result_summary, completed_at
            FROM task_items
            WHERE workroot_id = ? AND task_id = ? AND item_id = ?
            """,
            (workroot_id, task_id, item_id),
        ).fetchone()
        if row is None:
            continue
        try:
            status = _task_item_status(item.get("status"), default=str(row[1]))
        except ProjectionError as exc:
            if exc.code == "projection_failed":
                continue
            raise
        _require_task_item_transition(str(row[1]), status)
        completed_at = now if status == "done" and row[5] is None else row[5]
        conn.execute(
            """
            UPDATE task_items
            SET title = ?,
                status = ?,
                item_order = ?,
                detail = ?,
                result_summary = ?,
                source_event_id = ?,
                updated_at = ?,
                completed_at = ?
            WHERE workroot_id = ? AND task_id = ? AND item_id = ?
            """,
            (
                _clean_item_title(item.get("title")) or str(row[0]),
                status,
                int(item.get("order") or item.get("item_order") or row[2] or 0),
                _text_or_none(item.get("detail")) if "detail" in item else row[3],
                _text_or_none(item.get("result_summary")) if "result_summary" in item else row[4],
                str(event["event_id"]),
                now,
                completed_at,
                workroot_id,
                task_id,
                item_id,
            ),
        )
        effects.append({"type": "task_item_updated", "target_type": "task_item", "target_id": item_id})
    return effects


def _find_task_item_by_title(
    conn: sqlite3.Connection,
    workroot_id: str,
    task_id: str,
    title: str,
) -> Optional[str]:
    normalized = _normalize_for_match(title)
    if not normalized:
        return None
    for row in conn.execute(
        """
        SELECT item_id, title
        FROM task_items
        WHERE workroot_id = ? AND task_id = ?
        ORDER BY updated_at DESC
        LIMIT 50
        """,
        (workroot_id, task_id),
    ).fetchall():
        if _normalize_for_match(str(row[1] or "")) == normalized:
            return str(row[0])
    return None


def _upsert_context_candidate(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    candidate_id: str,
    source_type: str,
    source_id: str,
    title: str,
    summary: str,
    domains: str,
    importance: str,
    context_policy: str,
    updated_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO context_candidates (
          candidate_id, workroot_id, source_type, source_id, title, summary,
          domains, importance, confidence, status, context_policy, safety_policy,
          token_estimate, updatedAt, lastUsedAt, use_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '', 0)
        ON CONFLICT(candidate_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          source_type=excluded.source_type,
          source_id=excluded.source_id,
          title=excluded.title,
          summary=excluded.summary,
          domains=excluded.domains,
          importance=excluded.importance,
          confidence=excluded.confidence,
          status=excluded.status,
          context_policy=excluded.context_policy,
          safety_policy=excluded.safety_policy,
          token_estimate=excluded.token_estimate,
          updatedAt=excluded.updatedAt
        """,
        (
            candidate_id,
            workroot_id,
            source_type,
            source_id,
            title,
            summary,
            domains,
            importance,
            0.8,
            "active",
            context_policy,
            "",
            max(40, len(summary) // 4),
            updated_at,
        ),
    )
    conn.execute("DELETE FROM context_candidates_fts WHERE candidate_id = ?", (candidate_id,))
    conn.execute(
        "INSERT INTO context_candidates_fts (candidate_id, title, summary, domains) VALUES (?, ?, ?, ?)",
        (candidate_id, title, summary, domains),
    )


def _link_task_to_target(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    target_type: str,
    target_id: str,
    target_title: str,
    relationship_type: str,
) -> None:
    task_node_id = f"node-task-{task_id}"
    target_node_id = f"node-{target_type}-{target_id}"
    conn.execute(
        """
        INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          node_type=excluded.node_type,
          title=excluded.title,
          target_type=excluded.target_type,
          target_id=excluded.target_id
        """,
        (task_node_id, workroot_id, "task", task_id, "task", task_id),
    )
    conn.execute(
        """
        INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          node_type=excluded.node_type,
          title=excluded.title,
          target_type=excluded.target_type,
          target_id=excluded.target_id
        """,
        (target_node_id, workroot_id, target_type, target_title, target_type, target_id),
    )
    conn.execute(
        """
        INSERT INTO relationship_edges (
          edge_id, workroot_id, from_node_id, to_node_id, relationship_type, confidence, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(edge_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          from_node_id=excluded.from_node_id,
          to_node_id=excluded.to_node_id,
          relationship_type=excluded.relationship_type,
          confidence=excluded.confidence,
          status=excluded.status
        """,
        (
            f"edge-task-{task_id}-{target_type}-{target_id}",
            workroot_id,
            task_node_id,
            target_node_id,
            relationship_type,
            1.0,
            "active",
        ),
    )


def _path_asset_id(workroot_id: str, relative_path: str) -> Optional[str]:
    normalized = _normalize_relative_path(relative_path)
    if not normalized:
        return None
    digest = hashlib.sha256(f"{workroot_id}:{normalized}".encode("utf-8")).hexdigest()[:16]
    return f"asset-path-{digest}"


def _index_asset_file_if_text(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    asset_id: str,
    relative_path: str,
    user_directory: Optional[Path],
) -> tuple[Optional[str], bool]:
    normalized = _normalize_relative_path(relative_path)
    if not normalized:
        return None, False
    if user_directory is None:
        return None, False
    user_directory = user_directory.resolve()
    file_path = (user_directory / normalized).resolve()
    try:
        file_path.relative_to(user_directory)
    except ValueError:
        return None, False
    if not file_path.is_file():
        return None, False
    try:
        data = file_path.read_bytes()
    except OSError:
        return None, False
    if len(data) > 512_000 or b"\x00" in data:
        return hashlib.sha256(data).hexdigest(), False
    try:
        body = data.decode("utf-8")
    except UnicodeDecodeError:
        return hashlib.sha256(data).hexdigest(), False
    content_hash = hashlib.sha256(data).hexdigest()
    file_id = f"file-{hashlib.sha256(f'{workroot_id}:{normalized}'.encode('utf-8')).hexdigest()[:16]}"
    conn.execute(
        """
        INSERT INTO indexed_files (file_id, workroot_id, relative_path, source_type, source_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          relative_path=excluded.relative_path,
          source_type=excluded.source_type,
          source_id=excluded.source_id
        """,
        (file_id, workroot_id, normalized, "asset", asset_id),
    )
    existing_chunks = [
        str(row[0])
        for row in conn.execute("SELECT chunk_id FROM indexed_chunks WHERE file_id = ?", (file_id,)).fetchall()
    ]
    for chunk_id in existing_chunks:
        conn.execute("DELETE FROM indexed_chunks_fts WHERE chunk_id = ?", (chunk_id,))
    conn.execute("DELETE FROM indexed_chunks WHERE file_id = ?", (file_id,))
    chunks = _chunk_text(body)
    for index, chunk in enumerate(chunks):
        chunk_id = f"{file_id}:chunk:{index}"
        conn.execute(
            """
            INSERT INTO indexed_chunks (chunk_id, file_id, workroot_id, body)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chunk_id) DO UPDATE SET
              file_id=excluded.file_id,
              workroot_id=excluded.workroot_id,
              body=excluded.body
            """,
            (chunk_id, file_id, workroot_id, chunk),
        )
        conn.execute("INSERT INTO indexed_chunks_fts (chunk_id, body) VALUES (?, ?)", (chunk_id, chunk))
    return content_hash, bool(chunks)


def _chunk_text(body: str, *, max_chars: int = 4000) -> list[str]:
    text = body.strip()
    if not text:
        return []
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]


def _normalize_relative_path(value: str) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    if not raw or raw.startswith("/") or raw == ".":
        return ""
    parts = [part for part in raw.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _task_item_status(value: Any, *, default: str) -> str:
    status = _text_or_none(value) or default
    if status not in TASK_ITEM_STATUSES:
        raise ProjectionError("projection_failed", f"invalid task item status: {status}")
    return status


def _require_task_item_transition(from_status: str, to_status: str) -> None:
    if from_status == to_status:
        return
    if to_status not in TASK_ITEM_TRANSITIONS.get(from_status, set()):
        raise ProjectionError(
            "invalid_state_transition",
            f"cannot transition task item from {from_status} to {to_status}",
            {"current_status": from_status, "requested_status": to_status},
        )


def _has_task_metadata_transition(payload: dict[str, Any]) -> bool:
    return any(
        key in payload
        for key in ("to_role", "to_process_level", "to_visibility", "to_retention_policy", "to_task_kind")
    )


def _validate_choice(value: str, allowed: set[str], field_name: str) -> str:
    if value not in allowed:
        raise ProjectionError("projection_failed", f"invalid {field_name}: {value}")
    return value


def _dict_value(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        return {}
    return value


def _json_object(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _required_text(data: dict[str, Any], key: str) -> str:
    value = _text_or_none(data.get(key))
    if not value:
        raise ProjectionError("projection_failed", f"missing {key}")
    return value


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_item_title(value: Any) -> Optional[str]:
    text = _text_or_none(value)
    if _is_empty_item_value(text):
        return None
    return text


def _is_empty_item_value(value: Optional[str]) -> bool:
    if value is None:
        return False
    marker = value.lower().strip(" .:-_")
    return marker in {"n/a", "na", "nil", "none", "nothing", "not applicable"}


def _stable_id(prefix: str, event_id: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in event_id)
    return f"{prefix}-{cleaned}"
