"""Workroot Agent Protocol controller."""

from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from ai_workroot.protocol.directives import directive
from ai_workroot.protocol.lease import create_lease
from ai_workroot.protocol.model import SyncRequest
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


def _resolve_workroot(request: SyncRequest) -> dict[str, str]:
    if request.workroot_id:
        for record in list_workroots():
            if record["workrootId"] == request.workroot_id:
                return record
        raise ValueError(f"Workroot not found: {request.workroot_id}")
    if request.cwd:
        return find_workroot_by_cwd(Path(request.cwd))
    raise ValueError("missing Workroot locator")


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
