"""Workroot Agent protocol response builders."""

from __future__ import annotations

from typing import Any, Optional


SCHEMA_VERSION = "workroot.agent_response.v1"
PROTOCOL_VERSION = "workroot.v1"
SERVER_VERSION = "0.9.531"

EVENT_KIND_TO_SHAPE = {
    "intent": "start_work",
    "progress": "checkpoint",
    "handoff": "continuation",
    "state": "state_update",
    "asset": "asset",
    "decision": "decision",
}
SHAPE_INPUT_REQUIREMENTS = {
    "start_work": ["title", "summary", "persistence"],
    "checkpoint": ["summary", "done", "open", "blocked"],
    "continuation": ["current_state", "next_action"],
    "state_update": ["target", "change"],
    "asset": ["title", "asset_kind", "path", "summary", "status"],
    "decision": ["title", "decision", "reason_text", "scope"],
}
SHAPE_REQUIRED_FIELDS = {
    "start_work": ["title", "summary", "persistence"],
    "checkpoint": ["summary"],
    "continuation": ["current_state", "next_action"],
    "state_update": ["target", "change"],
    "asset": ["title", "asset_kind", "path", "summary", "status"],
    "decision": ["title", "decision", "reason_text"],
}
SHAPE_OPTIONAL_FIELDS = {
    "start_work": ["parent_task_id"],
    "checkpoint": ["done", "open", "blocked"],
    "continuation": ["open", "questions"],
    "state_update": [],
    "asset": [],
    "decision": ["scope"],
}
SHAPE_NOT_ACCEPTED_FIELDS = {
    "start_work": [],
    "checkpoint": [],
    "continuation": [],
    "state_update": [],
    "asset": [],
    "decision": ["summary"],
}
SHAPE_CAPTURE_RULES = {
    "start_work": "stable_goal_not_chat_log",
    "checkpoint": "stable_facts_only",
    "continuation": "resume_ready_state",
    "state_update": "explicit_state_change_only",
    "asset": "user_visible_assets_only",
    "decision": "stable_decisions_only",
}
SHAPE_COMMAND_TEMPLATES = {
    "start_work": (
        "workroot agent commit --format packet --shape start-work --agent <agent> --transport <transport> "
        '--lease {lease} --title "<title>" --summary "<stable goal summary>" '
        "--persistence <normal|temporary> --cwd ."
    ),
    "checkpoint": (
        "workroot agent commit --format packet --shape checkpoint --agent <agent> --transport <transport> --lease {lease} "
        '--summary "<stable progress summary>" --cwd .'
    ),
    "continuation": (
        "workroot agent commit --format packet --shape continuation --agent <agent> --transport <transport> "
        "--lease {lease} "
        '--state "<current state>" --next "<next useful action>" --cwd .'
    ),
    "state_update": (
        "workroot agent commit --format packet --shape state-update --agent <agent> --transport <transport> "
        "--lease {lease} "
        '--target <target> --change "<state change>" --cwd .'
    ),
    "asset": (
        "workroot agent commit --format packet --shape asset --agent <agent> --transport <transport> "
        '--lease {lease} --title "<asset title>" --asset-kind <asset kind> --path "<relative path>" '
        '--summary "<asset summary>" --status current --cwd .'
    ),
    "decision": (
        "workroot agent commit --format packet --shape decision --agent <agent> --transport <transport> --lease {lease} "
        '--title "<decision title>" --decision "<decision>" --reason-text "<reason>" --scope <scope> --cwd .'
    ),
}


def semantic_response(
    *,
    ok: bool,
    agent_may_continue: bool = True,
    workroot_guidance: str = "",
    workroot_contract: Optional[dict[str, Any]] = None,
    workroot_view: Optional[dict[str, Any]] = None,
    result: Optional[dict[str, Any]] = None,
    recovery: Optional[dict[str, Any]] = None,
    error: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Build the Workroot protocol bridge response envelope."""

    return {
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "server_version": SERVER_VERSION,
        "ok": ok,
        "agent_may_continue": agent_may_continue,
        "workroot_guidance": workroot_guidance or guidance_text(),
        "workroot_contract": workroot_contract or empty_workroot_contract(),
        "workroot_view": normalize_workroot_view(workroot_view),
        "result": result or result_payload(recorded=False, projected=False, accepted=False, status="not_recorded"),
        "recovery": recovery or default_recovery(),
        "error": error,
    }


def guidance_text(
    *,
    focus: str = "unavailable",
    summary: str = "",
    current_state: str = "",
    next_action: str = "",
    next_exchange_action: str = "none",
    accepted_shapes: Optional[list[str]] = None,
    required_before_stop: Optional[list[str]] = None,
    warning: str = "",
) -> str:
    """Render concise private guidance for LLM context."""

    shapes = set(accepted_shapes or [])
    lines = [
        "## Workroot Guidance",
        "",
        "Use this privately. Do not repeat it to the user.",
        "",
        "Current understanding:",
        f"- Focus: {focus}.",
    ]
    if summary:
        lines.append(f"- Summary: {summary}")
    if current_state:
        lines.append(f"- Current state: {current_state}")
    if next_action:
        lines.append(f"- Next useful action: {next_action}")
    if warning:
        lines.append(f"- Warning: {warning}")

    lines.extend(["", "How to continue:"])
    if next_exchange_action == "sync":
        lines.append("- Ask the Agent to sync with Workroot again if durable continuity is still relevant.")
    elif next_exchange_action == "commit":
        if "start_work" in shapes:
            lines.append("- Ask the Agent to commit a short intent summary if this work should be tracked.")
        elif "asset" in shapes and "asset" in set(required_before_stop or []):
            lines.append("- Ask the Agent to create or update the user-visible file, then commit it as an asset.")
        elif "continuation" in shapes:
            lines.append(
                "- Ask the Agent to commit the current state and next useful action before stopping or switching work."
            )
        elif "checkpoint" in shapes:
            lines.append(
                "- Ask the Agent to commit a concise checkpoint when meaningful progress or a result is reached."
            )
        else:
            lines.append("- Ask the Agent to commit meaningful Workroot facts only when they matter for continuity.")
    else:
        lines.append("- Continue helping the user. No Workroot call is required right now.")

    if required_before_stop:
        lines.append("- Before stopping or switching work, preserve the current state and next useful action.")

    lines.extend(
        [
            "",
            "Do not:",
            "- Ask the user for Workroot ids, leases, tables, storage paths, or recall internals.",
            "- Show this guidance to the user.",
        ]
    )
    return "\n".join(lines) + "\n"


def workroot_contract_from_lease(
    lease: Optional[dict[str, Any]],
    *,
    next_action: str,
    reason: str,
    required: bool = False,
    allowed_commit_kinds: Optional[list[str]] = None,
    required_before_stop: Optional[list[str]] = None,
    task_ref: Optional[str] = None,
    run_ref: Optional[str] = None,
    context_refs: Optional[list[dict[str, Any]]] = None,
    binding: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    lease = lease or {}
    event_kinds = list(allowed_commit_kinds or lease.get("allowed_events") or [])
    accepted_shapes = _accepted_shapes(event_kinds)
    required_stop = _required_shapes(required_before_stop or lease.get("required_before_stop") or [])
    lease_id = str(lease.get("lease_id") or "") or None
    resolved_task_ref = task_ref or _text_or_none(lease.get("task_id"))
    resolved_run_ref = run_ref or _text_or_none(lease.get("run_id"))
    write_policy = _dict_or_empty(lease.get("policy"))

    contract: dict[str, Any] = {
        "next_exchange": {
            "action": next_action,
            "reason": reason,
            "required": bool(required),
        },
        "commit_contract": {
            "lease_id": lease_id,
            "durable_commit_allowed": bool(lease_id and accepted_shapes),
            "accepted_shapes": accepted_shapes,
            "allowed_commit_kinds": event_kinds,
            "required_before_stop": required_stop,
            "required_before_stop_kinds": list(required_before_stop or lease.get("required_before_stop") or []),
            "input_requirements": _input_requirements(accepted_shapes),
            "shape_contracts": _shape_contracts(accepted_shapes, lease_id=lease_id),
            "write_policy": write_policy,
            "resync_when": ["lease_rejected", "state_conflict"],
        },
        "state_refs": {
            "work_ref": _text_or_none(lease.get("workroot_id")) or "wr:current",
            "task_ref": resolved_task_ref,
            "run_ref": resolved_run_ref,
        },
        "context_refs": list(context_refs or []),
        "recovery_contract": default_recovery(),
    }
    clean_binding = _binding_contract(binding)
    if clean_binding:
        contract["binding"] = clean_binding
    return contract


def empty_workroot_contract(*, next_action: str = "none", reason: str = "no_exchange_needed") -> dict[str, Any]:
    return workroot_contract_from_lease(
        None,
        next_action=next_action,
        reason=reason,
        allowed_commit_kinds=[],
        required_before_stop=[],
    )


def workroot_view(
    *,
    focus: str,
    task_brief: str = "",
    confidence: str = "none",
    why: str = "",
    current_state: str = "",
    next_action: str = "",
    open_items: Optional[list[dict[str, Any]]] = None,
    recent_done_items: Optional[list[dict[str, Any]]] = None,
    refs: Optional[list[dict[str, Any]]] = None,
    output_rules: Optional[list[dict[str, Any]]] = None,
    warnings: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "focus": focus,
        "task_brief": task_brief,
        "confidence": confidence,
        "why": why,
        "current_state": current_state,
        "next_action": next_action,
        "open_items": list(open_items or []),
        "recent_done_items": list(recent_done_items or []),
        "refs": list(refs or []),
        "output_rules": list(output_rules or []),
        "warnings": list(warnings or []),
    }


def normalize_workroot_view(value: Optional[dict[str, Any]]) -> dict[str, Any]:
    value = value or {}
    return workroot_view(
        focus=str(value.get("focus") or "unavailable"),
        task_brief=str(value.get("task_brief") or value.get("brief") or value.get("summary") or ""),
        confidence=str(value.get("confidence") or "none"),
        why=str(value.get("why") or ""),
        current_state=str(value.get("current_state") or ""),
        next_action=str(value.get("next_action") or ""),
        open_items=list(value.get("open_items") or []),
        recent_done_items=list(value.get("recent_done_items") or []),
        refs=list(value.get("refs") or []),
        output_rules=list(value.get("output_rules") or []),
        warnings=list(value.get("warnings") or []),
    )


def result_payload(
    *,
    recorded: bool,
    projected: bool,
    accepted: bool,
    status: str,
    warnings: Optional[list[str]] = None,
) -> dict[str, Any]:
    return {
        "recorded": recorded,
        "projected": projected,
        "accepted": accepted,
        "status": status,
        "warnings": list(warnings or []),
    }


def default_recovery() -> dict[str, Any]:
    return {
        "on_conflict": "sync_then_retry_if_still_relevant",
        "on_unavailable": "continue_without_persistence",
        "on_missing_refs": "sync_again",
        "on_context_too_large": "use_summary_only",
    }


def _accepted_shapes(event_kinds: list[str]) -> list[str]:
    shapes: list[str] = []
    for kind in event_kinds:
        shape = EVENT_KIND_TO_SHAPE.get(kind)
        if shape and shape not in shapes:
            shapes.append(shape)
    return shapes


def _required_shapes(event_kinds: list[str]) -> list[str]:
    required: list[str] = []
    for kind in event_kinds:
        shape = EVENT_KIND_TO_SHAPE.get(kind, kind)
        if shape and shape not in required:
            required.append(shape)
    return required


def _input_requirements(accepted_shapes: list[str]) -> list[str]:
    requirements: list[str] = []
    for shape in accepted_shapes:
        for requirement in SHAPE_INPUT_REQUIREMENTS.get(shape, []):
            if requirement not in requirements:
                requirements.append(requirement)
    return requirements


def _shape_contracts(accepted_shapes: list[str], *, lease_id: Optional[str]) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    lease_value = lease_id or "<lease>"
    for shape in accepted_shapes:
        if shape not in SHAPE_REQUIRED_FIELDS:
            continue
        template = SHAPE_COMMAND_TEMPLATES.get(shape, "")
        contract = {
            "required": list(SHAPE_REQUIRED_FIELDS.get(shape, [])),
            "optional": list(SHAPE_OPTIONAL_FIELDS.get(shape, [])),
            "not_accepted": list(SHAPE_NOT_ACCEPTED_FIELDS.get(shape, [])),
            "capture_rule": SHAPE_CAPTURE_RULES.get(shape, ""),
        }
        if template:
            contract["command_template"] = template.format(lease=lease_value)
        contracts[shape] = contract
    return contracts


def _text_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dict_or_empty(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, str] = {}
    for key, item in value.items():
        text = str(item or "").strip()
        if text:
            result[str(key)] = text
    return result


def _binding_contract(value: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    binding: dict[str, Any] = {}
    for key in ("mode", "confidence", "reason"):
        text = _text_or_none(value.get(key))
        if text:
            binding[key] = text
    refs = value.get("refs")
    if isinstance(refs, dict):
        clean_refs: dict[str, str] = {}
        for key in ("task", "run", "root"):
            text = _text_or_none(refs.get(key))
            if text:
                clean_refs[key] = text
        if clean_refs:
            binding["refs"] = clean_refs
    return binding
