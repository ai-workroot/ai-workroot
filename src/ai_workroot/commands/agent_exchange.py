"""Agent protocol command adapter."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from ai_workroot.protocol import controller
from ai_workroot.protocol.events import canonical_json
from ai_workroot.protocol.errors import protocol_error_response
from ai_workroot.protocol.lease import now_utc
from ai_workroot.protocol.model import PROTOCOL_VERSION, SYNC_REASONS
from ai_workroot.protocol.packet import render_private_packet_markdown
from ai_workroot.state.protocol_friction import record_locatable_protocol_friction


SYNC_REASON_CHOICES = sorted(SYNC_REASONS)
COMMIT_SHAPES = ("start_work", "checkpoint", "continuation", "state_update", "asset", "decision")
SHAPE_TO_EVENT_KIND = {
    "start_work": "intent",
    "checkpoint": "progress",
    "continuation": "handoff",
    "state_update": "state",
    "asset": "asset",
    "decision": "decision",
}


def run_exchange_request(request_path: Path) -> dict[str, Any]:
    envelope = _read_json_object(request_path)
    action = str(envelope.get("action") or "")
    request = envelope.get("request") or {}
    if not isinstance(request, dict):
        request = {}
    if action == "sync":
        return controller.sync(request)
    if action == "commit":
        return controller.commit(request)
    return invalid_exchange_action()


def run_sync_request(
    *,
    request_id: str,
    agent_name: str,
    agent_transport: str = "cli",
    cwd: Path,
    query: str,
    reason: str,
    workroot_id: Optional[str] = None,
    known_state: Optional[dict[str, Any]] = None,
    work_signal: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "agent": {"name": agent_name, "transport": agent_transport.strip() or "cli"},
        "cwd": str(cwd),
        "reason": reason,
        "query": query,
        "known_state": known_state or {},
        "work_signal": work_signal or {},
    }
    if workroot_id:
        request["workroot_id"] = workroot_id
    return controller.sync(request)


def run_commit_request(request_path: Path) -> dict[str, Any]:
    return controller.commit(_read_json_object(request_path))


def run_commit_shape(
    *,
    shape: str,
    lease_id: str,
    agent_name: str,
    agent_transport: str = "cli",
    client: str = "",
    agent_version: str = "",
    thread_id: str = "",
    channel_id: str = "",
    cwd: Optional[Path] = None,
    workroot_id: Optional[str] = None,
    title: str = "",
    summary: str = "",
    current_state: str = "",
    next_action: str = "",
    state: str = "",
    next: str = "",
    task_id: Optional[str] = None,
    run_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    persistence: str = "normal",
    done: tuple[str, ...] = (),
    open: tuple[str, ...] = (),
    blocked: tuple[str, ...] = (),
    target: Optional[str] = None,
    change: Optional[str] = None,
    path: str = "",
    asset_kind: str = "",
    status: str = "",
    decision: str = "",
    reason_text: str = "",
    scope: str = "",
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
    request_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict[str, Any]:
    try:
        request = build_commit_request_from_shape(
            shape=shape,
            lease_id=lease_id,
            agent_name=agent_name,
            agent_transport=agent_transport,
            client=client,
            agent_version=agent_version,
            thread_id=thread_id,
            channel_id=channel_id,
            cwd=cwd,
            workroot_id=workroot_id,
            title=title,
            summary=summary,
            current_state=state or current_state,
            next_action=next or next_action,
            task_id=task_id,
            run_id=run_id,
            parent_task_id=parent_task_id,
            persistence=persistence,
            done=done,
            open=open,
            blocked=blocked,
            target=target,
            change=change,
            path=path,
            asset_kind=asset_kind,
            status=status,
            decision=decision,
            reason_text=reason_text,
            scope=scope,
            session_id=session_id,
            event_id=event_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at,
        )
    except ValueError as exc:
        record_locatable_protocol_friction(
            cwd=cwd,
            workroot_id=workroot_id,
            action="commit",
            source_layer="cli_adapter",
            stage="pre_request",
            code="missing_shape_fields",
            result_status="rejected",
            request_id=request_id or "",
            lease_id=lease_id,
            shape=shape,
            details={"message": str(exc)},
        )
        return protocol_error_response(
            "missing_shape_fields",
            details={"message": str(exc), "shape": shape},
            next_action="Sync before retrying durable persistence, then provide the required fields for this shape.",
            result_status="rejected",
        )
    return controller.commit(request)


def render_agent_response(
    response: dict[str, Any], *, output_format: str = "json", agent: str = "codex", transport: str = "cli"
) -> str:
    if output_format == "guidance":
        return str(response.get("workroot_guidance") or "").rstrip() + "\n"
    if output_format == "packet":
        return render_private_packet_markdown(response, adapter="cli", agent=agent, transport=transport).rstrip() + "\n"
    if output_format != "json":
        raise ValueError("--format must be json, guidance, or packet")
    return json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n"


def build_commit_request_from_shape(
    *,
    shape: str,
    lease_id: str,
    agent_name: str,
    agent_transport: str = "cli",
    client: str = "",
    agent_version: str = "",
    thread_id: str = "",
    channel_id: str = "",
    cwd: Optional[Path] = None,
    workroot_id: Optional[str] = None,
    title: str = "",
    summary: str = "",
    current_state: str = "",
    next_action: str = "",
    state: str = "",
    next: str = "",
    task_id: Optional[str] = None,
    run_id: Optional[str] = None,
    parent_task_id: Optional[str] = None,
    persistence: str = "normal",
    done: tuple[str, ...] = (),
    open: tuple[str, ...] = (),
    blocked: tuple[str, ...] = (),
    target: Optional[str] = None,
    change: Optional[str] = None,
    path: str = "",
    asset_kind: str = "",
    status: str = "",
    decision: str = "",
    reason_text: str = "",
    scope: str = "",
    session_id: Optional[str] = None,
    event_id: Optional[str] = None,
    request_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    occurred_at: Optional[str] = None,
) -> dict[str, Any]:
    requested_shape = _normalize_shape(shape)
    if requested_shape not in COMMIT_SHAPES:
        raise ValueError(f"--shape must be one of: {', '.join(COMMIT_SHAPES)}")
    event_kind = SHAPE_TO_EVENT_KIND[requested_shape]

    payload = _shorthand_payload(
        kind=event_kind,
        title=title,
        summary=summary,
        current_state=state or current_state,
        next_action=next or next_action,
        task_id=task_id,
        run_id=run_id,
        parent_task_id=parent_task_id,
        persistence=persistence,
        done=done,
        open=open,
        blocked=blocked,
        target=target,
        change=change,
        path=path,
        asset_kind=asset_kind,
        status=status,
        decision=decision,
        reason_text=reason_text,
        scope=scope,
    )
    digest = _shorthand_digest(
        {
            "shape": requested_shape,
            "event_kind": event_kind,
            "lease_id": lease_id.strip(),
            "agent_name": agent_name.strip() or "agent",
            "payload": payload,
        }
    )
    source: dict[str, Any] = {
        "actor_type": "agent",
        "actor_name": agent_name.strip() or "agent",
    }
    _add_source_metadata(
        source,
        transport=agent_transport,
        client=client,
        agent_version=agent_version,
        thread_id=thread_id,
        channel_id=channel_id,
    )
    if session_id:
        source["session_id"] = session_id
    request: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id or f"req-auto-{digest}",
        "exchange_lease_id": lease_id.strip(),
        "idempotency_key": idempotency_key or f"idem-auto-{digest}",
        "events": [
            {
                "event_id": event_id or f"evt-auto-{digest}",
                "kind": event_kind,
                "schema_version": f"{event_kind}.v1",
                "occurred_at": occurred_at or now_utc(),
                "source": source,
                "confirmation": {"status": "agent_observed", "confirmed_by": None},
                "payload": payload,
                "evidence": [],
            }
        ],
    }
    if cwd is not None:
        request["cwd"] = str(cwd)
    if workroot_id:
        request["workroot_id"] = workroot_id
    return request


def invalid_exchange_action() -> dict[str, Any]:
    return protocol_error_response(
        "invalid_exchange_action",
        next_action="Use action=sync or action=commit.",
        result_status="rejected",
    )


def _shorthand_payload(
    *,
    kind: str,
    title: str,
    summary: str,
    current_state: str,
    next_action: str,
    task_id: Optional[str],
    run_id: Optional[str],
    parent_task_id: Optional[str],
    persistence: str,
    done: tuple[str, ...],
    open: tuple[str, ...],
    blocked: tuple[str, ...],
    target: Optional[str],
    change: Optional[str],
    path: str,
    asset_kind: str,
    status: str,
    decision: str,
    reason_text: str,
    scope: str,
) -> dict[str, Any]:
    if kind == "intent":
        intent_text = summary.strip() or title.strip()
        if not intent_text:
            raise ValueError("--summary or --title is required for intent shorthand")
        persistence_value = persistence.strip() or "normal"
        if persistence_value not in {"normal", "temporary", "quick"}:
            raise ValueError("--persistence must be normal, temporary, or quick")
        return {
            "intent_text": intent_text,
            "classification": {
                "persistence": persistence_value,
                "confidence": 0.9,
                "reason": "agent_commit_shorthand",
            },
            "task_hint": {
                "title": title.strip() or intent_text,
                "task_id": _clean_optional(task_id),
                "parent_task_id": _clean_optional(parent_task_id),
            },
        }
    if kind == "progress":
        cleaned_done = _clean_item_values(done)
        cleaned_open = _clean_item_values(open)
        cleaned_blocked = _clean_item_values(blocked)
        if not summary.strip() and not cleaned_done and not cleaned_open and not cleaned_blocked:
            raise ValueError("--summary, --done, --open, or --blocked is required for progress shorthand")
        payload: dict[str, Any] = {
            "summary": summary.strip(),
            "items_created": [
                *[{"title": item, "status": "done", "result_summary": item} for item in cleaned_done],
                *[{"title": item, "status": "todo", "result_summary": None} for item in cleaned_open],
                *[{"title": item, "status": "blocked", "result_summary": None} for item in cleaned_blocked],
            ],
            "open_questions": [],
            "source_refs": [],
        }
        _add_task_run_fields(payload, task_id=task_id, run_id=run_id)
        return payload
    if kind == "handoff":
        if not current_state.strip() and not next_action.strip() and summary.strip():
            current_state = summary
        if not current_state.strip() and not next_action.strip():
            raise ValueError("--state/--current-state or --next/--next-action is required for continuation")
        payload = {
            "current_state": current_state.strip(),
            "next_action": next_action.strip(),
            "open_items": [],
            "open_questions": [],
            "important_refs": [],
            "source_refs": [],
        }
        _add_task_run_fields(payload, task_id=task_id, run_id=run_id)
        return payload
    if kind == "state":
        return _state_update_payload(target=target, change=change)
    if kind == "asset":
        payload = _asset_payload(
            title=title,
            path=path,
            asset_kind=asset_kind,
            summary=summary,
            status=status,
            task_id=task_id,
            run_id=run_id,
        )
        return payload
    if kind == "decision":
        payload = _decision_payload(
            title=title,
            decision=decision,
            reason_text=reason_text,
            scope=scope,
            task_id=task_id,
            run_id=run_id,
        )
        return payload
    raise ValueError(f"unsupported commit shape event kind: {kind}")


def _state_update_payload(*, target: Optional[str], change: Optional[str]) -> dict[str, Any]:
    target_type, target_id = _parse_target(target)
    change_value = _clean_optional(change)
    if not change_value:
        raise ValueError("--change is required for state_update")
    if target_type == "output_rule":
        path = _parse_output_rule_change(change_value)
        return {
            "target_type": target_type,
            "target_id": target_id,
            "path": path,
            "reason": f"User declared output rule for {target_id}.",
        }
    compact = change_value.lower().strip()
    if compact == "close:completed":
        return {
            "target_type": target_type,
            "target_id": target_id,
            "from_status": "active",
            "to_status": "closed",
            "close_reason": "completed",
            "reason": "Task completed.",
        }
    status_change = _parse_status_change(change_value)
    if status_change:
        from_status, to_status = status_change
        return {
            "target_type": target_type,
            "target_id": target_id,
            "from_status": from_status,
            "to_status": to_status,
            "reason": change_value,
        }
    raise ValueError("--change supports close:completed or status <from> -> <to>")


def _parse_output_rule_change(value: str) -> str:
    cleaned = value.strip()
    lower = cleaned.lower()
    if lower.startswith("path="):
        path = cleaned[5:].strip()
    elif lower.startswith("path "):
        path = cleaned[5:].strip()
    else:
        raise ValueError("--change for output-rule targets supports path <relative-path> or path=<relative-path>")
    if not path:
        raise ValueError("--change for output-rule targets requires a relative path")
    return path


def _clean_item_values(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(item for item in (_clean_item_value(value) for value in values) if item)


def _clean_item_value(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    marker = text.lower().strip(" .:-_")
    if marker in {"n/a", "na", "nil", "none", "nothing", "not applicable"}:
        return None
    return text


def _asset_payload(
    *,
    title: str,
    path: str,
    asset_kind: str,
    summary: str,
    status: str,
    task_id: Optional[str],
    run_id: Optional[str],
) -> dict[str, Any]:
    cleaned_title = title.strip()
    cleaned_path = path.strip()
    if not cleaned_path:
        raise ValueError("--path is required for asset")
    if not cleaned_title:
        cleaned_title = _title_from_path(cleaned_path)
    payload: dict[str, Any] = {
        "title": cleaned_title,
        "path": cleaned_path,
        "asset_kind": asset_kind.strip() or "artifact",
        "summary": summary.strip(),
        "status": status.strip() or "current",
    }
    _add_task_run_fields(payload, task_id=task_id, run_id=run_id)
    return payload


def _decision_payload(
    *,
    title: str,
    decision: str,
    reason_text: str,
    scope: str,
    task_id: Optional[str],
    run_id: Optional[str],
) -> dict[str, Any]:
    cleaned_decision = decision.strip()
    if not cleaned_decision:
        raise ValueError("--decision is required for decision")
    payload: dict[str, Any] = {
        "title": title.strip() or cleaned_decision[:80],
        "decision": cleaned_decision,
        "reason": reason_text.strip(),
        "scope": scope.strip() or "task",
    }
    _add_task_run_fields(payload, task_id=task_id, run_id=run_id)
    return payload


def _title_from_path(value: str) -> str:
    stem = Path(value).stem.strip()
    normalized = stem.replace("-", " ").replace("_", " ").strip()
    return normalized.title() if normalized else "Asset"


def _parse_target(value: Optional[str]) -> tuple[str, str]:
    cleaned = _clean_optional(value)
    if not cleaned:
        raise ValueError("--target is required for state_update")
    if ":" in cleaned:
        target_type, target_id = cleaned.split(":", 1)
        target_type = target_type.strip() or "task"
        target_id = target_id.strip()
    else:
        target_type = "task"
        target_id = cleaned
    if target_type == "output-rule":
        target_type = "output_rule"
    if target_type not in {"task", "output_rule"}:
        raise ValueError("--target currently supports task or output-rule targets")
    if not target_id:
        raise ValueError("--target is required for state_update")
    return target_type, target_id


def _parse_status_change(value: str) -> Optional[tuple[str, str]]:
    normalized = value.strip()
    if normalized.lower().startswith("status "):
        normalized = normalized[7:].strip()
    if "->" not in normalized:
        return None
    from_status, to_status = (part.strip().lower() for part in normalized.split("->", 1))
    if not from_status or not to_status:
        return None
    return from_status, to_status


def _normalize_shape(value: str) -> str:
    return value.strip().lower().replace("-", "_")


def _add_task_run_fields(payload: dict[str, Any], *, task_id: Optional[str], run_id: Optional[str]) -> None:
    cleaned_task_id = _clean_optional(task_id)
    cleaned_run_id = _clean_optional(run_id)
    if cleaned_task_id:
        payload["task_id"] = cleaned_task_id
    if cleaned_run_id:
        payload["run_id"] = cleaned_run_id


def _add_source_metadata(
    source: dict[str, Any],
    *,
    transport: str,
    client: str,
    agent_version: str,
    thread_id: str,
    channel_id: str,
) -> None:
    for key, value in (
        ("transport", transport),
        ("client", client),
        ("agent_version", agent_version),
        ("thread_id", thread_id),
        ("channel_id", channel_id),
    ):
        cleaned = str(value or "").strip()
        if cleaned:
            source[key] = cleaned


def _clean_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _shorthand_digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()[:16]


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("request file must contain a JSON object")
    return data
