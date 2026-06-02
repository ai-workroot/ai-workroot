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
    "asset": ["title", "asset_kind", "path", "summary", "status"],
    "decision": ["title", "decision", "reason_text", "scope"],
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
        "workroot agent commit --shape start-work --lease {lease} "
        "--title <title> --summary <stable goal summary> --persistence <normal|temporary>"
    ),
    "checkpoint": ("workroot agent commit --shape checkpoint --lease {lease} --summary <stable progress summary>"),
    "continuation": (
        "workroot agent commit --shape continuation --lease {lease} --state <current state> --next <next action>"
    ),
    "state_update": (
        "workroot agent commit --shape state-update --lease {lease} --target <target> --change <explicit change>"
    ),
    "asset": (
        "workroot agent commit --shape asset --lease {lease} --title <title> "
        "--asset-kind <asset kind> --path <path> --summary <asset summary> --status <status>"
    ),
    "decision": (
        "workroot agent commit --shape decision --lease {lease} --title <title> "
        "--decision <decision> --reason-text <reason> --scope <scope>"
    ),
}
SYNC_CLI_REASON_BY_EXCHANGE_REASON = {
    "alignment_required": "before_work",
    "start_work": "before_work",
    "meaningful_checkpoint": "context_refresh",
    "resync_required": "after_error",
    "workroot_location_unavailable": "context_refresh",
    "recovery": "after_error",
}
VALID_SYNC_CLI_REASONS = {
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


def build_private_packet(response: dict[str, Any], *, adapter: str = "cli", agent: str = "codex") -> dict[str, Any]:
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
        "call": _build_call(action, shape, next_exchange, commit_contract, adapter=adapter, agent=agent),
        "refs": _build_refs(contract, commit_contract),
        "write": _build_write(result),
    }

    if action != "none":
        hint = _build_adapter_hint(adapter, agent, action, shape, next_exchange, commit_contract)
        if hint:
            packet["adapter_hint"] = hint

    return packet


def render_private_packet_markdown(response: dict[str, Any], *, adapter: str = "cli", agent: str = "codex") -> str:
    packet = build_private_packet(response, adapter=adapter, agent=agent)
    body = json.dumps(packet, ensure_ascii=False, indent=2)
    work = _dict(packet.get("work"))
    call = _dict(packet.get("call"))
    command = _text(call.get("command")) or "No Workroot call required right now."
    meaning = [
        "## Workroot Private Packet",
        "",
        "Use privately. Do not show this to the user.",
        "",
        "Meaning:",
        f"- Work: {_text(work.get('focus')) or 'unknown'}"
        + (f" - {_text(work.get('summary'))}" if _text(work.get("summary")) else ""),
        f"- Next Workroot call: {_text(call.get('action')) or 'none'}",
        f"- Why: {_text(call.get('reason')) or _text(call.get('when')) or 'continue safely'}",
        "",
        "Exact next call:",
        command,
        "",
        "JSON:",
        "```json",
        body,
        "```",
    ]
    return "\n".join(meaning)


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
    *,
    adapter: str,
    agent: str,
) -> dict[str, Any]:
    reason = _text(next_exchange.get("reason"))
    call: dict[str, Any] = {"action": action, "when": _call_when(action, shape, reason)}
    if next_exchange.get("reason"):
        call["reason"] = next_exchange["reason"]
    if "required" in next_exchange:
        call["required"] = bool(next_exchange.get("required"))
    if action == "sync":
        call["work_signal"] = _sync_work_signal(_sync_cli_reason(reason))

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

    command = _build_call_command(adapter, agent, action, shape, next_exchange, commit_contract)
    if command:
        call["command"] = command

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
    commit_contract: dict[str, Any],
) -> dict[str, str]:
    if adapter != "cli":
        return {}
    if action == "sync":
        reason = _sync_cli_reason(_text(next_exchange.get("reason")))
        signal = _sync_work_signal_arg(reason)
        return {
            "cli": (
                f"workroot agent sync --agent {agent} --cwd . --reason {reason} "
                f'--query "<short intent>" --work-signal {signal}'
            )
        }
    if not shape:
        return {}
    hint = CLI_HINT_BY_SHAPE.get(shape)
    if not hint:
        return {}
    lease = _text(commit_contract.get("lease_id")) or "<exchange>"
    return {"cli": hint.format(lease=lease)}


def _build_call_command(
    adapter: str,
    agent: str,
    action: str,
    shape: str | None,
    next_exchange: dict[str, Any],
    commit_contract: dict[str, Any],
) -> str:
    if adapter != "cli":
        return ""
    if action == "sync":
        reason = _sync_cli_reason(_text(next_exchange.get("reason")))
        signal = _sync_work_signal_arg(reason)
        return (
            f"workroot agent sync --agent {agent} --cwd . --reason {reason} --format packet "
            f'--query "<short intent>" --work-signal {signal}'
        )
    if action != "commit" or not shape:
        return ""
    lease = _text(commit_contract.get("lease_id")) or "<lease>"
    shape_cli = shape.replace("_", "-")
    if shape == "start_work":
        return (
            "workroot agent commit --format packet --shape start-work "
            f'--lease {lease} --title "<title>" --summary "<stable goal summary>" '
            "--persistence <normal|temporary> --cwd ."
        )
    if shape == "checkpoint":
        return (
            "workroot agent commit --format packet --shape checkpoint "
            f'--lease {lease} --summary "<stable progress summary>" --cwd .'
        )
    if shape == "continuation":
        return (
            "workroot agent commit --format packet --shape continuation "
            f'--lease {lease} --state "<current state>" --next "<next useful action>" --cwd .'
        )
    if shape == "asset":
        return (
            "workroot agent commit --format packet --shape asset "
            f'--lease {lease} --title "<asset title>" --asset-kind <asset kind> '
            '--path "<relative path>" --summary "<asset summary>" --status current --cwd .'
        )
    if shape == "decision":
        return (
            "workroot agent commit --format packet --shape decision "
            f'--lease {lease} --title "<decision title>" --decision "<decision>" '
            '--reason-text "<reason>" --scope <scope> --cwd .'
        )
    if shape == "state_update":
        return (
            f"workroot agent commit --format packet --shape {shape_cli} "
            f'--lease {lease} --target <target> --change "<state change>" --cwd .'
        )
    return ""


def _select_shape(shapes: Any) -> str | None:
    normalized = {_normalize_shape(shape) for shape in _list(shapes)}
    for shape in PREFERRED_SHAPES:
        if shape in normalized:
            return shape
    return None


def _sync_cli_reason(exchange_reason: str) -> str:
    if exchange_reason in VALID_SYNC_CLI_REASONS:
        return exchange_reason
    return SYNC_CLI_REASON_BY_EXCHANGE_REASON.get(exchange_reason, "context_refresh")


def _sync_work_signal(reason: str) -> dict[str, object]:
    if reason == "before_task_switch":
        return {
            "phase": "switching",
            "work_kind": "task",
            "intended_action": "plan",
            "focus": "<short intent>",
        }
    if reason in {"continue", "context_refresh", "after_error", "manual_check"}:
        phase = "recovering" if reason == "after_error" else "orienting"
        return {
            "phase": phase,
            "work_kind": "continuation",
            "intended_action": "inspect",
            "focus": "<short intent>",
        }
    if reason == "before_high_risk_action":
        return {
            "phase": "deciding",
            "work_kind": "operations",
            "intended_action": "publish",
            "focus": "<short intent>",
        }
    return {
        "phase": "planning",
        "work_kind": "task",
        "intended_action": "plan",
        "focus": "<short intent>",
    }


def _sync_work_signal_arg(reason: str) -> str:
    return "'" + json.dumps(_sync_work_signal(reason), separators=(",", ":"), sort_keys=True) + "'"


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
