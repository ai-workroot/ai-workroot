"""Helpers for non-blocking protocol event preservation."""

from __future__ import annotations

from typing import Any


EVENT_APPLIED = "applied"
EVENT_QUARANTINED = "quarantined"


def minimally_identifiable(event: object) -> bool:
    return (
        isinstance(event, dict)
        and bool(str(event.get("event_id") or "").strip())
        and bool(str(event.get("kind") or "").strip())
        and isinstance(event.get("payload"), dict)
    )


def safe_event_for_storage(event: dict[str, Any], *, occurred_at: str) -> dict[str, Any]:
    return {
        "event_id": str(event.get("event_id") or ""),
        "kind": str(event.get("kind") or ""),
        "schema_version": str(event.get("schema_version") or "unknown"),
        "occurred_at": str(event.get("occurred_at") or occurred_at),
        "source": event.get("source") if isinstance(event.get("source"), dict) else {},
        "confirmation": event.get("confirmation") if isinstance(event.get("confirmation"), dict) else {},
        "payload": event.get("payload") if isinstance(event.get("payload"), dict) else {},
        "evidence": event.get("evidence") if isinstance(event.get("evidence"), list) else [],
    }


def hard_projection_error(code: str) -> bool:
    return code in {"asset_owner_conflict", "invalid_state_transition", "state_conflict"}
