"""Protocol request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from ai_workroot.protocol.errors import ProtocolError
from ai_workroot.protocol.work_signal import WorkSignal


PROTOCOL_VERSION = "workroot.v1"
SYNC_REASONS = {
    "startup",
    "continue",
    "before_work",
    "context_refresh",
    "after_error",
    "before_task_switch",
    "before_handoff",
    "manual_check",
    "before_high_risk_action",
}


def require_protocol_version(data: dict[str, Any]) -> None:
    version = data.get("protocol_version")
    if not version:
        raise ProtocolError("missing_protocol_version")
    if version != PROTOCOL_VERSION:
        raise ProtocolError("unsupported_protocol_version")


@dataclass(frozen=True)
class SyncRequest:
    request_id: str
    agent: dict[str, Any]
    cwd: Optional[str]
    workroot_id: Optional[str]
    reason: str
    query: str
    known_state: dict[str, Any]
    work_signal: dict[str, object]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SyncRequest":
        require_protocol_version(data)
        agent = data.get("agent") or {}
        if not data.get("request_id"):
            raise ProtocolError("missing_request_id")
        if not agent.get("name") or not agent.get("transport"):
            raise ProtocolError("invalid_agent")
        if not data.get("cwd") and not data.get("workroot_id"):
            raise ProtocolError("missing_workroot_locator")
        reason = data.get("reason")
        if reason not in SYNC_REASONS:
            raise ProtocolError("invalid_sync_reason")
        return cls(
            request_id=data["request_id"],
            agent=agent,
            cwd=data.get("cwd"),
            workroot_id=data.get("workroot_id"),
            reason=reason,
            query=data.get("query") or "",
            known_state=data.get("known_state") or {},
            work_signal=WorkSignal.from_dict(data.get("work_signal")).to_dict(),
        )


@dataclass(frozen=True)
class CommitRequest:
    request_id: str
    exchange_lease_id: str
    cwd: Optional[str]
    workroot_id: Optional[str]
    idempotency_key: str
    atomic_batch: bool
    events: list[dict[str, Any]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommitRequest":
        require_protocol_version(data)
        events = data.get("events")
        if not isinstance(events, list) or not events:
            raise ProtocolError("empty_event_batch")
        for field in ("request_id", "idempotency_key"):
            if not data.get(field):
                raise ProtocolError(f"missing_{field}")
        return cls(
            request_id=data["request_id"],
            exchange_lease_id=data.get("exchange_lease_id") or "",
            cwd=data.get("cwd"),
            workroot_id=data.get("workroot_id"),
            idempotency_key=data["idempotency_key"],
            atomic_batch=data.get("atomic_batch") is not False,
            events=[event for event in events if isinstance(event, dict)],
        )
