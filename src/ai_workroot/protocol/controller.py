"""Workroot Agent Protocol controller."""

from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any, Optional
import uuid

from ai_workroot.protocol.directives import directive
from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.events import canonical_json, request_hash
from ai_workroot.protocol.lease import create_lease, load_lease, now_utc, validate_lease
from ai_workroot.protocol.model import CommitRequest, SyncRequest
from ai_workroot.protocol.projections import ProjectionResult, apply_projection
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.registry import find_workroot_by_cwd, list_workroots
from ai_workroot.state.sqlite import initialize_workroot_sqlite


def sync(request_data: dict[str, Any]) -> dict[str, Any]:
    request = SyncRequest.from_dict(request_data)
    workroot = _resolve_workroot(request)
    state_directory = Path(workroot["stateDirectory"])
    sqlite_path = workroot_sqlite_path(state_directory)
    initialize_workroot_sqlite(sqlite_path)

    with sqlite3.connect(sqlite_path) as conn:
        current_task_id = str((request.known_state or {}).get("task_id") or "")
        if request.reason == "continue" and current_task_id:
            directive_payload = directive(
                "continue_task",
                goal="Continue the current Workroot task.",
                next_action="Continue the task and commit progress or handoff when a checkpoint is reached.",
                expected_events=["progress", "handoff", "state"],
                required_before_stop=["handoff"],
            )
            scope = "task"
            task_id = current_task_id
            run_id = (request.known_state or {}).get("run_id")
        elif request.query.strip():
            directive_payload = directive(
                "commit_required",
                goal="Persist the user's intent before creating task facts.",
                next_action="Call commit with an intent event if this work should be tracked.",
                expected_events=["intent"],
            )
            scope = "workroot"
            task_id = None
            run_id = None
        else:
            directive_payload = directive(
                "no_persistent_work",
                goal=None,
                next_action="Answer directly without creating persistent Workroot facts.",
                expected_events=[],
            )
            scope = "workroot"
            task_id = None
            run_id = None

        lease = create_lease(
            conn,
            workroot_id=workroot["workrootId"],
            scope=scope,
            task_id=task_id,
            run_id=str(run_id) if run_id else None,
            allowed_events=list(directive_payload["expected_events"]),
            required_before_stop=list(directive_payload["required_before_stop"]),
        )

    return _sync_response(workroot, directive_payload, lease, context={"brief": "", "refs": [], "warnings": []})


def commit(request_data: dict[str, Any]) -> dict[str, Any]:
    request = CommitRequest.from_dict(request_data)
    located = _locate_workroot_by_lease(request.exchange_lease_id)
    if located is None:
        return _error_response("lease_not_found")
    workroot, sqlite_path = located
    request_digest = request_hash(request_data)
    with sqlite3.connect(sqlite_path) as conn:
        existing = _load_existing_batch(conn, workroot["workrootId"], request.idempotency_key)
        if existing and existing["request_hash"] == request_digest:
            return json.loads(existing["response_json"])
        if existing and existing["request_hash"] != request_digest:
            return _error_response("idempotency_key_conflict")

        validation = validate_lease(conn, request.exchange_lease_id, events=request.events)
        if not validation.ok:
            return {
                "ok": False,
                "error": validation.error,
                "directive": validation.directive,
                "warnings": [],
            }
        lease = validation.lease or {}
        received_at = now_utc()
        batch_id = f"batch-{uuid.uuid4().hex}"
        conn.execute("BEGIN")
        try:
            conn.execute(
                """
                INSERT INTO protocol_commit_batches (
                  batch_id, workroot_id, request_id, idempotency_key, request_hash,
                  response_json, status, received_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, NULL, ?, ?, NULL)
                """,
                (
                    batch_id,
                    workroot["workrootId"],
                    request.request_id,
                    request.idempotency_key,
                    request_digest,
                    "started",
                    received_at,
                ),
            )
            event_results = []
            all_effects = []
            projection_result: Optional[ProjectionResult] = None
            for event in request.events:
                _append_protocol_event(
                    conn,
                    batch_id=batch_id,
                    workroot_id=workroot["workrootId"],
                    lease_id=request.exchange_lease_id,
                    request_id=request.request_id,
                    idempotency_key=request.idempotency_key,
                    event=event,
                    received_at=received_at,
                )
                projection_result = apply_projection(
                    conn,
                    workroot_id=workroot["workrootId"],
                    lease=lease,
                    event=event,
                )
                _append_event_effects(conn, event_id=event["event_id"], effects=projection_result.effects)
                all_effects.extend(projection_result.effects)
                event_results.append(
                    {"event_id": event["event_id"], "status": "applied", "effects": projection_result.effects}
                )
            next_scope = projection_result.lease_scope if projection_result else str(lease.get("scope") or "workroot")
            next_task_id = projection_result.task_id if projection_result else lease.get("task_id")
            next_run_id = projection_result.run_id if projection_result else lease.get("run_id")
            next_allowed_events = (
                projection_result.allowed_events if projection_result else list(lease.get("allowed_events") or [])
            )
            next_required_before_stop = (
                projection_result.required_before_stop
                if projection_result
                else list(lease.get("required_before_stop") or [])
            )
            next_directive = directive(
                projection_result.directive_type if projection_result else "continue_task",
                goal=projection_result.directive_goal if projection_result else "Continue the current Workroot exchange.",
                next_action=(
                    projection_result.directive_next_action
                    if projection_result
                    else "Commit progress or handoff when a checkpoint is reached."
                ),
                expected_events=list(next_allowed_events),
                required_before_stop=list(next_required_before_stop),
            )
            next_lease = create_lease(
                conn,
                workroot_id=workroot["workrootId"],
                scope=str(next_scope),
                task_id=str(next_task_id) if next_task_id else None,
                run_id=str(next_run_id) if next_run_id else None,
                allowed_events=list(next_allowed_events),
                required_before_stop=list(next_required_before_stop),
            )
            response = {
                "ok": True,
                "accepted": True,
                "event_results": event_results,
                "effects": all_effects,
                "state_vector": next_lease["observed_versions"],
                "directive": next_directive,
                "lease": next_lease,
                "contract": {
                    "contract_id": f"contract-{next_lease['lease_id']}",
                    "lease": next_lease,
                    "allowed_events": next_lease["allowed_events"],
                    "required_before_stop": next_lease["required_before_stop"],
                },
                "warnings": [],
            }
            conn.execute(
                """
                UPDATE protocol_commit_batches
                SET response_json = ?, status = ?, completed_at = ?
                WHERE batch_id = ?
                """,
                (json.dumps(response, ensure_ascii=False, sort_keys=True), "completed", now_utc(), batch_id),
            )
        except ProtocolError as exc:
            conn.rollback()
            return _error_response(exc.code, details=exc.details)
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
    return response


def _resolve_workroot(request: SyncRequest) -> dict[str, str]:
    if request.workroot_id:
        for record in list_workroots():
            if record["workrootId"] == request.workroot_id:
                return record
        raise ValueError(f"Workroot not found: {request.workroot_id}")
    if request.cwd:
        return find_workroot_by_cwd(Path(request.cwd))
    raise ValueError("missing Workroot locator")


def _locate_workroot_by_lease(lease_id: str) -> tuple[dict[str, str], Path] | None:
    for record in list_workroots():
        sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
        initialize_workroot_sqlite(sqlite_path)
        with sqlite3.connect(sqlite_path) as conn:
            if load_lease(conn, lease_id) is not None:
                return record, sqlite_path
    return None


def _load_existing_batch(
    conn: sqlite3.Connection, workroot_id: str, idempotency_key: str
) -> dict[str, str] | None:
    row = conn.execute(
        """
        SELECT request_hash, response_json, status
        FROM protocol_commit_batches
        WHERE workroot_id = ? AND idempotency_key = ?
        """,
        (workroot_id, idempotency_key),
    ).fetchone()
    if row is None:
        return None
    return {"request_hash": row[0], "response_json": row[1], "status": row[2]}


def _append_protocol_event(
    conn: sqlite3.Connection,
    *,
    batch_id: str,
    workroot_id: str,
    lease_id: str,
    request_id: str,
    idempotency_key: str,
    event: dict[str, Any],
    received_at: str,
) -> None:
    conn.execute(
        """
        INSERT INTO protocol_events (
          event_id, batch_id, workroot_id, request_id, lease_id, idempotency_key,
          kind, schema_version, payload_json, evidence_json, confirmation_json,
          source_json, occurred_at, received_at, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            batch_id,
            workroot_id,
            request_id,
            lease_id,
            idempotency_key,
            event["kind"],
            event["schema_version"],
            canonical_json(event["payload"]),
            canonical_json(event["evidence"]),
            canonical_json(event["confirmation"]),
            canonical_json(event["source"]),
            event["occurred_at"],
            received_at,
            "accepted",
        ),
    )


def _append_event_effects(
    conn: sqlite3.Connection,
    *,
    event_id: str,
    effects: list[dict[str, str]],
) -> None:
    created_at = now_utc()
    for index, effect in enumerate(effects, start=1):
        conn.execute(
            """
            INSERT INTO protocol_event_effects (
              effect_id, event_id, effect_type, target_type, target_id, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                f"effect-{event_id}-{index}",
                event_id,
                effect["type"],
                effect["target_type"],
                effect["target_id"],
                created_at,
            ),
        )


def _error_response(code: str, *, details: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": code, "details": details or {}},
        "directive": directive("resync_required", next_action="Call sync and retry if still relevant."),
        "warnings": [],
    }


def _sync_response(
    workroot: dict[str, str],
    directive_payload: dict[str, Any],
    lease: dict[str, Any],
    *,
    context: dict[str, Any],
) -> dict[str, Any]:
    contract = {
        "contract_id": f"contract-{lease['lease_id']}",
        "lease": lease,
        "allowed_events": lease["allowed_events"],
        "required_before_stop": lease["required_before_stop"],
        "resync_required_when": ["lease_expired", "state_conflict", "task_switch", "context_stale"],
    }
    return {
        "ok": True,
        "protocol": {
            "name": "workroot",
            "version": "v1",
            "min_agent_behavior": [
                "respect_directive",
                "commit_facts",
                "resync_on_conflict",
                "do_not_write_internal_state_directly",
            ],
        },
        "state": {
            "workroot_id": workroot["workrootId"],
            "focus": "active_task" if lease.get("task_id") else "workroot",
            "task_id": lease.get("task_id"),
            "run_id": lease.get("run_id"),
            "task_status": None,
            "summary_status": None,
        },
        "state_vector": lease["observed_versions"],
        "context": context,
        "directive": directive_payload,
        "lease": lease,
        "contract": contract,
        "recovery": {
            "on_commit_conflict": "resync_then_retry",
            "on_storage_unavailable": "return_user_result_and_save_handoff_when_available",
            "on_context_too_large": "use_summary_only",
        },
        "warnings": [],
    }
