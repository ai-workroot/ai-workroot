"""Protocol event envelope validation and request hashing."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from ai_workroot.protocol.errors import ProtocolError


EVENT_KINDS = {"intent", "progress", "decision", "correction", "asset", "guidance", "handoff", "state"}


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def request_hash(data: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


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
    return event
