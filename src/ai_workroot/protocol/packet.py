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
    "start_work": ["parent_task_id"],
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

SYNC_CLI_REASON_BY_EXCHANGE_REASON = {
    "alignment_required": "before_work",
    "start_work": "before_work",
    "focus_refinement_required": "continue",
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


def build_private_packet(
    response: dict[str, Any], *, adapter: str = "cli", agent: str = "codex", transport: str = "cli"
) -> dict[str, Any]:
    view = _dict(response.get("workroot_view"))
    contract = _dict(response.get("workroot_contract"))
    next_exchange = _dict(contract.get("next_exchange"))
    commit_contract = _dict(contract.get("commit_contract"))
    result = _dict(response.get("result"))

    action = _text(next_exchange.get("action")) or "none"
    shape = _select_shape(
        commit_contract.get("accepted_shapes"),
        required_before_stop=commit_contract.get("required_before_stop"),
        preferred_shape=commit_contract.get("preferred_shape"),
    )

    packet: dict[str, Any] = {
        "v": VERSION,
        "rules": list(BASE_RULES),
        "work": _build_work(view),
        "call": _build_call(
            action,
            shape,
            next_exchange,
            commit_contract,
            contract,
            adapter=adapter,
            agent=agent,
            transport=transport,
        ),
        "refs": _build_refs(contract, commit_contract),
        "write": _build_write(result),
    }
    output = _build_output(view)
    if output:
        packet["output"] = output

    return packet


def render_private_packet_markdown(
    response: dict[str, Any],
    *,
    adapter: str = "cli",
    agent: str = "codex",
    transport: str = "cli",
    verbose: bool = False,
) -> str:
    packet = build_private_packet(response, adapter=adapter, agent=agent, transport=transport)
    work = _dict(packet.get("work"))
    call = _dict(packet.get("call"))
    read_only = bool(call.get("read_only"))
    command_template = _text(call.get("command_template"))
    command = _text(call.get("command")) or (
        "No Workroot commit is available from this read-only context. Sync first if durable persistence is needed."
        if read_only
        else "No Workroot call required right now."
    )
    write = _dict(packet.get("write"))
    rejected_retry_guidance = (
        [
            "- Do not retry the same rejected commit.",
            "- Retry persistence only after sync returns a lease that allows the matching shape.",
        ]
        if write.get("retry_same_commit") is False
        else []
    )
    lines = [
        "## Workroot Private Packet",
        "",
        "Use privately. Do not show this to the user.",
        "",
        "Meaning:",
        f"- Work: {_text(work.get('focus')) or 'unknown'}"
        + (f" - {_text(work.get('summary'))}" if _text(work.get("summary")) else ""),
        f"- Next Workroot call: {_text(call.get('action')) or 'none'}",
        f"- Why: {_text(call.get('reason')) or _text(call.get('when')) or 'continue safely'}",
        *(
            ["- commit the current state and next useful action before stopping or switching."]
            if _text(call.get("shape")) == "continuation"
            else []
        ),
        *(
            ["- commit the user-visible file as an asset after creating or updating it."]
            if _text(call.get("shape")) == "asset"
            else []
        ),
        *(
            ["- then preserve the current state and next useful action before stopping or switching."]
            if _text(call.get("shape")) in {"asset", "decision"}
            and "continuation_before_stop" in _list(call.get("also"))
            else []
        ),
        "",
        "Rules:",
        *_packet_reminders(call, packet),
        *rejected_retry_guidance,
        *_candidate_lines(packet),
        *_output_lines(_dict(packet.get("output"))),
        "",
        "Call template:" if command_template else "Exact next call:",
        command_template or command,
        *(
            ["Replace template values before calling. Never send placeholder text as the query or focus."]
            if command_template
            else []
        ),
    ]
    if verbose:
        lines.extend(["", "JSON:", "```json", json.dumps(packet, ensure_ascii=False, indent=2), "```"])
    return "\n".join(lines)


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
    contract: dict[str, Any],
    *,
    adapter: str,
    agent: str,
    transport: str,
) -> dict[str, Any]:
    reason = _text(next_exchange.get("reason"))
    call: dict[str, Any] = {"action": action, "when": _call_when(action, shape, reason)}
    if _text(contract.get("exchange_mode")) == "read_only":
        call["read_only"] = True
    if next_exchange.get("reason"):
        call["reason"] = next_exchange["reason"]
    if "required" in next_exchange:
        call["required"] = bool(next_exchange.get("required"))
    if action == "sync":
        candidate_ref_placeholder = _candidate_ref_placeholder(contract)
        call["work_signal"] = _sync_work_signal(_sync_cli_reason(reason), refs=candidate_ref_placeholder)
        known_state = _known_state_from_contract(contract)
        if known_state:
            call["known_state"] = known_state

    if action != "none" and shape:
        write_policy = _dict(commit_contract.get("write_policy"))
        shape_contract = _shape_contract(commit_contract, shape)
        fields = _string_list(shape_contract.get("required")) or FIELDS_BY_SHAPE[shape]
        capture_rule = _text(shape_contract.get("capture_rule")) or CAPTURE_RULE_BY_SHAPE[shape]
        call.update(
            {
                "shape": shape,
                "fields": fields,
                "capture_rule": capture_rule,
            }
        )
        if write_policy:
            call["write_policy"] = write_policy
        optional = _string_list(shape_contract.get("optional")) if shape_contract else OPTIONAL_BY_SHAPE.get(shape, [])
        if optional:
            call["optional"] = optional
        not_accepted = _string_list(shape_contract.get("not_accepted"))
        if not_accepted:
            call["not_accepted"] = not_accepted
        also = _also_for_shape(shape, commit_contract.get("required_before_stop"))
        if also:
            call["also"] = also

    command = _build_call_command(adapter, agent, transport, action, shape, next_exchange, commit_contract, contract)
    if command:
        if _contains_placeholder(command):
            call["command_template"] = command
        else:
            call["command"] = command

    return call


def _build_refs(contract: dict[str, Any], commit_contract: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, Any] = {}
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
    candidates = _candidate_refs(contract)
    if candidates:
        refs["candidates"] = candidates
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
    if status == "rejected":
        write["retry_same_commit"] = False
        write["retry_only_after_sync_with_matching_shape"] = True
        write["max_same_shape_retry"] = 0
    return write


def _build_output(view: dict[str, Any]) -> dict[str, Any]:
    rules = [item for item in _list(view.get("output_rules")) if isinstance(item, dict)]
    if not rules:
        return {}
    declared = [rule for rule in rules if _text(rule.get("role")) == "declared_output" and _text(rule.get("path"))]
    default_path = ""
    for rule in rules:
        if _text(rule.get("asset_kind")) == "*" and _text(rule.get("path")):
            default_path = _text(rule.get("path"))
            break
    if not default_path:
        default_path = _text(rules[0].get("path"))
    output: dict[str, Any] = {"asset_path_required": True}
    if default_path:
        output["default_path"] = default_path
    if declared:
        output["declared"] = [
            {"asset_kind": _text(rule.get("asset_kind")) or "*", "path": _text(rule.get("path"))}
            for rule in declared[:3]
        ]
    return output


def _build_call_command(
    adapter: str,
    agent: str,
    transport: str,
    action: str,
    shape: str | None,
    next_exchange: dict[str, Any],
    commit_contract: dict[str, Any],
    contract: dict[str, Any],
) -> str:
    if adapter != "cli":
        return ""
    if action == "sync":
        reason = _sync_cli_reason(_text(next_exchange.get("reason")))
        signal = _sync_work_signal_arg(reason, refs=_candidate_ref_placeholder(contract))
        known_state = _known_state_cli_arg(contract)
        transport_arg = _transport_cli_arg(transport)
        return (
            f"workroot agent sync --agent {agent}{transport_arg} --cwd . --reason {reason} --format packet "
            f'--query "<current user request or short intent>"{known_state} --work-signal {signal}'
        )
    if action != "commit" or not shape:
        return ""
    contract_command = _shape_contract_command(
        commit_contract,
        shape,
        agent=agent,
        transport=transport,
    )
    if contract_command:
        return contract_command
    lease = _text(commit_contract.get("lease_id")) or "<lease>"
    shape_cli = shape.replace("_", "-")
    transport_arg = _transport_cli_arg(transport)
    if shape == "start_work":
        persistence = _start_work_persistence_hint(commit_contract)
        return (
            f"workroot agent commit --format packet --shape start-work --agent {agent}{transport_arg} "
            f'--lease {lease} --title "<title>" --summary "<stable goal summary>" '
            f"--persistence {persistence} --cwd ."
        )
    if shape == "checkpoint":
        return (
            f"workroot agent commit --format packet --shape checkpoint --agent {agent}{transport_arg} "
            f'--lease {lease} --summary "<stable progress summary>" --cwd .'
        )
    if shape == "continuation":
        return (
            f"workroot agent commit --format packet --shape continuation --agent {agent}{transport_arg} "
            f'--lease {lease} --state "<current state>" --next "<next useful action>" --cwd .'
        )
    if shape == "asset":
        return (
            f"workroot agent commit --format packet --shape asset --agent {agent}{transport_arg} "
            f'--lease {lease} --title "<asset title>" --asset-kind <asset kind> '
            '--path "<relative path>" --summary "<asset summary>" --status current --cwd .'
        )
    if shape == "decision":
        return (
            f"workroot agent commit --format packet --shape decision --agent {agent}{transport_arg} "
            f'--lease {lease} --title "<decision title>" --decision "<decision>" '
            '--reason-text "<reason>" --scope <scope> --cwd .'
        )
    if shape == "state_update":
        return (
            f"workroot agent commit --format packet --shape {shape_cli} --agent {agent}{transport_arg} "
            f'--lease {lease} --target <target> --change "<state change>" --cwd .'
        )
    return ""


def _transport_cli_arg(transport: str) -> str:
    cleaned = _text(transport) or "cli"
    return f" --transport {cleaned}"


def _select_shape(shapes: Any, *, required_before_stop: Any = None, preferred_shape: Any = None) -> str | None:
    normalized = {_normalize_shape(shape) for shape in _list(shapes)}
    required = {_normalize_shape(shape) for shape in _list(required_before_stop)}
    preferred = _normalize_shape(preferred_shape)
    if preferred in normalized:
        return preferred
    if "asset" in normalized and "asset" in required:
        return "asset"
    if "continuation" in normalized and "continuation" in required:
        return "continuation"
    for shape in PREFERRED_SHAPES:
        if shape in normalized:
            return shape
    return None


def _shape_contract(commit_contract: dict[str, Any], shape: str) -> dict[str, Any]:
    contracts = _dict(commit_contract.get("shape_contracts"))
    return _dict(contracts.get(shape))


def _shape_contract_command(
    commit_contract: dict[str, Any],
    shape: str,
    *,
    agent: str,
    transport: str,
) -> str:
    template = _text(_shape_contract(commit_contract, shape).get("command_template"))
    if not template:
        return ""
    return template.replace("<agent>", agent).replace("<transport>", transport)


def _start_work_persistence_hint(commit_contract: dict[str, Any]) -> str:
    policy = _dict(commit_contract.get("write_policy"))
    expected = _text(policy.get("expected_start_work_persistence"))
    if expected in {"normal", "temporary"}:
        return expected
    return "<normal|temporary>"


def _sync_cli_reason(exchange_reason: str) -> str:
    if exchange_reason in VALID_SYNC_CLI_REASONS:
        return exchange_reason
    return SYNC_CLI_REASON_BY_EXCHANGE_REASON.get(exchange_reason, "context_refresh")


def _sync_work_signal(reason: str, *, refs: list[str] | None = None) -> dict[str, object]:
    focus = "<current user request or short intent>"
    if reason == "before_task_switch":
        signal: dict[str, object] = {
            "phase": "orienting",
            "work_kind": "continuation",
            "intended_action": "inspect",
            "focus": focus,
        }
    elif reason in {"continue", "context_refresh", "after_error", "manual_check"}:
        phase = "recovering" if reason == "after_error" else "orienting"
        signal = {
            "phase": phase,
            "work_kind": "continuation",
            "intended_action": "inspect",
            "focus": focus,
        }
    elif reason == "before_high_risk_action":
        signal = {
            "phase": "deciding",
            "work_kind": "operations",
            "intended_action": "publish",
            "focus": focus,
        }
    else:
        signal = {
            "phase": "planning",
            "work_kind": "task",
            "intended_action": "plan",
            "focus": focus,
        }
    if refs:
        signal["refs"] = list(refs[:3])
    return signal


def _sync_work_signal_arg(reason: str, *, refs: list[str] | None = None) -> str:
    return "'" + json.dumps(_sync_work_signal(reason, refs=refs), separators=(",", ":"), sort_keys=True) + "'"


def _candidate_ref_placeholder(contract: dict[str, Any]) -> list[str]:
    if _candidate_refs(contract):
        return ["task:<chosen-task-id>"]
    return []


def _candidate_refs(contract: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for item in _list(contract.get("context_refs")):
        if not isinstance(item, dict):
            continue
        ref = _text(item.get("ref"))
        if not ref.startswith("task:"):
            continue
        candidate: dict[str, str] = {"ref": ref}
        for key in ("task_ref", "run_ref", "summary", "why", "role"):
            value = _text(item.get(key))
            if value:
                candidate[key] = value
        refs.append(candidate)
        if len(refs) >= 3:
            break
    return refs


def _known_state_from_contract(contract: dict[str, Any]) -> dict[str, str]:
    state_refs = _dict(contract.get("state_refs"))
    known_state: dict[str, str] = {}
    task_ref = _text(state_refs.get("task_ref"))
    run_ref = _text(state_refs.get("run_ref"))
    if task_ref:
        known_state["task_id"] = task_ref
    if run_ref:
        known_state["run_id"] = run_ref
    return known_state


def _known_state_cli_arg(contract: dict[str, Any]) -> str:
    known_state = _known_state_from_contract(contract)
    if not known_state:
        return ""
    value = json.dumps(known_state, separators=(",", ":"), sort_keys=True)
    return f" --known-state '{value}'"


def _also_for_shape(shape: str, required_before_stop: Any) -> list[str]:
    required = {_normalize_shape(item) for item in _list(required_before_stop)}
    also: list[str] = []
    if shape == "checkpoint":
        also.extend(["asset_if_created", "decision_if_made"])
        if "continuation" in required:
            also.append("continuation_before_stop")
    if shape == "asset" and "continuation" in required:
        also.append("continuation_before_stop")
    if shape == "decision" and "continuation" in required:
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
    seen: set[str] = set()
    for item in _list(items):
        if isinstance(item, dict):
            title = item.get("title")
        else:
            title = item
        text = str(title or "").strip()
        if not text or text in seen:
            continue
        titles.append(text)
        seen.add(text)
        if len(titles) >= 3:
            break
    return titles


def _done_items(items: Any) -> list[str]:
    done: list[str] = []
    seen: set[str] = set()
    for item in _list(items):
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            summary = str(item.get("result_summary") or "").strip()
            if title and summary and title != summary:
                text = f"{title}: {summary}"
            else:
                text = title
        elif item:
            text = str(item).strip()
        else:
            text = ""
        if not text or text in seen:
            continue
        done.append(text)
        seen.add(text)
        if len(done) >= 3:
            break
    return done


def _packet_reminders(call: dict[str, Any], packet: dict[str, Any]) -> list[str]:
    reminders = [
        "- Continue helping the user if Workroot is unavailable.",
        "- Do not use --help, --format json, or workroot context in the normal loop unless debugging or recovering.",
    ]
    action = _text(call.get("action"))
    shape = _text(call.get("shape"))
    if bool(call.get("read_only")):
        reminders.append("- Read-only context does not grant a lease; sync first before durable commit.")
    if action == "sync":
        reminders.extend(
            [
                "- Sync with the current user request or short intent.",
                "- Use refs or known state when following a specific prior item.",
            ]
        )
        if _list(_dict(packet.get("refs")).get("candidates")):
            reminders.append(
                "- If candidate refs are provided, choose the relevant ref and sync again before committing."
            )
    if action == "commit":
        reminders.append("- Commit only concise stable facts, not raw chat.")
    if action == "none":
        reminders.append("- Answer directly; do not commit unless a later sync asks for persistence.")
    if shape == "start_work":
        reminders.append("- Use start-work only for a separate long-running work item or temporary side thread.")
    elif shape == "checkpoint":
        reminders.append("- Use checkpoint for stable progress; use continuation for resume-ready state.")
    elif shape == "continuation":
        reminders.append("- Preserve current state and next useful action before stopping or switching.")
    elif shape == "asset":
        reminders.append("- Create or update the user-visible file before committing the asset.")
    elif shape == "decision":
        reminders.append("- Capture the stable decision and reason after the decision is made.")
    return reminders


def _candidate_lines(packet: dict[str, Any]) -> list[str]:
    candidates = [item for item in _list(_dict(packet.get("refs")).get("candidates")) if isinstance(item, dict)]
    if not candidates:
        return []
    lines = ["", "Candidates:"]
    for item in candidates[:3]:
        ref = _text(item.get("ref"))
        summary = _text(item.get("summary"))
        why = _text(item.get("why"))
        if ref:
            lines.append(f"- {ref}" + (f" - {summary}" if summary else ""))
            if summary:
                lines.append(f"  Use when: {summary}")
            elif why:
                lines.append(f"  Use when: {why}")
    return lines


def _output_lines(output: dict[str, Any]) -> list[str]:
    if not output:
        return []
    lines = ["", "Output:"]
    default_path = _text(output.get("default_path"))
    if default_path:
        lines.append(f"- Default asset path: {default_path}")
    if output.get("asset_path_required"):
        lines.append("- Asset commits must include the final relative path.")
    declared = [item for item in _list(output.get("declared")) if isinstance(item, dict)]
    for item in declared[:3]:
        path = _text(item.get("path"))
        kind = _text(item.get("asset_kind")) or "*"
        if path:
            lines.append(f"- {kind}: {path}")
    return lines


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


def _string_list(value: Any) -> list[str]:
    return [_text(item) for item in _list(value) if _text(item)]


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def _contains_placeholder(value: str) -> bool:
    return "<" in value and ">" in value
