"""Runtime protocol-friction diagnostics."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from ai_workroot.state.environment import utc_now
from ai_workroot.state.jsonl import append_jsonl, read_jsonl
from ai_workroot.state.registry import find_workroot_by_cwd, list_workroots


FRICTION_LOG_RELATIVE_PATH = Path("logs/protocol-friction.jsonl")


def record_protocol_friction(
    *,
    state_directory: Path,
    workroot_id: str,
    action: str,
    source_layer: str,
    stage: str,
    code: str,
    severity: str = "recoverable",
    result_status: str = "rejected",
    request_id: str = "",
    lease_id: str = "",
    idempotency_key: str = "",
    shape: str = "",
    details: dict[str, Any] | None = None,
    occurred_at: str | None = None,
) -> None:
    record = {
        "eventId": f"friction_{uuid.uuid4().hex}",
        "workrootId": workroot_id,
        "action": action,
        "sourceLayer": source_layer,
        "stage": stage,
        "code": code,
        "severity": severity,
        "resultStatus": result_status,
        "occurredAt": occurred_at or utc_now(),
    }
    for key, value in (
        ("requestId", request_id),
        ("leaseId", lease_id),
        ("idempotencyKey", idempotency_key),
        ("shape", shape),
    ):
        if value:
            record[key] = value
    if details:
        record["details"] = _sanitize_details(details)
    append_jsonl(Path(state_directory) / FRICTION_LOG_RELATIVE_PATH, record)


def record_locatable_protocol_friction(
    *,
    cwd: Path | str | None = None,
    workroot_id: str | None = None,
    ai_workroot_home: Path | str | None = None,
    action: str,
    source_layer: str,
    stage: str,
    code: str,
    severity: str = "recoverable",
    result_status: str = "rejected",
    request_id: str = "",
    lease_id: str = "",
    idempotency_key: str = "",
    shape: str = "",
    details: dict[str, Any] | None = None,
) -> bool:
    try:
        located = _locate_workroot(cwd=cwd, workroot_id=workroot_id, ai_workroot_home=ai_workroot_home)
        if located is None:
            return False
        record_protocol_friction(
            state_directory=Path(located["stateDirectory"]),
            workroot_id=located["workrootId"],
            action=action,
            source_layer=source_layer,
            stage=stage,
            code=code,
            severity=severity,
            result_status=result_status,
            request_id=request_id,
            lease_id=lease_id,
            idempotency_key=idempotency_key,
            shape=shape,
            details=details,
        )
        return True
    except Exception:
        return False


def summarize_protocol_friction(
    *,
    state_directory: Path,
    workroot_id: str,
    recent_limit: int = 20,
) -> dict[str, Any]:
    events = [
        event
        for event in read_jsonl(Path(state_directory) / FRICTION_LOG_RELATIVE_PATH)
        if str(event.get("workrootId") or "") == workroot_id
    ]
    events.sort(key=lambda event: str(event.get("occurredAt") or ""))
    return {
        "frictionEventsTotal": len(events),
        "frictionByCode": _count_by(events, "code"),
        "frictionByStage": _count_by(events, "stage"),
        "frictionBySourceLayer": _count_by(events, "sourceLayer"),
        "recent": [_recent_payload(event) for event in events[-recent_limit:]],
    }


def _locate_workroot(
    *,
    cwd: Path | str | None,
    workroot_id: str | None,
    ai_workroot_home: Path | str | None,
) -> dict[str, str] | None:
    if workroot_id:
        for record in list_workroots(ai_workroot_home=ai_workroot_home):
            if record["workrootId"] == workroot_id:
                return record
        return None
    if cwd:
        try:
            return find_workroot_by_cwd(Path(cwd), ai_workroot_home=ai_workroot_home)
        except ValueError:
            return None
    return None


def _count_by(events: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = str(event.get(key) or "")
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _recent_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in (
        "code",
        "action",
        "sourceLayer",
        "stage",
        "resultStatus",
        "requestId",
        "leaseId",
        "shape",
        "occurredAt",
    ):
        value = event.get(key)
        if value:
            payload[key] = value
    return payload


def _sanitize_details(details: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in details.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [str(item)[:200] for item in value[:20]]
        elif isinstance(value, dict):
            sanitized[key] = {str(item_key): str(item_value)[:200] for item_key, item_value in list(value.items())[:20]}
        else:
            sanitized[key] = str(value)[:200]
    return sanitized
