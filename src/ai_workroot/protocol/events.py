"""Protocol event envelope validation and request hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ai_workroot.protocol.errors import ProtocolError


EVENT_KINDS = {"intent", "progress", "decision", "correction", "asset", "guidance", "handoff", "state"}


def canonical_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def request_hash(data: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def semantic_commit_request(request_data: dict[str, Any], *, workroot_id: str) -> dict[str, Any]:
    return {
        "protocol_version": request_data.get("protocol_version"),
        "action": "commit",
        "workroot_id": workroot_id,
        "exchange_lease_id": request_data.get("exchange_lease_id") or "",
        "atomic_batch": request_data.get("atomic_batch") is not False,
        "events": [_semantic_event_item(index, event) for index, event in enumerate(request_data.get("events") or [])],
    }


def semantic_commit_hash(request_data: dict[str, Any], *, workroot_id: str) -> tuple[str, str]:
    normalized = semantic_commit_request(request_data, workroot_id=workroot_id)
    normalized_json = canonical_json(normalized)
    return "sha256:" + hashlib.sha256(normalized_json.encode("utf-8")).hexdigest(), normalized_json


def validate_event_envelope(event: dict[str, Any]) -> dict[str, Any]:
    required = ("event_id", "kind", "schema_version", "occurred_at", "source", "confirmation", "payload", "evidence")
    for field in required:
        if field not in event:
            raise ProtocolError("invalid_event_schema", f"missing event field: {field}")
    if event["kind"] not in EVENT_KINDS:
        raise ProtocolError("invalid_event_kind", f"invalid event kind: {event['kind']}")
    if not isinstance(event["evidence"], list):
        raise ProtocolError("invalid_event_schema", "evidence must be a list")
    if not isinstance(event["payload"], dict):
        raise ProtocolError("invalid_event_schema", "payload must be an object")
    if event["kind"] == "progress" and any(key in event["payload"] for key in ("done", "open", "blocked")):
        raise ProtocolError("invalid_event_schema", "progress shorthand must be converted before projection")
    return event


def _semantic_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": event.get("kind"),
        "schema_version": event.get("schema_version"),
        "payload": event.get("payload") if isinstance(event.get("payload"), dict) else {},
        "evidence": event.get("evidence") if isinstance(event.get("evidence"), list) else [],
        "confirmation": event.get("confirmation") if isinstance(event.get("confirmation"), dict) else {},
    }


def _semantic_event_item(index: int, event: Any) -> dict[str, Any]:
    if isinstance(event, dict):
        return _semantic_event(event)
    return {
        "invalid": True,
        "index": index,
        "item_type": type(event).__name__,
        "fingerprint": request_hash({"invalid_event_item": event}),
    }
