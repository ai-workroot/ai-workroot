# Workroot Private Packet Protocol Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement `workroot.packet.v1` as the LLM-facing private protocol packet, while keeping `sync` and `commit` as the stable Workroot actions and `commit` as the only durable fact entry.

**Architecture:** Add a focused packet renderer in `ai_workroot.protocol` that maps existing protocol responses into a compact LLM-facing packet. Route `workroot context`, `workroot agent sync`, and `workroot agent commit` through this renderer for model-facing output, then add shape-native commit inputs and protocol projections for Asset and Decision capture using existing storage/query primitives.

**Tech Stack:** Python stdlib, `unittest`, SQLite, existing `ai_workroot.protocol`, `ai_workroot.context`, `ai_workroot.assets`, `ai_workroot.relationships`, and CLI modules.

---

## File Structure

Create:

- `src/ai_workroot/protocol/packet.py`
  - Owns `workroot.packet.v1` construction and Markdown rendering.
  - Depends only on protocol response dictionaries and small constants.
  - Does not import CLI, context builder, or domain operations.

- `tests/unit/test_protocol_packet.py`
  - Unit tests for packet field mapping, compression, adapter hints, and private Markdown output.

- `tests/integration/test_protocol_packet_loop.py`
  - End-to-end protocol loop tests for packet output over sync, start_work, checkpoint, continuation, asset, decision, and degraded cases.

Modify:

- `src/ai_workroot/protocol/response.py`
  - Add Asset and Decision shape mapping.
  - Keep full structured response available for runtime/debug use.

- `src/ai_workroot/protocol/projections.py`
  - Add `asset` and `decision` projections.
  - Extend task-scoped lease allowed events to include `asset` and `decision`.
  - Record query-model hints and relationships without adding new domain entities.

- `src/ai_workroot/commands/agent_exchange.py`
  - Add `packet` output format.
  - Replace LLM-facing shorthand with shape-native commit inputs.

- `src/ai_workroot/cli/main.py`
  - Add `--format packet`.
  - Add `--shape` and shape-specific fields for `agent commit`.

- `src/ai_workroot/context/builder.py`
  - Render startup packet from read-only `startup_context`.
  - Stop duplicating old Workroot guidance text in startup packages once packet output is present.

- `src/ai_workroot/context/control.py`
  - Reduce static guidance to a thin bootstrap instruction if still needed.

- `tests/unit/test_agent_exchange_command.py`
  - Update output-format and shape-native command tests.

- `tests/unit/test_protocol_response_v2.py`
  - Assert full JSON remains available but packet is the LLM-facing render.

- `tests/unit/test_context_wrapper_v2.py`
  - Assert `workroot context` includes the private packet and no internal debug contract.

- `tests/integration/test_agent_protocol_loop.py`
  - Update existing sync/commit loop expectations to shape/packet terminology.

- `tests/e2e/live_protocol.py`
  - Update live prompts to prefer packet/shape hints over internal `--kind` language.

Do not modify:

- Context L1/L2/L3 recall strategy.
- Storage engine choice.
- Task/TaskRun/TaskItem/TaskSummary/Handoff domain shapes beyond what protocol projection already owns.

---

### Task 1: Add Workroot Private Packet Renderer

**Files:**

- Create: `src/ai_workroot/protocol/packet.py`
- Create: `tests/unit/test_protocol_packet.py`

- [ ] **Step 1: Write packet renderer unit tests**

Create `tests/unit/test_protocol_packet.py`:

```python
from __future__ import annotations

import json
import unittest

from ai_workroot.protocol.packet import build_private_packet, render_private_packet_markdown


class ProtocolPacketTest(unittest.TestCase):
    def test_new_work_packet_maps_start_work_call(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "new_work",
                "confidence": "high",
                "task_brief": "Redesign Agent protocol interaction",
                "current_state": "",
                "next_action": "",
                "open_items": [],
                "recent_done_items": [],
                "warnings": [],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "start_work", "required": False},
                "commit_contract": {
                    "lease_id": "lease-1",
                    "accepted_shapes": ["start_work"],
                    "required_before_stop": [],
                },
                "state_refs": {"task_ref": None, "run_ref": None},
                "debug": {"effects": [{"type": "internal", "target_type": "debug", "target_id": "x"}]},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["v"], "workroot.packet.v1")
        self.assertIn("private_do_not_show_user", packet["rules"])
        self.assertEqual(packet["work"]["focus"], "new_work")
        self.assertEqual(packet["work"]["summary"], "Redesign Agent protocol interaction")
        self.assertEqual(packet["call"]["action"], "commit")
        self.assertEqual(packet["call"]["shape"], "start_work")
        self.assertEqual(packet["call"]["fields"], ["title", "summary", "persistence"])
        self.assertEqual(packet["refs"], {"exchange": "lease-1"})
        self.assertEqual(packet["write"]["status"], "not_recorded")
        self.assertIn("--shape start-work", packet["adapter_hint"]["cli"])
        serialized = json.dumps(packet, ensure_ascii=False)
        self.assertNotIn("debug", serialized)
        self.assertNotIn("effects", serialized)

    def test_continuation_packet_limits_open_and_done_items(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {
                "focus": "continuation",
                "confidence": "high",
                "task_brief": "Protocol packet design",
                "current_state": "Core fields agreed.",
                "next_action": "Implement packet renderer.",
                "open_items": [
                    {"title": "Open 1"},
                    {"title": "Open 2"},
                    {"title": "Open 3"},
                    {"title": "Open 4"},
                ],
                "recent_done_items": [
                    {"title": "Done 1", "result_summary": "A"},
                    {"title": "Done 2", "result_summary": "B"},
                    {"title": "Done 3", "result_summary": "C"},
                    {"title": "Done 4", "result_summary": "D"},
                ],
                "warnings": [],
            },
            "workroot_contract": {
                "next_exchange": {"action": "commit", "reason": "meaningful_checkpoint", "required": False},
                "commit_contract": {
                    "lease_id": "lease-2",
                    "accepted_shapes": ["checkpoint", "continuation_checkpoint", "state_update"],
                    "required_before_stop": ["continuation_checkpoint"],
                },
                "state_refs": {"task_ref": "task-1", "run_ref": "run-1"},
            },
            "result": {"accepted": True, "status": "applied", "warnings": []},
        }

        packet = build_private_packet(response, adapter="cli", agent="codex")

        self.assertEqual(packet["work"]["open"], ["Open 1", "Open 2", "Open 3"])
        self.assertEqual(packet["work"]["done"], ["Done 1: A", "Done 2: B", "Done 3: C"])
        self.assertEqual(packet["call"]["shape"], "checkpoint")
        self.assertEqual(packet["call"]["also"], ["asset_if_created", "decision_if_made", "continuation_before_stop"])
        self.assertEqual(packet["refs"], {"exchange": "lease-2", "task": "task-1", "run": "run-1"})

    def test_packet_markdown_is_private_and_contains_json(self) -> None:
        response = {
            "agent_may_continue": True,
            "workroot_view": {"focus": "quick", "confidence": "medium", "task_brief": "Answer a question"},
            "workroot_contract": {
                "next_exchange": {"action": "none", "reason": "no_exchange_needed", "required": False},
                "commit_contract": {"lease_id": None, "accepted_shapes": [], "required_before_stop": []},
                "state_refs": {},
            },
            "result": {"accepted": False, "status": "not_recorded", "warnings": []},
        }

        rendered = render_private_packet_markdown(response, adapter="cli", agent="codex")

        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn("Use privately. Do not show this to the user.", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertIn('"focus": "quick"', rendered)
        self.assertNotIn("adapter_hint", rendered)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run packet tests and verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_packet -q
```

Expected:

```text
FAILED (errors=1)
ModuleNotFoundError: No module named 'ai_workroot.protocol.packet'
```

- [ ] **Step 3: Implement `protocol.packet`**

Create `src/ai_workroot/protocol/packet.py`:

```python
"""LLM-facing Workroot private packet renderer."""

from __future__ import annotations

import json
from typing import Any


PACKET_VERSION = "workroot.packet.v1"
BASE_RULES = [
    "private_do_not_show_user",
    "continue_if_workroot_unavailable",
    "sync_when_focus_or_refs_unclear",
    "capture:start_work,checkpoint,asset,decision,continuation",
]

SHAPE_ALIASES = {
    "continuation_checkpoint": "continuation",
}

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


def build_private_packet(response: dict[str, Any], *, adapter: str = "cli", agent: str = "codex") -> dict[str, Any]:
    view = response.get("workroot_view") if isinstance(response.get("workroot_view"), dict) else {}
    contract = response.get("workroot_contract") if isinstance(response.get("workroot_contract"), dict) else {}
    commit_contract = contract.get("commit_contract") if isinstance(contract.get("commit_contract"), dict) else {}
    next_exchange = contract.get("next_exchange") if isinstance(contract.get("next_exchange"), dict) else {}
    state_refs = contract.get("state_refs") if isinstance(contract.get("state_refs"), dict) else {}
    result = response.get("result") if isinstance(response.get("result"), dict) else {}

    call = _call(next_exchange, commit_contract)
    packet: dict[str, Any] = {
        "v": PACKET_VERSION,
        "rules": _rules_for(call, view),
        "work": _work(view),
        "call": call,
        "refs": _refs(commit_contract, state_refs),
        "write": _write(result),
    }
    adapter_hint = _adapter_hint(call, packet["refs"], adapter=adapter, agent=agent)
    if adapter_hint:
        packet["adapter_hint"] = adapter_hint
    return _drop_empty(packet)


def render_private_packet_markdown(
    response: dict[str, Any],
    *,
    adapter: str = "cli",
    agent: str = "codex",
) -> str:
    packet = build_private_packet(response, adapter=adapter, agent=agent)
    body = json.dumps(packet, ensure_ascii=False, indent=2)
    return (
        "## Workroot Private Packet\n\n"
        "Use privately. Do not show this to the user. Continue helping the user if "
        "Workroot cannot persist; sync again when focus or refs are unclear.\n\n"
        "```json\n"
        f"{body}\n"
        "```\n"
    )


def _rules_for(call: dict[str, Any], view: dict[str, Any]) -> list[str]:
    rules = list(BASE_RULES)
    warnings = view.get("warnings") if isinstance(view.get("warnings"), list) else []
    if call.get("shape") == "asset" or any("asset" in str(warning).lower() for warning in warnings):
        rules.extend(["asset_after_file_exists_only", "user_visible_assets_only"])
    if call.get("shape") == "decision":
        rules.append("stable_decisions_only")
    return rules


def _work(view: dict[str, Any]) -> dict[str, Any]:
    work = {
        "focus": str(view.get("focus") or "unavailable"),
        "confidence": str(view.get("confidence") or "none"),
        "summary": str(view.get("task_brief") or view.get("summary") or ""),
        "state": str(view.get("current_state") or ""),
        "next": str(view.get("next_action") or ""),
        "open": _titles(view.get("open_items"), limit=3),
        "done": _done_titles(view.get("recent_done_items"), limit=3),
        "warnings": [str(item) for item in view.get("warnings") or [] if str(item).strip()],
    }
    return _drop_empty(work)


def _call(next_exchange: dict[str, Any], commit_contract: dict[str, Any]) -> dict[str, Any]:
    action = str(next_exchange.get("action") or "none")
    accepted_shapes = [_shape(str(shape)) for shape in commit_contract.get("accepted_shapes") or []]
    shape = _preferred_shape(action, accepted_shapes)
    call: dict[str, Any] = {
        "action": action,
        "when": _when(action, str(next_exchange.get("reason") or ""), shape),
    }
    if shape:
        call["shape"] = shape
        call["fields"] = list(FIELDS_BY_SHAPE.get(shape, []))
        optional = OPTIONAL_BY_SHAPE.get(shape, [])
        if optional:
            call["optional"] = list(optional)
        if shape == "checkpoint":
            call["also"] = ["asset_if_created", "decision_if_made", "continuation_before_stop"]
        capture_rule = CAPTURE_RULE_BY_SHAPE.get(shape)
        if capture_rule:
            call["capture_rule"] = capture_rule
    return _drop_empty(call)


def _preferred_shape(action: str, accepted_shapes: list[str]) -> str:
    if action != "commit":
        return ""
    for shape in ("start_work", "checkpoint", "continuation", "asset", "decision", "state_update"):
        if shape in accepted_shapes:
            return shape
    return accepted_shapes[0] if accepted_shapes else ""


def _shape(value: str) -> str:
    return SHAPE_ALIASES.get(value, value)


def _when(action: str, reason: str, shape: str) -> str:
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


def _refs(commit_contract: dict[str, Any], state_refs: dict[str, Any]) -> dict[str, str]:
    refs: dict[str, str] = {}
    exchange = _clean(commit_contract.get("lease_id"))
    task = _clean(state_refs.get("task_ref"))
    run = _clean(state_refs.get("run_ref"))
    if exchange:
        refs["exchange"] = exchange
    if task:
        refs["task"] = task
    if run:
        refs["run"] = run
    return refs


def _write(result: dict[str, Any]) -> dict[str, Any]:
    status = str(result.get("status") or "not_recorded")
    accepted = bool(result.get("accepted"))
    write = {
        "accepted": accepted,
        "status": status,
        "meaning": _meaning(status, accepted),
        "warnings": [str(item) for item in result.get("warnings") or [] if str(item).strip()],
    }
    return _drop_empty(write)


def _meaning(status: str, accepted: bool) -> str:
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


def _adapter_hint(call: dict[str, Any], refs: dict[str, str], *, adapter: str, agent: str) -> dict[str, str]:
    if call.get("action") == "none":
        return {}
    if adapter != "cli":
        return {}
    if call.get("action") == "sync":
        return {"cli": f'workroot agent sync --agent {agent} --cwd . --reason before_work --query "<short intent>"'}
    shape = str(call.get("shape") or "")
    lease = "<exchange>" if refs.get("exchange") else "<exchange>"
    templates = {
        "start_work": f'workroot agent commit --shape start-work --lease {lease} --title "<title>" --summary "<goal summary>" --persistence normal',
        "checkpoint": f'workroot agent commit --shape checkpoint --lease {lease} --summary "<stable progress summary>"',
        "continuation": f'workroot agent commit --shape continuation --lease {lease} --state "<current state>" --next "<next action>"',
        "state_update": f'workroot agent commit --shape state-update --lease {lease} --target "<task ref>" --change "<state change>"',
        "asset": f'workroot agent commit --shape asset --lease {lease} --title "<asset title>" --kind "design_doc" --path "<relative user-space path>" --summary "<asset summary>" --status current',
        "decision": f'workroot agent commit --shape decision --lease {lease} --title "<decision title>" --decision "<decision>" --reason "<reason>" --scope "<scope>"',
    }
    template = templates.get(shape)
    return {"cli": template} if template else {}


def _titles(value: object, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    titles: list[str] = []
    for item in value:
        if isinstance(item, dict):
            title = _clean(item.get("title"))
        else:
            title = _clean(item)
        if title:
            titles.append(title)
        if len(titles) >= limit:
            break
    return titles


def _done_titles(value: object, *, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    titles: list[str] = []
    for item in value:
        if isinstance(item, dict):
            title = _clean(item.get("title"))
            result = _clean(item.get("result_summary"))
            text = f"{title}: {result}" if title and result else title or result
        else:
            text = _clean(item)
        if text:
            titles.append(text)
        if len(titles) >= limit:
            break
    return titles


def _drop_empty(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item not in ("", None, [], {})}


def _clean(value: object) -> str:
    return str(value or "").strip()
```

- [ ] **Step 4: Run packet tests and verify they pass**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_packet -q
```

Expected:

```text
Ran 3 tests ... OK
```

- [ ] **Step 5: Commit Task 1**

```bash
git add src/ai_workroot/protocol/packet.py tests/unit/test_protocol_packet.py
git commit -m "feat: add Workroot private packet renderer"
```

---

### Task 2: Route Context and Agent Output Through Packet Format

**Files:**

- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `src/ai_workroot/context/builder.py`
- Modify: `src/ai_workroot/context/control.py`
- Modify: `tests/unit/test_agent_exchange_command.py`
- Modify: `tests/unit/test_context_wrapper_v2.py`

- [ ] **Step 1: Add failing tests for packet output**

Append to `tests/unit/test_agent_exchange_command.py`:

```python
    def test_packet_format_renders_private_packet_not_full_contract(self) -> None:
        rendered = render_agent_response(
            {
                "agent_may_continue": True,
                "workroot_guidance": "old guidance",
                "workroot_contract": {
                    "next_exchange": {"action": "commit", "reason": "start_work", "required": False},
                    "commit_contract": {"lease_id": "lease-1", "accepted_shapes": ["start_work"]},
                    "state_refs": {"task_ref": None, "run_ref": None},
                    "debug": {"effects": [{"type": "secret"}]},
                },
                "workroot_view": {
                    "focus": "new_work",
                    "confidence": "high",
                    "task_brief": "Packet output",
                    "open_items": [],
                    "recent_done_items": [],
                    "warnings": [],
                },
                "result": {"accepted": False, "status": "not_recorded", "warnings": []},
            },
            output_format="packet",
        )

        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertIn('"shape": "start_work"', rendered)
        self.assertIn("adapter_hint", rendered)
        self.assertNotIn("debug", rendered)
        self.assertNotIn("workroot_contract", rendered)
```

Update `tests/unit/test_context_wrapper_v2.py` by adding:

```python
    def test_context_package_includes_private_packet(self) -> None:
        rendered = build_context(agent="codex", cwd=self.user_dir, query="Continue protocol packet design")

        self.assertIn("## Workroot Private Packet", rendered)
        self.assertIn('"v": "workroot.packet.v1"', rendered)
        self.assertIn("private_do_not_show_user", rendered)
        self.assertNotIn("workroot_contract", rendered)
        self.assertNotIn("debug", rendered)
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command tests.unit.test_context_wrapper_v2 -q
```

Expected:

```text
FAILED
ValueError: --format must be json or guidance
```

or assertion failure because context does not yet render `Workroot Private Packet`.

- [ ] **Step 3: Implement packet output in command adapter**

Modify `src/ai_workroot/commands/agent_exchange.py`:

```python
from ai_workroot.protocol.packet import render_private_packet_markdown
```

Replace `render_agent_response` with:

```python
def render_agent_response(response: dict[str, Any], *, output_format: str = "json", agent: str = "codex") -> str:
    if output_format == "guidance":
        return str(response.get("workroot_guidance") or "").rstrip() + "\n"
    if output_format == "packet":
        return render_private_packet_markdown(response, adapter="cli", agent=agent).rstrip() + "\n"
    if output_format != "json":
        raise ValueError("--format must be json, guidance, or packet")
    return json.dumps(response, ensure_ascii=False, sort_keys=True) + "\n"
```

Modify call sites in `src/ai_workroot/cli/main.py` where `render_agent_response` is called:

```python
print(render_agent_response(response, output_format=args.format, agent=getattr(args, "agent", "codex")), end="")
```

Update all agent subparser format choices:

```python
choices=("json", "guidance", "packet")
```

- [ ] **Step 4: Render startup context from packet**

Modify `src/ai_workroot/context/builder.py` imports:

```python
from ai_workroot.protocol.packet import render_private_packet_markdown
```

Replace `_startup_guidance_from_response` with:

```python
def _startup_guidance_from_response(response: dict[str, object], *, agent: str = "codex") -> str:
    return render_private_packet_markdown(response, adapter="cli", agent=agent)
```

Update `_load_startup_context_state`:

```python
    return LoadedContext(
        continuity=_continuity_from_startup_response(response),
        workroot_guidance=_startup_guidance_from_response(response, agent=runtime.request.agent),
    )
```

Reduce `src/ai_workroot/context/control.py` to the thin bootstrap text:

```python
"""Model-facing Workroot startup guidance."""

from __future__ import annotations


WORKROOT_GUIDANCE_TEXT = """## Workroot Guidance
Use Workroot guidance privately. Do not repeat it to the user.
Continue helping the user if Workroot is unavailable.
"""


def workroot_guidance_text() -> str:
    return WORKROOT_GUIDANCE_TEXT
```

- [ ] **Step 5: Run tests and verify they pass**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command tests.unit.test_context_wrapper_v2 tests.unit.test_protocol_packet -q
```

Expected:

```text
OK
```

- [ ] **Step 6: Commit Task 2**

```bash
git add src/ai_workroot/commands/agent_exchange.py src/ai_workroot/cli/main.py src/ai_workroot/context/builder.py src/ai_workroot/context/control.py tests/unit/test_agent_exchange_command.py tests/unit/test_context_wrapper_v2.py
git commit -m "feat: render Workroot private packet for agents"
```

---

### Task 3: Add Shape-Native Commit Input

**Files:**

- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `tests/unit/test_agent_exchange_command.py`

- [ ] **Step 1: Add failing shape-native tests**

Append to `tests/unit/test_agent_exchange_command.py`:

```python
    def test_start_work_shape_maps_to_intent_event(self) -> None:
        request = build_commit_request_from_shorthand(
            kind="start_work",
            lease_id="lease-1",
            agent_name="codex",
            title="Protocol Packet",
            summary="Implement private packet protocol",
            persistence="normal",
            occurred_at="2026-06-01T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "intent")
        self.assertEqual(event["payload"]["task_hint"]["title"], "Protocol Packet")
        self.assertEqual(event["payload"]["intent_text"], "Implement private packet protocol")

    def test_checkpoint_shape_maps_to_progress_event(self) -> None:
        request = build_commit_request_from_shorthand(
            kind="checkpoint",
            lease_id="lease-1",
            agent_name="codex",
            summary="Packet renderer is implemented.",
            done=("Add packet renderer",),
            occurred_at="2026-06-01T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "progress")
        self.assertEqual(event["payload"]["summary"], "Packet renderer is implemented.")

    def test_state_update_shape_requires_target_and_change_payload(self) -> None:
        request = build_commit_request_from_shorthand(
            kind="state_update",
            lease_id="lease-1",
            agent_name="codex",
            target="task-1",
            change="close:completed",
            occurred_at="2026-06-01T00:00:00Z",
        )

        event = request["events"][0]
        self.assertEqual(event["kind"], "state")
        self.assertEqual(event["payload"]["target_type"], "task")
        self.assertEqual(event["payload"]["target_id"], "task-1")
        self.assertEqual(event["payload"]["from_status"], "active")
        self.assertEqual(event["payload"]["to_status"], "closed")
        self.assertEqual(event["payload"]["close_reason"], "completed")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command -q
```

Expected:

```text
FAILED
ValueError: --kind must be one of...
```

- [ ] **Step 3: Add shape constants and parameters**

Modify `src/ai_workroot/commands/agent_exchange.py` constants:

```python
COMMIT_SHAPES = ("start_work", "checkpoint", "continuation", "state_update", "asset", "decision")
COMMIT_SHORTHAND_KINDS = COMMIT_SHAPES
SHAPE_TO_EVENT_KIND = {
    "start_work": "intent",
    "checkpoint": "progress",
    "continuation": "handoff",
    "state_update": "state",
    "asset": "asset",
    "decision": "decision",
}
```

Add parameters to `run_commit_shorthand` and `build_commit_request_from_shorthand`:

```python
    target: Optional[str] = None,
    change: Optional[str] = None,
    path: str = "",
    asset_kind: str = "",
    status: str = "",
    decision: str = "",
    reason_text: str = "",
    scope: str = "",
```

Normalize the requested shape:

```python
    requested_kind = kind.strip().lower().replace("-", "_")
    if requested_kind not in COMMIT_SHAPES:
        raise ValueError(f"--shape must be one of: {', '.join(COMMIT_SHAPES)}")
    normalized_kind = SHAPE_TO_EVENT_KIND[requested_kind]
```

Pass the extra fields into `_shorthand_payload`.

- [ ] **Step 4: Implement state_update payload mapping**

Extend `_shorthand_payload` signature with `target`, `change`, `path`, `asset_kind`, `status`, `decision`, `reason_text`, and `scope`.

Add this branch:

```python
    if kind == "state":
        target_id = _clean_optional(target)
        change_value = _clean_optional(change)
        if not target_id or not change_value:
            raise ValueError("--target and --change are required for state_update")
        if change_value == "close:completed":
            return {
                "target_type": "task",
                "target_id": target_id,
                "from_status": "active",
                "to_status": "closed",
                "close_reason": "completed",
                "reason": "Task completed.",
            }
        raise ValueError("--change currently supports close:completed")
```

- [ ] **Step 5: Update CLI arguments**

Modify `src/ai_workroot/cli/main.py` import:

```python
from ai_workroot.commands.agent_exchange import COMMIT_SHAPES
```

For `agent commit`, replace the user-facing shape argument:

```python
commit_parser.add_argument("--shape", choices=tuple(shape.replace("_", "-") for shape in COMMIT_SHAPES))
```

Keep the implementation variable normalized:

```python
shape = args.shape.replace("-", "_") if args.shape else None
```

Pass new fields:

```python
target=args.target,
change=args.change,
path=args.path,
asset_kind=args.asset_kind,
status=args.status,
decision=args.decision,
reason_text=args.reason_text,
scope=args.scope,
```

Add CLI options:

```python
commit_parser.add_argument("--target")
commit_parser.add_argument("--change")
commit_parser.add_argument("--path", default="")
commit_parser.add_argument("--asset-kind", default="")
commit_parser.add_argument("--status", default="")
commit_parser.add_argument("--decision", default="")
commit_parser.add_argument("--reason-text", default="")
commit_parser.add_argument("--scope", default="")
```

Update the branch:

```python
elif shape:
    response = run_commit_shorthand(
        kind=shape,
        lease_id=args.lease or "",
        agent_name=args.agent,
        cwd=Path(args.cwd) if args.cwd else None,
        workroot_id=args.workroot_id,
        title=args.title,
        summary=args.summary,
        current_state=args.current_state,
        next_action=args.next_action,
        task_id=args.task_id,
        run_id=args.run_id,
        parent_task_id=args.parent_task_id,
        persistence=args.persistence,
        done=tuple(args.done),
        open=tuple(args.open),
        blocked=tuple(args.blocked),
        session_id=args.session_id,
        event_id=args.event_id,
        request_id=args.request_id,
        idempotency_key=args.idempotency_key,
        occurred_at=args.occurred_at,
        target=args.target,
        change=args.change,
        path=args.path,
        asset_kind=args.asset_kind,
        status=args.status,
        decision=args.decision,
        reason_text=args.reason_text,
        scope=args.scope,
    )
else:
    parser.error("agent commit requires --request or --shape")
```

- [ ] **Step 6: Run tests and verify they pass**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command -q
```

Expected:

```text
OK
```

- [ ] **Step 7: Commit Task 3**

```bash
git add src/ai_workroot/commands/agent_exchange.py src/ai_workroot/cli/main.py tests/unit/test_agent_exchange_command.py
git commit -m "feat: add shape-native Workroot commit input"
```

---

### Task 4: Add Asset Commit Projection

**Files:**

- Modify: `src/ai_workroot/protocol/response.py`
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Create/Modify: `tests/integration/test_protocol_packet_loop.py`

- [ ] **Step 1: Add failing asset integration test**

Create `tests/integration/test_protocol_packet_loop.py` with this setup and asset test:

```python
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from ai_workroot.protocol.controller import commit, sync
from ai_workroot.state.environment import initialize_environment, register_workroot
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.sqlite import initialize_workroot_sqlite


class ProtocolPacketLoopTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "ai-home"
        self.user_dir = Path(self.tmp.name) / "workspace"
        self.user_dir.mkdir()
        initialize_environment(self.home)
        self.registration = register_workroot(
            self.home,
            workroot_id="wr_demo",
            name="Demo",
            user_directory=self.user_dir,
        )
        self.sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        initialize_workroot_sqlite(self.sqlite_path)
        self.previous_home = os.environ.get("AI_WORKROOT_HOME")
        os.environ["AI_WORKROOT_HOME"] = str(self.home)
        self.addCleanup(self.restore_home)

    def restore_home(self) -> None:
        if self.previous_home is None:
            os.environ.pop("AI_WORKROOT_HOME", None)
        else:
            os.environ["AI_WORKROOT_HOME"] = self.previous_home

    def test_asset_commit_records_existing_user_visible_file(self) -> None:
        task = self.create_task()
        asset_path = self.user_dir / "space" / "outputs" / "protocol-design.md"
        asset_path.parent.mkdir(parents=True)
        asset_path.write_text("# Protocol Design\n", encoding="utf-8")

        response = commit(
            self.commit_request(
                lease_id=self.lease_id(task),
                event_id="evt-asset-design",
                kind="asset",
                payload={
                    "task_id": self.task_id(task),
                    "run_id": self.run_id(task),
                    "title": "Protocol Design",
                    "asset_type": "design_doc",
                    "path": "space/outputs/protocol-design.md",
                    "summary": "Design document for the private packet protocol.",
                    "status": "current",
                },
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "applied")
        with sqlite3.connect(self.sqlite_path) as conn:
            asset = conn.execute(
                "SELECT asset_type, title, current_path, lifecycle_status FROM assets WHERE asset_id = ?",
                ("asset-evt-asset-design",),
            ).fetchone()
            hint = conn.execute(
                "SELECT title, summary FROM context_recall_hints WHERE target_type = 'asset' AND target_id = ?",
                ("asset-evt-asset-design",),
            ).fetchone()
        self.assertEqual(asset, ("design_doc", "Protocol Design", "space/outputs/protocol-design.md", "current"))
        self.assertEqual(hint, ("Protocol Design", "Design document for the private packet protocol."))

    def create_task(self) -> dict[str, object]:
        aligned = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-task",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Design protocol packet",
                "work_signal": {"phase": "starting", "work_kind": "implementation", "intended_action": "plan"},
            }
        )
        return commit(
            self.commit_request(
                lease_id=self.lease_id(aligned),
                event_id="evt-intent-task",
                kind="intent",
                payload={
                    "intent_text": "Design protocol packet.",
                    "classification": {"persistence": "normal", "confidence": 0.95, "reason": "test"},
                    "task_hint": {"title": "Protocol Packet", "task_id": "task-protocol-packet"},
                },
            )
        )

    def commit_request(self, *, lease_id: str, event_id: str, kind: str, payload: dict[str, object]) -> dict[str, object]:
        return {
            "protocol_version": "workroot.v1",
            "request_id": f"req-{event_id}",
            "exchange_lease_id": lease_id,
            "idempotency_key": f"idem-{event_id}",
            "events": [
                {
                    "event_id": event_id,
                    "kind": kind,
                    "schema_version": f"{kind}.v1",
                    "occurred_at": "2026-06-01T00:00:00Z",
                    "source": {"actor_type": "agent", "actor_name": "codex", "session_id": "test"},
                    "confirmation": {"status": "agent_observed", "confirmed_by": None},
                    "payload": payload,
                    "evidence": [],
                }
            ],
        }

    def lease_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["commit_contract"]["lease_id"])

    def task_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["task_ref"])

    def run_id(self, response: dict[str, object]) -> str:
        return str(response["workroot_contract"]["state_refs"]["run_ref"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the asset test and verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.integration.test_protocol_packet_loop.ProtocolPacketLoopTest.test_asset_commit_records_existing_user_visible_file -q
```

Expected:

```text
FAILED
event_not_allowed
```

or:

```text
projection not implemented for event kind: asset
```

- [ ] **Step 3: Add Asset shape response mappings**

Modify `src/ai_workroot/protocol/response.py`:

```python
EVENT_KIND_TO_SHAPE = {
    "intent": "start_work",
    "progress": "checkpoint",
    "handoff": "continuation_checkpoint",
    "state": "state_update",
    "asset": "asset",
    "decision": "decision",
}
SHAPE_INPUT_REQUIREMENTS = {
    "start_work": ["intent_summary"],
    "checkpoint": ["summary", "changed_steps_or_results"],
    "continuation_checkpoint": ["current_state", "next_action"],
    "state_update": ["target_ref", "state_change"],
    "asset": ["title", "kind", "path", "summary", "status"],
    "decision": ["title", "decision", "reason", "scope"],
}
```

- [ ] **Step 4: Allow asset events on task leases**

Modify `src/ai_workroot/protocol/projections.py`:

```python
TASK_LEASE_EVENTS = ["progress", "handoff", "state", "asset", "decision"]
```

- [ ] **Step 5: Implement `project_asset`**

In `src/ai_workroot/protocol/projections.py`, update `apply_projection`:

```python
    if kind == "asset":
        return project_asset(conn, workroot_id=workroot_id, lease=lease, event=event)
```

Add:

```python
def project_asset(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    task_id, run_id = _task_run_from_payload_or_lease(payload, lease)
    _require_matching_lease(lease, task_id=task_id, run_id=run_id)
    _require_run(conn, workroot_id, task_id, run_id)
    title = _required_text(payload, "title")
    asset_type = _required_text(payload, "asset_type")
    path = _required_text(payload, "path")
    summary = _required_text(payload, "summary")
    status = _text_or_none(payload.get("status")) or "current"
    _require_user_visible_existing_asset(conn, workroot_id=workroot_id, relative_path=path)
    asset_id = _stable_id("asset", str(event["event_id"]))
    hint_id = _stable_id("hint", f"{event['event_id']}-asset")
    now = now_utc()
    conn.execute(
        """
        INSERT INTO assets (
          asset_id, workroot_id, asset_type, title, lifecycle_status,
          publication_status, surface_id, current_path, content_hash, updatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
          workroot_id=excluded.workroot_id,
          asset_type=excluded.asset_type,
          title=excluded.title,
          lifecycle_status=excluded.lifecycle_status,
          publication_status=excluded.publication_status,
          current_path=excluded.current_path,
          updatedAt=excluded.updatedAt
        """,
        (asset_id, workroot_id, asset_type, title, status, "internal", path, now),
    )
    _upsert_context_hint(
        conn,
        hint_id=hint_id,
        workroot_id=workroot_id,
        target_type="asset",
        target_id=asset_id,
        scope_type="task",
        scope_id=task_id,
        kind="asset",
        title=title,
        summary=summary,
        priority="normal",
        recall_rule="metadata_then_summary",
        origin="protocol_asset",
        source_ref=str(event["event_id"]),
        now=now,
    )
    _link_task_target(
        conn,
        workroot_id=workroot_id,
        task_id=task_id,
        target_type="asset",
        target_id=asset_id,
        title=title,
        relationship_type="produced",
        event_id=str(event["event_id"]),
        now=now,
    )
    _bump_task_run_context(conn, workroot_id, task_id, run_id)
    return _continue_result(
        effects=[
            {"type": "asset_recorded", "target_type": "asset", "target_id": asset_id},
            {"type": "context_recall_hint_created", "target_type": "context_recall_hint", "target_id": hint_id},
        ],
        task_id=task_id,
        run_id=run_id,
    )
```

Add helpers:

```python
def _require_user_visible_existing_asset(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    relative_path: str,
) -> None:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ProtocolError("projection_failed", "asset path must be relative and stay in user space")
    row = conn.execute(
        "SELECT user_directory FROM workroots WHERE workroot_id = ? LIMIT 1",
        (workroot_id,),
    ).fetchone()
    if row is None:
        return
    full_path = Path(str(row[0])) / path
    if not full_path.is_file():
        raise ProtocolError("projection_failed", f"asset file does not exist: {relative_path}")


def _upsert_context_hint(
    conn: sqlite3.Connection,
    *,
    hint_id: str,
    workroot_id: str,
    target_type: str,
    target_id: str,
    scope_type: str,
    scope_id: str,
    kind: str,
    title: str,
    summary: str,
    priority: str,
    recall_rule: str,
    origin: str,
    source_ref: str,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO context_recall_hints (
          hint_id, workroot_id, target_type, target_id, scope_type, scope_id,
          kind, title, summary, priority, recall_rule, lifecycle_status,
          origin, source_ref, createdAt, updatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(hint_id) DO UPDATE SET
          title=excluded.title,
          summary=excluded.summary,
          priority=excluded.priority,
          recall_rule=excluded.recall_rule,
          lifecycle_status=excluded.lifecycle_status,
          updatedAt=excluded.updatedAt
        """,
        (
            hint_id,
            workroot_id,
            target_type,
            target_id,
            scope_type,
            scope_id,
            kind,
            title,
            summary,
            priority,
            recall_rule,
            "active",
            origin,
            source_ref,
            now,
            now,
        ),
    )
    conn.execute("DELETE FROM context_recall_hints_fts WHERE hint_id = ?", (hint_id,))
    conn.execute(
        "INSERT INTO context_recall_hints_fts (hint_id, title, summary) VALUES (?, ?, ?)",
        (hint_id, title, summary),
    )


def _link_task_target(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    task_id: str,
    target_type: str,
    target_id: str,
    title: str,
    relationship_type: str,
    event_id: str,
    now: str,
) -> None:
    task_node = f"task:{task_id}"
    target_node = f"{target_type}:{target_id}"
    edge_id = _stable_id("edge", f"{event_id}-{relationship_type}")
    conn.execute(
        """
        INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
          title=excluded.title,
          target_type=excluded.target_type,
          target_id=excluded.target_id
        """,
        (task_node, workroot_id, "task", task_id, "task", task_id),
    )
    conn.execute(
        """
        INSERT INTO relationship_nodes (node_id, workroot_id, node_type, title, target_type, target_id)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
          title=excluded.title,
          target_type=excluded.target_type,
          target_id=excluded.target_id
        """,
        (target_node, workroot_id, target_type, title, target_type, target_id),
    )
    conn.execute(
        """
        INSERT INTO relationship_edges (
          edge_id, workroot_id, from_node_id, to_node_id, relationship_type,
          confidence, status, createdAt, updatedAt
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(edge_id) DO UPDATE SET
          relationship_type=excluded.relationship_type,
          confidence=excluded.confidence,
          status=excluded.status,
          updatedAt=excluded.updatedAt
        """,
        (edge_id, workroot_id, task_node, target_node, relationship_type, 1.0, "active", now, now),
    )
```

Add import:

```python
from pathlib import Path
```

- [ ] **Step 6: Add asset payload mapping for shape-native shorthand**

Modify `_shorthand_payload` asset branch:

```python
    if kind == "asset":
        cleaned_title = title.strip()
        cleaned_type = asset_kind.strip()
        cleaned_path = path.strip()
        cleaned_summary = summary.strip()
        if not cleaned_title or not cleaned_type or not cleaned_path or not cleaned_summary:
            raise ValueError("--title, --asset-kind, --path, and --summary are required for asset")
        payload = {
            "title": cleaned_title,
            "asset_type": cleaned_type,
            "path": cleaned_path,
            "summary": cleaned_summary,
            "status": status.strip() or "current",
        }
        _add_task_run_fields(payload, task_id=task_id, run_id=run_id)
        return payload
```

- [ ] **Step 7: Run asset tests and focused protocol tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.integration.test_protocol_packet_loop tests.unit.test_agent_exchange_command tests.unit.test_protocol_response_v2 -q
```

Expected:

```text
OK
```

- [ ] **Step 8: Commit Task 4**

```bash
git add src/ai_workroot/protocol/response.py src/ai_workroot/protocol/projections.py src/ai_workroot/commands/agent_exchange.py tests/integration/test_protocol_packet_loop.py
git commit -m "feat: capture user-visible assets through protocol commits"
```

---

### Task 5: Add Decision Commit Projection and Final Verification

**Files:**

- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `tests/integration/test_protocol_packet_loop.py`
- Modify: `tests/e2e/live_protocol.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-06-01-workroot-private-packet-protocol-design.md`

- [ ] **Step 1: Add failing decision test**

Append to `tests/integration/test_protocol_packet_loop.py`:

```python
    def test_decision_commit_records_recall_hint_and_relationship(self) -> None:
        task = self.create_task()
        response = commit(
            self.commit_request(
                lease_id=self.lease_id(task),
                event_id="evt-decision-packet",
                kind="decision",
                payload={
                    "task_id": self.task_id(task),
                    "run_id": self.run_id(task),
                    "title": "LLM-visible packet",
                    "decision": "Workroot may pass a small private packet directly to the LLM.",
                    "reason": "Agent runtimes cannot be assumed to preserve hidden state consistently.",
                    "scope": "agent_protocol",
                },
            )
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["result"]["status"], "applied")
        with sqlite3.connect(self.sqlite_path) as conn:
            hint = conn.execute(
                """
                SELECT title, summary
                FROM context_recall_hints
                WHERE target_type = 'decision' AND target_id = ?
                """,
                ("decision-evt-decision-packet",),
            ).fetchone()
            edge = conn.execute(
                """
                SELECT relationship_type
                FROM relationship_edges
                WHERE to_node_id = ?
                """,
                ("decision:decision-evt-decision-packet",),
            ).fetchone()
        self.assertEqual(hint[0], "LLM-visible packet")
        self.assertIn("Workroot may pass a small private packet", hint[1])
        self.assertEqual(edge, ("decided",))
```

- [ ] **Step 2: Run decision test and verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.integration.test_protocol_packet_loop.ProtocolPacketLoopTest.test_decision_commit_records_recall_hint_and_relationship -q
```

Expected:

```text
FAILED
projection not implemented for event kind: decision
```

- [ ] **Step 3: Implement decision projection without a new decision table**

In `src/ai_workroot/protocol/projections.py`, update `apply_projection`:

```python
    if kind == "decision":
        return project_decision(conn, workroot_id=workroot_id, lease=lease, event=event)
```

Add:

```python
def project_decision(
    conn: sqlite3.Connection,
    *,
    workroot_id: str,
    lease: dict[str, Any],
    event: dict[str, Any],
) -> ProjectionResult:
    payload = event["payload"]
    task_id, run_id = _task_run_from_payload_or_lease(payload, lease)
    _require_matching_lease(lease, task_id=task_id, run_id=run_id)
    _require_run(conn, workroot_id, task_id, run_id)
    title = _required_text(payload, "title")
    decision_text = _required_text(payload, "decision")
    reason = _required_text(payload, "reason")
    scope = _required_text(payload, "scope")
    decision_id = _stable_id("decision", str(event["event_id"]))
    hint_id = _stable_id("hint", f"{event['event_id']}-decision")
    now = now_utc()
    summary = f"{decision_text} Reason: {reason} Scope: {scope}"
    _upsert_context_hint(
        conn,
        hint_id=hint_id,
        workroot_id=workroot_id,
        target_type="decision",
        target_id=decision_id,
        scope_type="task",
        scope_id=task_id,
        kind="decision",
        title=title,
        summary=summary,
        priority="high",
        recall_rule="summary_first",
        origin="protocol_decision",
        source_ref=str(event["event_id"]),
        now=now,
    )
    _link_task_target(
        conn,
        workroot_id=workroot_id,
        task_id=task_id,
        target_type="decision",
        target_id=decision_id,
        title=title,
        relationship_type="decided",
        event_id=str(event["event_id"]),
        now=now,
    )
    _bump_task_run_context(conn, workroot_id, task_id, run_id)
    return _continue_result(
        effects=[
            {"type": "decision_recorded", "target_type": "decision", "target_id": decision_id},
            {"type": "context_recall_hint_created", "target_type": "context_recall_hint", "target_id": hint_id},
        ],
        task_id=task_id,
        run_id=run_id,
    )
```

- [ ] **Step 4: Add decision payload mapping for shape-native shorthand**

Modify `_shorthand_payload` decision branch in `src/ai_workroot/commands/agent_exchange.py`:

```python
    if kind == "decision":
        cleaned_title = title.strip()
        cleaned_decision = decision.strip()
        cleaned_reason = reason_text.strip()
        cleaned_scope = scope.strip()
        if not cleaned_title or not cleaned_decision or not cleaned_reason or not cleaned_scope:
            raise ValueError("--title, --decision, --reason-text, and --scope are required for decision")
        payload = {
            "title": cleaned_title,
            "decision": cleaned_decision,
            "reason": cleaned_reason,
            "scope": cleaned_scope,
        }
        _add_task_run_fields(payload, task_id=task_id, run_id=run_id)
        return payload
```

- [ ] **Step 5: Update live E2E prompts**

Modify `tests/e2e/live_protocol.py` prompts to use packet and shape language:

- In `_guided_minimal_loop_prompt`, change sync call to request `--format packet` for model-facing inspection, then use JSON only where orchestration needs full response:

```python
call(["agent", "sync", "--agent", "codex", "--cwd", ".", "--reason", "before_work", "--query", "Live protocol guided loop", "--format", "packet"])
sync = json.loads(call([
    "agent", "sync",
    "--agent", "codex",
    "--cwd", ".",
    "--reason", "before_work",
    "--query", "Live protocol guided loop"
]))
```

- Replace LLM-facing `--kind` examples with `--shape`:

```python
continuation = json.loads(call([
    "agent", "commit",
    "--shape", "continuation",
    "--lease", progress["workroot_contract"]["commit_contract"]["lease_id"],
    "--cwd", ".",
    "--state", "Guided live protocol loop committed intent and progress.",
    "--next", "{GUIDED_HANDOFF_NEXT_ACTION}",
]))
```

Add aliases in CLI for `--state` and `--next` if not already present:

```python
commit_parser.add_argument("--state", dest="current_state", default="")
commit_parser.add_argument("--next", dest="next_action", default="")
```

- [ ] **Step 6: Update README protocol examples**

Modify `README.md` protocol section to show:

```markdown
```bash
workroot context --agent codex --cwd .
workroot agent sync --agent codex --cwd . --reason before_work --query "<short intent>"
workroot agent commit --shape start-work --lease <exchange> --title "<title>" --summary "<goal summary>" --persistence normal
workroot agent commit --shape checkpoint --lease <exchange> --summary "<stable progress summary>"
workroot agent commit --shape continuation --lease <exchange> --state "<current state>" --next "<next action>"
```
```

State that `--format packet` is for LLM-facing private protocol output and default JSON is for runtime/debug adapters.

- [ ] **Step 7: Run focused tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_packet tests.unit.test_agent_exchange_command tests.unit.test_protocol_response_v2 tests.integration.test_protocol_packet_loop tests.integration.test_agent_protocol_loop tests.unit.test_context_wrapper_v2 -q
```

Expected:

```text
OK
```

- [ ] **Step 8: Run full test suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Expected:

```text
OK
```

- [ ] **Step 9: Run release validation**

Run:

```bash
PATH=.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src scripts/dev/validate-release.sh
```

Expected:

```text
Clean Workroot release validation passed
```

- [ ] **Step 10: Commit Task 5**

```bash
git add src/ai_workroot/protocol/projections.py src/ai_workroot/commands/agent_exchange.py tests/integration/test_protocol_packet_loop.py tests/e2e/live_protocol.py README.md docs/superpowers/specs/2026-06-01-workroot-private-packet-protocol-design.md
git commit -m "feat: complete private packet asset and decision capture"
```

---

## Self-Review Notes

Spec coverage:

- Stable `sync` and `commit`: covered by Tasks 1-3.
- LLM-facing packet fields `v/rules/work/call/refs/write/adapter_hint`: covered by Task 1.
- Default-on adapter hint when `call.action != none`: covered by Task 1 and Task 2.
- Context startup packet: covered by Task 2.
- Shape-native commit semantics: covered by Task 3.
- Task creation only after `start_work` commit: preserved by Task 3 and existing projection tests.
- Asset capture after user-visible file exists: covered by Task 4.
- Decision capture without new domain entity/table: covered by Task 5 using protocol events, recall hints, and relationship nodes.
- Multi-fact capture guidance: covered by packet `call.also`; batch implementation can remain sequential in this iteration.
- Non-blocking degraded behavior: preserved by existing controller responses and packet `write` mapping.
- No L1/L2/L3 context strategy implementation: explicitly out of scope.

Placeholder scan:

- No `TODO`, `TBD`, or unspecified implementation slots are intentionally left in the plan.

Type consistency:

- LLM-facing `shape` names use underscores in Python and hyphenated CLI spellings where appropriate.
- Internal event kinds remain `intent/progress/handoff/state/asset/decision`.
- `refs.exchange` maps to current lease ID.
- Asset uses `asset_type` in internal payload and `--asset-kind` in CLI.
- Decision uses protocol event plus query projections, not a new table.
