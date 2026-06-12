"""Workroot Agent Protocol controller."""

from __future__ import annotations

from pathlib import Path
import json
import sqlite3
from typing import Any, Optional
import uuid

from ai_workroot.capabilities.composition.configuration import compact_asset_output_rules
from ai_workroot.capabilities.composition.projections import ProjectionError, ProjectionResult, apply_projection
from ai_workroot.protocol.continuity import load_continuity_package
from ai_workroot.protocol.preservation import (
    EVENT_APPLIED,
    EVENT_QUARANTINED,
    hard_projection_error,
    minimally_identifiable,
    safe_event_for_storage,
)
from ai_workroot.protocol.directives import directive
from ai_workroot.protocol.errors import ProtocolError, protocol_error_response
from ai_workroot.protocol.events import canonical_json, request_hash, semantic_commit_hash, validate_event_envelope
from ai_workroot.protocol.focus import FocusResolution, resolve_sync_focus
from ai_workroot.protocol.lease import create_lease, decide_lease_safety
from ai_workroot.protocol.location import locate_for_commit
from ai_workroot.protocol.model import CommitRequest, SyncRequest
from ai_workroot.protocol.packet import build_private_packet, render_private_packet_markdown
from ai_workroot.protocol.response import (
    EVENT_KIND_TO_SHAPE,
    empty_workroot_contract,
    guidance_text,
    result_payload,
    semantic_response,
    workroot_contract_from_lease,
    workroot_view,
)
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.protocol_friction import record_locatable_protocol_friction, record_protocol_friction
from ai_workroot.state.registry import find_workroot_by_cwd, list_workroots
from ai_workroot.state.runtime_views import refresh_runtime_views
from ai_workroot.state.sqlite import initialize_workroot_sqlite
from ai_workroot.state.sync_trace import record_sync_packet_trace, sync_packet_trim_counts
from ai_workroot.state.versions import bump_state_version, now_utc


def sync(request_data: dict[str, Any], *, ai_workroot_home: Path | str | None = None) -> dict[str, Any]:
    return _sync(request_data, issue_lease=True, ai_workroot_home=ai_workroot_home)


def startup_context(request_data: dict[str, Any], *, ai_workroot_home: Path | str | None = None) -> dict[str, Any]:
    """Build a read-only sync-shaped response for startup context rendering."""

    response = _sync(request_data, issue_lease=False, ai_workroot_home=ai_workroot_home)
    contract = response.get("workroot_contract")
    if isinstance(contract, dict):
        contract["exchange_mode"] = "read_only"
    return response


def _sync(
    request_data: dict[str, Any],
    *,
    issue_lease: bool,
    ai_workroot_home: Path | str | None,
) -> dict[str, Any]:
    try:
        request = SyncRequest.from_dict(request_data)
    except (ProjectionError, ProtocolError) as exc:
        _record_validation_friction(
            request_data,
            action="sync",
            code=exc.code,
            details=exc.details,
            ai_workroot_home=ai_workroot_home,
        )
        return protocol_error_response(exc.code, details=exc.details)
    try:
        workroot = _resolve_workroot(request, ai_workroot_home=ai_workroot_home)
    except (OSError, ValueError):
        return _sync_unavailable_response("workroot_not_found")
    state_directory = Path(workroot["stateDirectory"])
    sqlite_path = workroot_sqlite_path(state_directory)
    initialize_workroot_sqlite(sqlite_path)

    with sqlite3.connect(sqlite_path) as conn:
        focus_resolution = resolve_sync_focus(conn, workroot_id=workroot["workrootId"], request=request)
        if focus_resolution.task_id:
            context = load_continuity_package(
                conn,
                workroot_id=workroot["workrootId"],
                task_id=focus_resolution.task_id,
            ).to_dict()
        else:
            context = {"brief": "", "refs": [], "warnings": []}
        directive_payload = directive(
            focus_resolution.directive_type,
            goal=focus_resolution.directive_goal,
            next_action=focus_resolution.directive_next_action,
            expected_events=list(focus_resolution.allowed_events),
            required_before_stop=list(focus_resolution.required_before_stop),
        )
        lease = None
        if issue_lease and focus_resolution.durable_commit_allowed and focus_resolution.allowed_events:
            lease = create_lease(
                conn,
                workroot_id=workroot["workrootId"],
                scope="task" if focus_resolution.task_id else "workroot",
                task_id=focus_resolution.task_id,
                run_id=focus_resolution.run_id,
                allowed_events=list(focus_resolution.allowed_events),
                required_before_stop=list(focus_resolution.required_before_stop),
                policy=focus_resolution.write_policy,
            )

    response = _sync_response(workroot, directive_payload, lease, context=context, focus_resolution=focus_resolution)
    _record_sync_packet_trace_best_effort(
        response=response,
        request=request,
        state_directory=state_directory,
        workroot_id=workroot["workrootId"],
        focus_resolution=focus_resolution,
    )
    return response


def commit(request_data: dict[str, Any], *, ai_workroot_home: Path | str | None = None) -> dict[str, Any]:
    try:
        request = CommitRequest.from_dict(request_data)
    except (ProjectionError, ProtocolError) as exc:
        _record_validation_friction(
            request_data,
            action="commit",
            code=exc.code,
            details=exc.details,
            ai_workroot_home=ai_workroot_home,
        )
        return protocol_error_response(exc.code, details=exc.details)
    if not request.atomic_batch:
        record_locatable_protocol_friction(
            cwd=request.cwd,
            workroot_id=request.workroot_id,
            ai_workroot_home=ai_workroot_home,
            action="commit",
            source_layer="protocol_controller",
            stage="validation",
            code="unsupported_atomic_batch_mode",
            result_status="rejected",
            request_id=request.request_id,
            lease_id=request.exchange_lease_id,
            idempotency_key=request.idempotency_key,
        )
        return protocol_error_response(
            "unsupported_atomic_batch_mode",
            next_action="Continue user-visible work. Sync before retrying with atomic_batch=true.",
            result_status="rejected",
        )
    located = locate_for_commit(
        lease_id=request.exchange_lease_id,
        cwd=request.cwd,
        workroot_id=request.workroot_id,
        ai_workroot_home=ai_workroot_home,
    )
    if not located.located:
        return _not_recorded_response(located.reason)
    workroot = located.record or {}
    sqlite_path = located.sqlite_path
    if sqlite_path is None:
        return _not_recorded_response("missing_sqlite_path")
    raw_request_hash = request_hash(request_data)
    semantic_hash, normalized_request_json = semantic_commit_hash(request_data, workroot_id=workroot["workrootId"])
    received_at = now_utc()
    batch_id = f"batch-{uuid.uuid4().hex}"
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = _load_existing_batch(conn, workroot["workrootId"], request.idempotency_key)
        if existing:
            if existing["semantic_hash"] == semantic_hash:
                if existing.get("response_json"):
                    response = json.loads(existing["response_json"])
                    conn.rollback()
                    return response
                response = _recovery_response("commit_batch_still_applying")
                record_protocol_friction(
                    state_directory=Path(workroot["stateDirectory"]),
                    workroot_id=workroot["workrootId"],
                    action="commit",
                    source_layer="protocol_controller",
                    stage="idempotency",
                    code="commit_batch_still_applying",
                    severity="info",
                    result_status="recovered",
                    request_id=request.request_id,
                    lease_id=request.exchange_lease_id,
                    idempotency_key=request.idempotency_key,
                )
                conn.rollback()
                return response
            response = protocol_error_response("idempotency_key_conflict", result_status="rejected")
            record_protocol_friction(
                state_directory=Path(workroot["stateDirectory"]),
                workroot_id=workroot["workrootId"],
                action="commit",
                source_layer="protocol_controller",
                stage="idempotency",
                code="idempotency_key_conflict",
                result_status="rejected",
                request_id=request.request_id,
                lease_id=request.exchange_lease_id,
                idempotency_key=request.idempotency_key,
            )
            conn.rollback()
            return response

        conn.execute(
            """
            INSERT INTO protocol_commit_batches (
              batch_id, workroot_id, request_id, idempotency_key, request_hash,
              semantic_hash, normalized_request_json, response_json, status,
              created_at, received_at, completed_at, error_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL, NULL)
            """,
            (
                batch_id,
                workroot["workrootId"],
                request.request_id,
                request.idempotency_key,
                raw_request_hash,
                semantic_hash,
                normalized_request_json,
                "applying",
                received_at,
                received_at,
            ),
        )

        response = _apply_commit_batch(
            conn,
            request=request,
            workroot_id=workroot["workrootId"],
            state_directory=Path(workroot["stateDirectory"]),
            user_directory=_user_directory_from_record(workroot),
            batch_id=batch_id,
            received_at=received_at,
        )
        _store_terminal_batch_response(conn, batch_id=batch_id, response=response, completed_at=now_utc())
        conn.commit()
        _refresh_runtime_views_best_effort(
            state_directory=Path(workroot["stateDirectory"]),
            sqlite_path=sqlite_path,
            workroot_id=workroot["workrootId"],
        )
        return response
    except Exception as exc:
        conn.rollback()
        return _unexpected_commit_response(
            exc,
            state_directory=Path(workroot["stateDirectory"]),
            recorded=False,
        )
    finally:
        conn.close()


def _record_validation_friction(
    request_data: dict[str, Any],
    *,
    action: str,
    code: str,
    details: dict[str, Any],
    ai_workroot_home: Path | str | None,
) -> None:
    record_locatable_protocol_friction(
        cwd=request_data.get("cwd") if isinstance(request_data.get("cwd"), str) else None,
        workroot_id=request_data.get("workroot_id") if isinstance(request_data.get("workroot_id"), str) else None,
        ai_workroot_home=ai_workroot_home,
        action=action,
        source_layer="protocol_controller",
        stage="validation",
        code=f"{action}_validation_error",
        result_status="rejected",
        request_id=str(request_data.get("request_id") or ""),
        lease_id=str(request_data.get("exchange_lease_id") or ""),
        idempotency_key=str(request_data.get("idempotency_key") or ""),
        details={"code": code, **details},
    )


def _refresh_runtime_views_best_effort(*, state_directory: Path, sqlite_path: Path, workroot_id: str) -> None:
    try:
        refresh_runtime_views(
            state_directory=state_directory,
            sqlite_path=sqlite_path,
            workroot_id=workroot_id,
        )
    except Exception:
        return


def _record_sync_packet_trace_best_effort(
    *,
    response: dict[str, Any],
    request: SyncRequest,
    state_directory: Path,
    workroot_id: str,
    focus_resolution: FocusResolution,
) -> None:
    try:
        call = response.get("workroot_contract", {}).get("next_exchange", {})
        packet = build_private_packet(
            response,
            adapter="cli",
            agent=str(request.agent.get("name") or "agent"),
            transport=str(request.agent.get("transport") or "cli"),
        )
        packet_call = packet.get("call") if isinstance(packet.get("call"), dict) else {}
        shape = str(packet_call.get("shape") or "")
        packet_text = render_private_packet_markdown(
            response,
            adapter="cli",
            agent=str(request.agent.get("name") or "agent"),
            transport=str(request.agent.get("transport") or "cli"),
        )
        trimmed_open, trimmed_done = sync_packet_trim_counts(response)
        record_sync_packet_trace(
            state_directory=state_directory,
            workroot_id=workroot_id,
            request_id=request.request_id,
            agent=str(request.agent.get("name") or "agent"),
            transport=str(request.agent.get("transport") or "cli"),
            focus=str(response.get("workroot_view", {}).get("focus") or ""),
            confidence=str(response.get("workroot_view", {}).get("confidence") or ""),
            action=str(call.get("action") or ""),
            shape=shape,
            packet_bytes=len(packet_text.encode("utf-8")),
            task_bound=bool(focus_resolution.task_id),
            run_bound=bool(focus_resolution.run_id),
            compact=True,
            trimmed_open_items=trimmed_open,
            trimmed_done_items=trimmed_done,
        )
    except Exception:
        return


def _user_directory_from_record(workroot: dict[str, str]) -> Path | None:
    value = workroot.get("userDirectory")
    if not value:
        return None
    return Path(value).resolve()


def _resolve_workroot(request: SyncRequest, *, ai_workroot_home: Path | str | None = None) -> dict[str, str]:
    if request.workroot_id:
        for record in list_workroots(ai_workroot_home=ai_workroot_home):
            if record["workrootId"] == request.workroot_id:
                return record
        raise ValueError(f"Workroot not found: {request.workroot_id}")
    if request.cwd:
        return find_workroot_by_cwd(Path(request.cwd), ai_workroot_home=ai_workroot_home)
    raise ValueError("missing Workroot locator")


def _not_recorded_response(reason: str) -> dict[str, Any]:
    contract = empty_workroot_contract(next_action="sync", reason="workroot_location_unavailable")
    return semantic_response(
        ok=True,
        agent_may_continue=True,
        workroot_guidance=guidance_text(
            focus="unavailable",
            summary=reason,
            next_exchange_action="sync",
            warning="Workroot could not safely locate the target workspace for persistence.",
        ),
        workroot_contract=contract,
        workroot_view=workroot_view(
            focus="unavailable",
            task_brief=reason,
            confidence="none",
            why="commit location unavailable",
            warnings=[reason] if reason else [],
        ),
        result=result_payload(
            recorded=False,
            projected=False,
            accepted=False,
            status="not_recorded",
            warnings=[reason] if reason else [],
        ),
    )


def _sync_unavailable_response(reason: str) -> dict[str, Any]:
    contract = empty_workroot_contract(next_action="sync", reason="workroot_location_unavailable")
    return semantic_response(
        ok=True,
        agent_may_continue=True,
        workroot_guidance=guidance_text(
            focus="unavailable",
            summary=reason,
            next_exchange_action="sync",
            warning="Workroot could not provide durable context for this turn.",
        ),
        workroot_contract=contract,
        workroot_view=workroot_view(
            focus="unavailable",
            task_brief=reason,
            confidence="none",
            why="workroot location failed",
            warnings=[reason] if reason else [],
        ),
        result=result_payload(recorded=False, projected=False, accepted=False, status="not_recorded"),
    )


def _load_existing_batch(conn: sqlite3.Connection, workroot_id: str, idempotency_key: str) -> dict[str, str] | None:
    row = conn.execute(
        """
        SELECT semantic_hash, request_hash, response_json, status
        FROM protocol_commit_batches
        WHERE workroot_id = ? AND idempotency_key = ?
        """,
        (workroot_id, idempotency_key),
    ).fetchone()
    if row is None:
        return None
    return {
        "semantic_hash": row[0] or row[1],
        "request_hash": row[1],
        "response_json": row[2],
        "status": row[3],
    }


def _apply_commit_batch(
    conn: sqlite3.Connection,
    *,
    request: CommitRequest,
    workroot_id: str,
    state_directory: Path,
    user_directory: Path | None,
    batch_id: str,
    received_at: str,
) -> dict[str, Any]:
    events, invalid_events, invalid_items = _validate_commit_events(request.raw_events, received_at=received_at)
    if invalid_items:
        for event in invalid_events:
            _append_protocol_event(
                conn,
                batch_id=batch_id,
                workroot_id=workroot_id,
                lease_id=request.exchange_lease_id,
                request_id=request.request_id,
                idempotency_key=request.idempotency_key,
                event=event,
                received_at=received_at,
                status=EVENT_QUARANTINED,
            )
        _record_commit_rejection_friction(
            state_directory=state_directory,
            workroot_id=workroot_id,
            request=request,
            events=request.raw_events,
            stage="validation",
            code="invalid_event_schema",
            result_status="quarantined",
            details={"invalid_events": invalid_items},
        )
        return _commit_response(
            status="quarantined",
            recorded=True,
            projected=False,
            accepted=False,
            directive_type="not_recorded",
            directive_next_action="Continue helping the user. Sync before retrying durable Workroot persistence.",
            warnings=["invalid_event_schema"],
            invalid_events=invalid_items,
            state_directory=state_directory,
        )

    if _quick_intent_batch(events):
        return _commit_response(
            status="not_recorded",
            recorded=True,
            projected=False,
            accepted=False,
            directive_type="no_persistent_work",
            directive_goal="No persistent Workroot facts were created.",
            directive_next_action="Answer directly without creating persistent Workroot facts.",
            warnings=[],
            state_directory=state_directory,
        )

    if not request.exchange_lease_id:
        _record_commit_rejection_friction(
            state_directory=state_directory,
            workroot_id=workroot_id,
            request=request,
            events=events,
            stage="lease_guard",
            code="missing_exchange_lease_id",
            result_status="rejected",
        )
        return _commit_response(
            status="rejected",
            recorded=True,
            projected=False,
            accepted=False,
            directive_type="resync_required",
            directive_next_action="Call sync before committing durable Workroot facts.",
            warnings=["missing_exchange_lease_id"],
            state_directory=state_directory,
        )

    decision = decide_lease_safety(conn, request.exchange_lease_id, workroot_id=workroot_id, events=events)
    lease = decision.lease or {}
    if not decision.can_project:
        if decision.status == "quarantined":
            for event in events:
                _append_protocol_event(
                    conn,
                    batch_id=batch_id,
                    workroot_id=workroot_id,
                    lease_id=request.exchange_lease_id,
                    request_id=request.request_id,
                    idempotency_key=request.idempotency_key,
                    event=event,
                    received_at=received_at,
                    status=EVENT_QUARANTINED,
                )
        directive_type = "resync_required" if decision.status == "resync_required" else "not_recorded"
        _record_commit_rejection_friction(
            state_directory=state_directory,
            workroot_id=workroot_id,
            request=request,
            events=events,
            stage="lease_guard",
            code=decision.error_code or decision.status,
            result_status=decision.status,
        )
        return _commit_response(
            status=decision.status,
            recorded=True,
            projected=False,
            accepted=False,
            directive_type=directive_type,
            directive_next_action="Call sync before retrying durable Workroot persistence.",
            warnings=[decision.error_code] if decision.error_code else [],
            lease=lease,
            task_id=_text_or_none(lease.get("task_id")),
            run_id=_text_or_none(lease.get("run_id")),
            state_directory=state_directory,
        )

    projection_result: Optional[ProjectionResult] = None
    conn.execute("SAVEPOINT projection")
    try:
        for event in events:
            _append_protocol_event(
                conn,
                batch_id=batch_id,
                workroot_id=workroot_id,
                lease_id=request.exchange_lease_id,
                request_id=request.request_id,
                idempotency_key=request.idempotency_key,
                event=event,
                received_at=received_at,
                status=EVENT_APPLIED,
            )
            projection_result = apply_projection(
                conn,
                workroot_id=workroot_id,
                lease=lease,
                event=event,
                user_directory=user_directory,
                state_directory=state_directory,
            )
            _append_event_effects(conn, event_id=event["event_id"], effects=projection_result.effects)
            bump_state_version(
                conn,
                workroot_id,
                "event_log",
                received_at,
                updated_by_event_id=str(event["event_id"]),
                reason=f"commit:{event['kind']}",
            )
    except (ProjectionError, ProtocolError) as exc:
        conn.execute("ROLLBACK TO projection")
        conn.execute("RELEASE projection")
        hard_error = hard_projection_error(exc.code)
        if not hard_error:
            for event in events:
                _append_protocol_event(
                    conn,
                    batch_id=batch_id,
                    workroot_id=workroot_id,
                    lease_id=request.exchange_lease_id,
                    request_id=request.request_id,
                    idempotency_key=request.idempotency_key,
                    event=event,
                    received_at=received_at,
                    status=EVENT_QUARANTINED,
                )
        _record_commit_rejection_friction(
            state_directory=state_directory,
            workroot_id=workroot_id,
            request=request,
            events=events,
            stage="projection",
            code=exc.code,
            result_status="rejected" if hard_error else "quarantined",
            details=exc.details,
        )
        return _commit_response(
            status="rejected" if hard_error else "quarantined",
            recorded=True,
            projected=False,
            accepted=False,
            directive_type="resync_required",
            directive_next_action="Call sync before retrying durable Workroot persistence.",
            warnings=[exc.code],
            lease=lease,
            task_id=_text_or_none(lease.get("task_id")),
            run_id=_text_or_none(lease.get("run_id")),
            error={"code": exc.code, "message": exc.code, "details": exc.details} if hard_error else None,
            state_directory=state_directory,
        )
    except Exception as exc:
        conn.execute("ROLLBACK TO projection")
        conn.execute("RELEASE projection")
        code = _unexpected_commit_error_code(exc)
        _record_commit_rejection_friction(
            state_directory=state_directory,
            workroot_id=workroot_id,
            request=request,
            events=events,
            stage="projection",
            code=code,
            result_status="rejected",
        )
        return _commit_response(
            status="rejected",
            recorded=True,
            projected=False,
            accepted=False,
            directive_type="resync_required",
            directive_next_action="Call sync before retrying durable Workroot persistence.",
            warnings=[code],
            lease=lease,
            task_id=_text_or_none(lease.get("task_id")),
            run_id=_text_or_none(lease.get("run_id")),
            error={"code": code, "message": code, "details": {}},
            state_directory=state_directory,
        )
    else:
        conn.execute("RELEASE projection")

    next_lease: Optional[dict[str, Any]] = None
    next_allowed_events = (
        projection_result.allowed_events if projection_result else list(lease.get("allowed_events") or [])
    )
    next_required_before_stop = (
        projection_result.required_before_stop if projection_result else list(lease.get("required_before_stop") or [])
    )
    next_task_id = projection_result.task_id if projection_result else _text_or_none(lease.get("task_id"))
    next_run_id = projection_result.run_id if projection_result else _text_or_none(lease.get("run_id"))
    if next_allowed_events:
        next_lease = create_lease(
            conn,
            workroot_id=workroot_id,
            scope=str(projection_result.lease_scope if projection_result else lease.get("scope") or "workroot"),
            task_id=next_task_id,
            run_id=next_run_id,
            allowed_events=list(next_allowed_events),
            required_before_stop=list(next_required_before_stop),
        )
    return _commit_response(
        status="applied",
        recorded=True,
        projected=True,
        accepted=True,
        directive_type=projection_result.directive_type if projection_result else "continue_task",
        directive_goal=projection_result.directive_goal if projection_result else None,
        directive_next_action=projection_result.directive_next_action
        if projection_result
        else "Commit progress or handoff when a checkpoint is reached.",
        warnings=list(decision.warnings),
        lease=next_lease,
        task_id=next_task_id,
        run_id=next_run_id,
        allowed_events=list(next_allowed_events),
        required_before_stop=list(next_required_before_stop),
        state_directory=state_directory,
    )


def _validate_commit_events(
    raw_events: list[Any],
    *,
    received_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    invalid_events: list[dict[str, Any]] = []
    invalid_items: list[dict[str, Any]] = []
    for index, raw_event in enumerate(raw_events):
        if not isinstance(raw_event, dict):
            invalid_items.append(_invalid_event_item(index, raw_event, reason="event item must be an object"))
            continue
        if not minimally_identifiable(raw_event):
            invalid_items.append(
                _invalid_event_item(index, raw_event, reason="event item is not minimally identifiable")
            )
            continue
        try:
            events.append(validate_event_envelope(raw_event))
        except ProtocolError as exc:
            invalid_events.append(safe_event_for_storage(raw_event, occurred_at=received_at))
            invalid_items.append(_invalid_event_item(index, raw_event, reason=exc.code))
    return events, invalid_events, invalid_items


def _invalid_event_item(index: int, item: Any, *, reason: str) -> dict[str, Any]:
    detail = {
        "index": index,
        "reason": reason,
        "item_type": type(item).__name__,
    }
    if isinstance(item, dict):
        event_id = str(item.get("event_id") or "").strip()
        kind = str(item.get("kind") or "").strip()
        if event_id:
            detail["event_id"] = event_id
        if kind:
            detail["kind"] = kind
    return detail


def _record_commit_rejection_friction(
    *,
    state_directory: Path,
    workroot_id: str,
    request: CommitRequest,
    events: list[Any],
    stage: str,
    code: str,
    result_status: str,
    details: dict[str, Any] | None = None,
) -> None:
    record_protocol_friction(
        state_directory=state_directory,
        workroot_id=workroot_id,
        action="commit",
        source_layer="protocol_controller",
        stage=stage,
        code=code,
        result_status=result_status,
        request_id=request.request_id,
        lease_id=request.exchange_lease_id,
        idempotency_key=request.idempotency_key,
        shape=_shape_for_events(events),
        details=details,
    )


def _shape_for_events(events: list[Any]) -> str:
    shapes = {EVENT_KIND_TO_SHAPE.get(str(event.get("kind") or ""), "") for event in events if isinstance(event, dict)}
    shapes.discard("")
    if len(shapes) == 1:
        return next(iter(shapes))
    if len(shapes) > 1:
        return "batch"
    return ""


def _commit_response(
    *,
    status: str,
    recorded: bool,
    projected: bool,
    accepted: bool,
    directive_type: str,
    directive_next_action: str,
    warnings: list[str],
    directive_goal: Optional[str] = None,
    lease: Optional[dict[str, Any]] = None,
    task_id: Optional[str] = None,
    run_id: Optional[str] = None,
    allowed_events: Optional[list[str]] = None,
    required_before_stop: Optional[list[str]] = None,
    error: Optional[dict[str, Any]] = None,
    invalid_events: Optional[list[dict[str, Any]]] = None,
    state_directory: Optional[Path] = None,
) -> dict[str, Any]:
    if not accepted and status in {"rejected", "resync_required", "quarantined"}:
        lease = None
        allowed_events = []
        required_before_stop = []
        task_id = None
        run_id = None
    expected_events = list(allowed_events or (lease or {}).get("allowed_events") or [])
    required = list(required_before_stop or (lease or {}).get("required_before_stop") or [])
    if directive_type == "resync_required" or status in {"rejected", "resync_required", "quarantined"}:
        suggested_action = "sync"
        reason = "resync_required"
    elif expected_events:
        suggested_action = "commit"
        reason = "meaningful_checkpoint"
    else:
        suggested_action = "none"
        reason = "safe_to_continue"
    contract = workroot_contract_from_lease(
        lease,
        next_action=suggested_action,
        reason=reason,
        allowed_commit_kinds=expected_events,
        required_before_stop=required,
        task_ref=task_id,
        run_ref=run_id,
    )
    view = workroot_view(
        focus=_commit_focus(directive_type=directive_type, task_id=task_id),
        task_brief=directive_goal or directive_next_action,
        confidence="medium" if accepted else "low",
        why=f"commit result: {status}",
        output_rules=_compact_output_rules_from_state_directory(state_directory),
        warnings=warnings,
    )
    result = result_payload(
        recorded=recorded,
        projected=projected,
        accepted=accepted,
        status=status,
        warnings=warnings,
    )
    if invalid_events:
        result["invalid_events"] = list(invalid_events)
    payload = semantic_response(
        ok=error is None,
        agent_may_continue=True,
        workroot_guidance=guidance_text(
            focus=view["focus"],
            summary=view["task_brief"],
            next_exchange_action=suggested_action,
            accepted_shapes=contract["commit_contract"]["accepted_shapes"],
            required_before_stop=contract["commit_contract"]["required_before_stop"],
            warning=", ".join(warnings),
        ),
        workroot_contract=contract,
        workroot_view=view,
        result=result,
        error=error,
    )
    return payload


def _quick_intent_batch(events: list[dict[str, Any]]) -> bool:
    if not events:
        return False
    return all(_quick_intent_event(event) for event in events)


def _quick_intent_event(event: dict[str, Any]) -> bool:
    if event.get("kind") != "intent":
        return False
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    classification = payload.get("classification") if isinstance(payload.get("classification"), dict) else {}
    return str(classification.get("persistence") or "") == "quick"


def _commit_focus(*, directive_type: str, task_id: Optional[str]) -> str:
    if directive_type == "capture_workroot":
        return "workroot_capture"
    if directive_type == "no_persistent_work":
        return "no_persistent_work"
    if task_id:
        return "continuation"
    return "new_work"


def _recovery_response(reason: str) -> dict[str, Any]:
    contract = empty_workroot_contract(next_action="sync", reason="recovery")
    return semantic_response(
        ok=True,
        agent_may_continue=True,
        workroot_guidance=guidance_text(
            focus="recovery",
            summary=reason,
            next_exchange_action="sync",
            warning="A previous commit batch is still applying.",
        ),
        workroot_contract=contract,
        workroot_view=workroot_view(
            focus="recovery",
            task_brief=reason,
            confidence="low",
            why="idempotent batch is applying",
            warnings=[reason],
        ),
        result=result_payload(
            recorded=True, projected=False, accepted=False, status="resync_required", warnings=[reason]
        ),
    )


def _unexpected_commit_response(
    exc: Exception,
    *,
    state_directory: Path,
    recorded: bool,
) -> dict[str, Any]:
    code = _unexpected_commit_error_code(exc)
    return _commit_response(
        status="rejected",
        recorded=recorded,
        projected=False,
        accepted=False,
        directive_type="resync_required",
        directive_next_action="Call sync before retrying durable Workroot persistence.",
        warnings=[code],
        error={"code": code, "message": code, "details": {}},
        state_directory=state_directory,
    )


def _unexpected_commit_error_code(exc: Exception) -> str:
    if isinstance(exc, sqlite3.Error):
        return "storage_error"
    return "projection_error"


def _store_terminal_batch_response(
    conn: sqlite3.Connection,
    *,
    batch_id: str,
    response: dict[str, Any],
    completed_at: str,
) -> None:
    status = str((response.get("result") or {}).get("status") or "rejected")
    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    error_payload = response.get("error") or (
        {"invalid_events": result.get("invalid_events")} if result.get("invalid_events") else None
    )
    error_json = canonical_json(error_payload) if error_payload else None
    conn.execute(
        """
        UPDATE protocol_commit_batches
        SET response_json = ?, status = ?, completed_at = ?, error_json = ?
        WHERE batch_id = ?
        """,
        (canonical_json(response), status, completed_at, error_json, batch_id),
    )


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _commit_request_hash(request_data: dict[str, Any]) -> str:
    return request_hash(_normalize_auto_shorthand_request_for_hash(request_data))


def _normalize_auto_shorthand_request_for_hash(request_data: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(canonical_json(request_data))
    if not _looks_like_auto_shorthand_request(normalized):
        return normalized
    for event in normalized.get("events") or []:
        if isinstance(event, dict) and str(event.get("event_id") or "").startswith("evt-auto-"):
            event["occurred_at"] = "<auto-generated>"
    return normalized


def _looks_like_auto_shorthand_request(request_data: dict[str, Any]) -> bool:
    return str(request_data.get("request_id") or "").startswith("req-auto-") and str(
        request_data.get("idempotency_key") or ""
    ).startswith("idem-auto-")


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
    status: str,
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
            status,
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


def _sync_response(
    workroot: dict[str, str],
    directive_payload: dict[str, Any],
    lease: Optional[dict[str, Any]],
    *,
    context: dict[str, Any],
    focus_resolution: FocusResolution,
) -> dict[str, Any]:
    expected_events = list(directive_payload.get("expected_events") or [])
    if focus_resolution.directive_type == "commit_required":
        suggested_action = "commit"
        reason = "start_work"
    elif focus_resolution.directive_type == "continue_task":
        suggested_action = "commit"
        reason = "meaningful_checkpoint"
    elif focus_resolution.directive_type == "capture_workroot":
        suggested_action = "commit"
        reason = "workroot_capture"
    elif focus_resolution.directive_type == "ask_user":
        suggested_action = "none"
        reason = "guarded_action"
    elif focus_resolution.directive_type == "refine_focus":
        suggested_action = "sync"
        reason = "focus_refinement_required"
    elif focus_resolution.kind == "ambiguous" and focus_resolution.candidate_refs:
        suggested_action = "sync"
        reason = "focus_refinement_required"
    else:
        suggested_action = "none"
        reason = "no_exchange_needed"
    if suggested_action == "commit" and lease is None:
        suggested_action = "sync"
        reason = "alignment_required"
    task_brief = str(focus_resolution.summary or context.get("brief") or directive_payload.get("goal") or "")
    view = workroot_view(
        focus=focus_resolution.kind,
        task_brief=task_brief,
        confidence=focus_resolution.confidence,
        why=focus_resolution.why,
        current_state=str(context.get("current_state") or ""),
        next_action=str(context.get("next_action") or ""),
        open_items=list(context.get("open_items") or []),
        recent_done_items=list(context.get("recent_done_items") or []),
        refs=list(context.get("refs") or []),
        output_rules=_compact_output_rules_from_record(workroot),
        warnings=list(context.get("warnings") or []),
    )
    contract = workroot_contract_from_lease(
        lease,
        next_action=suggested_action,
        reason=reason,
        allowed_commit_kinds=expected_events,
        required_before_stop=list(directive_payload.get("required_before_stop") or []),
        task_ref=focus_resolution.task_id,
        run_ref=focus_resolution.run_id,
        context_refs=_sync_context_refs(context=context, focus_resolution=focus_resolution),
        binding=_binding_from_focus(focus_resolution),
        preferred_shape=focus_resolution.preferred_shape,
    )
    return semantic_response(
        ok=True,
        agent_may_continue=True,
        workroot_guidance=guidance_text(
            focus=view["focus"],
            summary=view["task_brief"],
            current_state=view["current_state"],
            next_action=view["next_action"],
            next_exchange_action=suggested_action,
            accepted_shapes=contract["commit_contract"]["accepted_shapes"],
            required_before_stop=contract["commit_contract"]["required_before_stop"],
            warning=", ".join(view["warnings"]),
        ),
        workroot_contract=contract,
        workroot_view=view,
        result=result_payload(recorded=False, projected=False, accepted=False, status="not_recorded"),
    )


def _compact_output_rules_from_record(workroot: dict[str, str]) -> list[dict[str, str]]:
    state_directory = workroot.get("stateDirectory")
    if not state_directory:
        return []
    try:
        return compact_asset_output_rules(Path(state_directory))
    except (OSError, ValueError):
        return []


def _sync_context_refs(*, context: dict[str, Any], focus_resolution: FocusResolution) -> list[dict[str, Any]]:
    refs = [item for item in list(context.get("refs") or []) if isinstance(item, dict)]
    for item in focus_resolution.candidate_refs:
        refs.append(dict(item))
    return refs


def _binding_from_focus(focus_resolution: FocusResolution) -> dict[str, Any]:
    mode = _binding_mode(focus_resolution)
    if not mode:
        return {}
    binding: dict[str, Any] = {
        "mode": mode,
        "confidence": focus_resolution.confidence,
        "reason": focus_resolution.why,
    }
    refs: dict[str, str] = {}
    if focus_resolution.task_id:
        refs["task"] = focus_resolution.task_id
    if focus_resolution.run_id:
        refs["run"] = focus_resolution.run_id
    if refs:
        binding["refs"] = refs
    return binding


def _binding_mode(focus_resolution: FocusResolution) -> str:
    if focus_resolution.kind == "continuation" and focus_resolution.task_id:
        return "continue_existing"
    if focus_resolution.kind == "new_work":
        policy = focus_resolution.write_policy or {}
        if policy.get("expected_task_role") == "inbox":
            return "temporary"
        return "start_new"
    if focus_resolution.kind == "workroot_capture":
        return "capture_workroot"
    if focus_resolution.kind == "ambiguous":
        return "clarify"
    return ""


def _compact_output_rules_from_state_directory(state_directory: Optional[Path]) -> list[dict[str, str]]:
    if not state_directory:
        return []
    try:
        return compact_asset_output_rules(state_directory)
    except (OSError, ValueError):
        return []
