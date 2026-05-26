"""Agent protocol command adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from ai_workroot.protocol import controller
from ai_workroot.protocol.directives import directive
from ai_workroot.protocol.model import PROTOCOL_VERSION, SYNC_REASONS


SYNC_REASON_CHOICES = sorted(SYNC_REASONS)


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
    cwd: Path,
    query: str,
    reason: str,
    workroot_id: Optional[str] = None,
    known_state: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "agent": {"name": agent_name, "transport": "cli"},
        "cwd": str(cwd),
        "reason": reason,
        "query": query,
        "known_state": known_state or {},
    }
    if workroot_id:
        request["workroot_id"] = workroot_id
    return controller.sync(request)


def run_commit_request(request_path: Path) -> dict[str, Any]:
    return controller.commit(_read_json_object(request_path))


def invalid_exchange_action() -> dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": "invalid_exchange_action",
            "message": "invalid_exchange_action",
            "details": {},
        },
        "directive": directive("resync_required", next_action="Use action=sync or action=commit."),
        "warnings": [],
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("request file must contain a JSON object")
    return data
