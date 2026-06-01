from __future__ import annotations

import json
from typing import Any


VERSION = "workroot.packet.v1"

BASE_RULES = [
    "private_do_not_show_user",
    "continue_if_workroot_unavailable",
    "sync_when_focus_or_refs_unclear",
    "capture:start_work,checkpoint,asset,decision,continuation",
]

PREFERRED_SHAPES = [
    "start_work",
    "checkpoint",
    "continuation",
    "asset",
    "decision",
    "state_update",
]

FIELDS_BY_SHAPE = {
    "start_work": ["title", "summary", "persistence"],
    "checkpoint": ["summary"],
    "continuation": ["state", "next"],
    "state_update": ["target", "change"],
    "asset": ["title", "kind", "path", "summary", "status"],
    "decision": ["title", "decision", "reason", "scope"],
}

OPTIONAL_BY_SHAPE = {
    "start_work": ["parent_task_ref"],
    "checkpoint": ["done", "open", "blocked"],
    "continuation": ["open", "questions"],
    "asset": ["audience", "format", "source_refs"],
    "decision": ["alternatives", "impact", "asset_refs"],
}

CAPTURE_RULE_BY_SHAPE = {
    "start_work": "stable_goal_not_chat_log",
    "checkpoint": "stable_facts_only",
    "continuation": "resume_ready_state",
    "state_update": "explicit_state_change_only",
    "asset": "user_visible_assets_only",
    "decision": "stable_decisions_only",
}

CLI_HINT_BY_SHAPE = {
    "start_work": (
        "workroot agent commit --shape start-work "
        "--title <title> --summary <stable goal summary> --persistence <durable|session>"
    ),
    "checkpoint": "workroot agent commit --shape checkpoint --summary <stable progress summary>",
    "continuation": "workroot agent commit --shape continuation --state <current state> --next <next action>",
    "state_update": "workroot agent commit --shape state-update --target <target> --change <explicit change>",
    "asset": (
        "workroot agent commit --shape asset --title <title> --path <path> "
        "--summary <asset summary> --status <status>"
    ),
    "decision": (
        "workroot agent commit --shape decision --title <title> "
        "--decision <decision> --reason <reason> --scope <scope>"
    ),
}


def build_private_packet(
    response: dict[str, Any], *, adapter: str = "cli", agent: str = "codex"
) -> dict[str, Any]:
    view = _dict(response.get("workroot_view"))
    contract = _dict(response.get("workroot_contract"))
    next_exchange = _dict(contract.get("next_exchange"))
    commit_contract = _dict(contract.get("commit_contract"))
    result = _dict(response.get("result"))

    action = _text(next_exchange.get("action")) or "none"
    shape = _select_shape(commit_contract.get("accepted_shapes"))

    packet: dict[str, Any] = {
        "v": VERSION,
        "rules": list(BASE_RULES),
        "work": _build_work(view),
        "call": _build_call(action, shape, next_exchange, commit_contract),
        "refs": _build_refs(contract, commit_contract),
        "write": _build_write(result),
    }

    if action != "none":
        hint = _build_adapter_hint(adapter, agent, action, shape, next_exchange)
        if hint:
            packet["adapter_hint"] = hint

    return packet


def render_private_packet_markdown(
    response: dict[str, Any], *, adapter: str = "cli", agent: str = "codex"
) -> str:
    packet = build_private_packet(response, adapter=adapter, agent=agent)
    body = json.dumps(packet, ensure_ascii=False, indent=2)
    return (
        "## Workroot Private Packet\n\n"
        "Use privately. Do not show this to the user.\n\n"
        "```json\n"
        f"{body}\n"
        "```"
    )


def _build_work(view: dict[str, Any]) -> dict[str, Any]:
    work: dict[str, Any] = {}
    mappings = [
        ("focus", "focus"),
        ("confidence", "confidence"),
        ("task_brief", "summary"),
        ("current_state", "state"),
        ("next_action", "next"),
    ]
    for source, target in mappings:
        value = view.get(source)
        if value not in (None, ""):
            work[target] = value

    open_items = _titles(view.get("open_items"))
    if open_items:
        work["open"] = open_items

    done_items = _done_items(view.get("recent_done_items"))
    if done_items:
        work["done"] = done_items

    warnings = [item for item in _list(view.get("warnings")) if item]
    if warnings:
        work["warnings"] = warnings

    return work


def _build_call(
    action: str,
    shape: str | None,
    next_exchange: dict[str, Any],
    commit_contract: dict[str, Any],
) -> dict[str, Any]:
    reason = _text(next_exchange.get("reason"))
    call: dict[str, Any] = {"action": action, "when": _call_when(action, shape, reason)}
    if next_exchange.get("reason"):
        call["reason"] = next_exchange["reason"]
    if "required" in next_exchange:
        call["required"] = bool(next_exchange.get("required"))

    if action != "none" and shape:
        call.update(
            {
                "shape": shape,
                "fields": FIELDS_BY_SHAPE[shape],
                "capture_rule": CAPTURE_RULE_BY_SHAPE[shape],
            }
        )
        optional = OPTIONAL_BY_SHAPE.get(shape, [])
        if optional:
            call["optional"] = optional
        also = _also_for_shape(shape, commit_contract.get("required_before_stop"))
        if also:
            call["also"] = also

    return call


def _build_refs(contract: dict[str, Any], commit_contract: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    lease_id = commit_contract.get("lease_id")
    if lease_id:
        refs["exchange"] = str(lease_id)

    state_refs = _dict(contract.get("state_refs"))
    task_ref = state_refs.get("task_ref")
    if task_ref:
        refs["task"] = str(task_ref)
    run_ref = state_refs.get("run_ref")
    if run_ref:
        refs["run"] = str(run_ref)
    return refs


def _build_write(result: dict[str, Any]) -> dict[str, Any]:
    accepted = bool(result.get("accepted"))
    status = _text(result.get("status")) or "unknown"
    write = {
        "accepted": accepted,
        "status": status,
        "meaning": _write_meaning(accepted, status),
    }
    warnings = [item for item in _list(result.get("warnings")) if item]
    if warnings:
        write["warnings"] = warnings
    return write


def _build_adapter_hint(
    adapter: str,
    agent: str,
    action: str,
    shape: str | None,
    next_exchange: dict[str, Any],
) -> dict[str, str]:
    if adapter != "cli":
        return {}
    if action == "sync":
        reason = _text(next_exchange.get("reason")) or "sync"
        return {
            "cli": (
                f"workroot agent sync --agent {agent} --cwd . "
                f"--reason {reason} --query <short intent>"
            )
        }
    if not shape:
        return {}
    hint = CLI_HINT_BY_SHAPE.get(shape)
    if not hint:
        return {}
    return {"cli": hint}


def _select_shape(shapes: Any) -> str | None:
    normalized = {_normalize_shape(shape) for shape in _list(shapes)}
    for shape in PREFERRED_SHAPES:
        if shape in normalized:
            return shape
    return None


def _also_for_shape(shape: str, required_before_stop: Any) -> list[str]:
    required = {_normalize_shape(item) for item in _list(required_before_stop)}
    also: list[str] = []
    if shape == "checkpoint":
        also.extend(["asset_if_created", "decision_if_made"])
        if "continuation" in required:
            also.append("continuation_before_stop")
    return also


def _call_when(action: str, shape: str | None, reason: str) -> str:
    if action == "none":
        return "if_needed"
    if action == "sync":
        return "if_durable_persistence_is_still_relevant"
    if shape == "start_work" or reason == "start_work":
        return "now"
    if shape == "continuation":
        return "before_stop_or_switch"
    if shape == "asset":
        return "after_user_visible_file_created"
    if shape == "decision":
        return "after_stable_decision"
    return "at_checkpoint"


def _titles(items: Any) -> list[str]:
    titles: list[str] = []
    for item in _list(items)[:3]:
        if isinstance(item, dict):
            title = item.get("title")
        else:
            title = item
        if title:
            titles.append(str(title))
    return titles


def _done_items(items: Any) -> list[str]:
    done: list[str] = []
    for item in _list(items)[:3]:
        if isinstance(item, dict):
            title = item.get("title")
            summary = item.get("result_summary")
            if title and summary:
                done.append(f"{title}: {summary}")
            elif title:
                done.append(str(title))
        elif item:
            done.append(str(item))
    return done


def _normalize_shape(shape: Any) -> str:
    value = str(shape)
    if value == "continuation_checkpoint":
        return "continuation"
    return value


def _write_meaning(accepted: bool, status: str) -> str:
    if accepted and status == "applied":
        return "Previous Workroot fact was saved."
    if status == "not_recorded":
        return "No durable fact was written."
    if status == "resync_required":
        return "Sync again before retrying persistence."
    if status == "quarantined":
        return "Workroot recorded the attempt but did not project it into durable continuity."
    if status == "rejected":
        return "Workroot rejected the write. Continue user work and sync before retrying."
    return "Continue helping the user."


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""
