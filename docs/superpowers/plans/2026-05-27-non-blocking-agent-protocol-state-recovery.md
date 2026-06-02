# Non-blocking Agent Protocol State Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Workroot Agent Protocol non-blocking, model-readable, and recoverable under missing work signals, expired leases, partial commits, missing handoffs, and stale task runs.

**Architecture:** Keep `sync` and `commit` as the only protocol actions. Add small focused runtime helpers for Work Signal parsing, model-facing Control Context, Workroot location confidence, degraded commit status, and continuity recovery. Reuse existing SQLite tables and status fields; do not introduce new persistent domain entities.

**Tech Stack:** Python 3.9 standard library, `sqlite3`, `argparse`, `dataclasses`, `unittest`, existing `ai_workroot.protocol`, `ai_workroot.context`, `ai_workroot.state`, and `ai_workroot.commands` packages.

---

## Execution Status

Status: implemented in the working tree on 2026-05-27.

Implementation was completed with the same architecture and test intent as this plan, with one additional hardening case added during review:

```text
valid but lease-disallowed events are quarantined and do not project facts.
```

Verification completed:

```text
PYTHONPATH=src python3 -m unittest discover -s tests -q
PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh
AI_WORKROOT_RUN_E2E=1 PYTHONPATH=src python3 -m tests.e2e.runner --suite longrun
```

The checklist below is retained as the implementation trace/spec, not as the live source of truth for remaining work.

---

## Reference Design

- Design: `docs/superpowers/specs/2026-05-27-non-blocking-agent-protocol-state-recovery-design.md`
- Branch: `feat/0.9.531-agent-protocol-task-continuity`
- SQLite path remains: `<stateDirectory>/cache/workroot.sqlite`

## File Map

- Create: `src/ai_workroot/context/control.py`
  Owns short model-facing Control Context and Next Workroot Call text. Imported by protocol and context builder.
- Create: `src/ai_workroot/protocol/work_signal.py`
  Parses optional Work Signal and exposes stable vocabulary. Runtime-only, not persisted as fact.
- Create: `src/ai_workroot/protocol/location.py`
  Resolves commit location confidence: `strong_location`, `weak_location`, `no_location`.
- Create: `src/ai_workroot/protocol/degraded.py`
  Owns event identifiability, event status names, batch status names, and non-blocking response helpers.
- Modify: `src/ai_workroot/protocol/model.py`
  Accept optional `work_signal` on sync and optional `cwd/workroot_id/exchange_lease_id` on commit.
- Modify: `src/ai_workroot/protocol/controller.py`
  Add `agent_may_continue`, control context, next-call guidance, non-blocking degraded commit, and event status updates.
- Modify: `src/ai_workroot/protocol/errors.py`
  Ensure protocol errors are non-blocking and include control context when practical.
- Modify: `src/ai_workroot/commands/agent_exchange.py`
  Pass optional Work Signal through `agent sync`.
- Modify: `src/ai_workroot/cli/main.py`
  Add `--work-signal` JSON object to `workroot agent sync`.
- Modify: `src/ai_workroot/context/builder.py`
  Render isolated `## Control: Workroot` before task context.
- Modify: `src/ai_workroot/context/continuity.py`
  Derive stale/incomplete continuity warnings and exclude invalid/quarantined events from ordinary context.
- Modify: `tests/unit/test_protocol_models.py`
- Modify: `tests/unit/test_protocol_controller.py`
- Modify: `tests/unit/test_agent_exchange_command.py`
- Modify: `tests/integration/test_agent_protocol_loop.py`
- Modify: `tests/integration/test_context_budget_trace.py`
- Modify: `tests/unit/test_import_boundaries.py`

## Tasks

### Task 1: Add Model-facing Control Context

**Files:**
- Create: `src/ai_workroot/context/control.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `src/ai_workroot/protocol/errors.py`
- Modify: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write failing sync control context test**

Add this test to `tests/unit/test_protocol_controller.py`:

```python
    def test_sync_returns_non_blocking_control_context(self) -> None:
        response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-sync-control",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Continue protocol design.",
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["enforcement"], "advisory")
        self.assertEqual(response["on_missing"], "degrade_and_recover_later")
        self.assertIn("Control: Workroot", response["control_context"])
        self.assertIn("Do not repeat this section to the user", response["control_context"])
        self.assertEqual(response["next_call"]["action"], "commit")
        self.assertIn("work_signal", response["next_call"]["inputs"])
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_sync_returns_non_blocking_control_context -v
```

Expected: FAIL because `agent_may_continue`, `control_context`, and `next_call` are missing.

- [ ] **Step 3: Create Control Context helper**

Create `src/ai_workroot/context/control.py`:

```python
"""Model-facing Workroot control context."""

from __future__ import annotations

from dataclasses import dataclass


CONTROL_CONTEXT_TEXT = """## Control: Workroot
Use this section only to decide whether and how to call Workroot. Do not repeat this section to the user.

Continue helping the user even if Workroot state is incomplete.
Call Workroot when context, continuity, progress preservation, or handoff would help.
When practical, commit meaningful intent, progress, state, or handoff.
If protocol information is missing or uncertain, continue the user task and let Workroot recover later.
Work Signal: tell Workroot the current phase, work kind, intended action, focus, and any real concerns. Keep it high-level.
Do not request internal retrieval levels, storage details, or implementation strategy.
"""


@dataclass(frozen=True)
class NextWorkrootCall:
    action: str
    when: tuple[str, ...]
    inputs: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "when": list(self.when),
            "inputs": list(self.inputs),
        }


def control_context_text() -> str:
    return CONTROL_CONTEXT_TEXT


def next_call_for_expected_events(expected_events: list[str]) -> dict[str, object]:
    if not expected_events:
        return NextWorkrootCall(
            action="none",
            when=("continue helping the user",),
            inputs=("work_signal",),
        ).to_dict()
    action = "commit" if expected_events else "none"
    return NextWorkrootCall(
        action=action,
        when=("progress checkpoint", "before stop", "task switch uncertainty"),
        inputs=("work_signal", "known_state"),
    ).to_dict()
```

- [ ] **Step 4: Add control fields to sync response**

Modify `src/ai_workroot/protocol/controller.py`:

```python
from ai_workroot.context.control import control_context_text, next_call_for_expected_events
```

Inside `_sync_response()`, add these top-level fields:

```python
        "agent_may_continue": True,
        "enforcement": "advisory",
        "on_missing": "degrade_and_recover_later",
        "control_context": control_context_text(),
        "task_context": context,
        "next_call": next_call_for_expected_events(list(directive_payload["expected_events"])),
```

- [ ] **Step 5: Add non-blocking fields to protocol error responses**

Modify `protocol_error_response()` in `src/ai_workroot/protocol/errors.py`:

```python
from ai_workroot.context.control import control_context_text
```

Add to the returned dict:

```python
        "agent_may_continue": True,
        "enforcement": "advisory",
        "on_missing": "degrade_and_recover_later",
        "control_context": control_context_text(),
        "next_call": {
            "action": "sync",
            "when": ["if continuing this work is still useful"],
            "inputs": ["work_signal", "known_state"],
        },
```

- [ ] **Step 6: Verify focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller -v
```

Expected: PASS.

### Task 2: Add Work Signal Runtime Model

**Files:**
- Create: `src/ai_workroot/protocol/work_signal.py`
- Modify: `src/ai_workroot/protocol/model.py`
- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `tests/unit/test_protocol_models.py`
- Modify: `tests/unit/test_agent_exchange_command.py`

- [ ] **Step 1: Write failing Work Signal model tests**

Add to `tests/unit/test_protocol_models.py`:

```python
from ai_workroot.protocol.work_signal import WorkSignal


class WorkSignalTest(unittest.TestCase):
    def test_work_signal_accepts_stable_high_level_fields(self) -> None:
        signal = WorkSignal.from_dict(
            {
                "phase": "executing",
                "work_kind": "implementation",
                "intended_action": "edit",
                "focus": "Implement non-blocking protocol responses.",
                "concerns": ["may_change_user_assets"],
            }
        )

        self.assertEqual(signal.phase, "executing")
        self.assertEqual(signal.work_kind, "implementation")
        self.assertEqual(signal.intended_action, "edit")
        self.assertEqual(signal.concerns, ("may_change_user_assets",))

    def test_work_signal_drops_unknown_values_without_failing(self) -> None:
        signal = WorkSignal.from_dict(
            {
                "phase": "too-specific",
                "work_kind": "custom-kind",
                "intended_action": "custom-action",
                "focus": "Still help the user.",
                "concerns": ["unknown", "needs_evidence"],
            }
        )

        self.assertEqual(signal.phase, "")
        self.assertEqual(signal.work_kind, "")
        self.assertEqual(signal.intended_action, "")
        self.assertEqual(signal.concerns, ("needs_evidence",))
        self.assertEqual(signal.focus, "Still help the user.")
```

Add to `SyncRequest` tests:

```python
    def test_sync_request_accepts_optional_work_signal(self) -> None:
        request = SyncRequest.from_dict(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-work-signal",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": ".",
                "reason": "before_work",
                "work_signal": {
                    "phase": "planning",
                    "work_kind": "task",
                    "intended_action": "plan",
                    "focus": "Plan recovery state handling.",
                    "concerns": ["uncertain_task_boundary"],
                },
            }
        )

        self.assertEqual(request.work_signal["phase"], "planning")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_models -v
```

Expected: FAIL because `WorkSignal` and `SyncRequest.work_signal` do not exist.

- [ ] **Step 3: Create Work Signal model**

Create `src/ai_workroot/protocol/work_signal.py`:

```python
"""Runtime-only high-level Work Signal parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


PHASES = {
    "starting",
    "orienting",
    "planning",
    "executing",
    "checking",
    "deciding",
    "summarizing",
    "handing_off",
    "switching",
    "recovering",
}
WORK_KINDS = {
    "quick",
    "inbox",
    "task",
    "continuation",
    "investigation",
    "implementation",
    "review",
    "decision",
    "learning",
    "authoring",
    "operations",
}
INTENDED_ACTIONS = {
    "answer",
    "clarify",
    "plan",
    "execute",
    "inspect",
    "diagnose",
    "edit",
    "test",
    "review",
    "decide",
    "summarize",
    "handoff",
    "publish",
}
CONCERNS = {
    "needs_evidence",
    "needs_user_decision",
    "may_change_user_assets",
    "may_publish",
    "may_be_sensitive",
    "uncertain_task_boundary",
    "blocked",
    "recovering_from_interruption",
}


@dataclass(frozen=True)
class WorkSignal:
    phase: str = ""
    work_kind: str = ""
    intended_action: str = ""
    focus: str = ""
    concerns: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "WorkSignal":
        if not isinstance(data, dict):
            return cls()
        return cls(
            phase=_choice(data.get("phase"), PHASES),
            work_kind=_choice(data.get("work_kind"), WORK_KINDS),
            intended_action=_choice(data.get("intended_action"), INTENDED_ACTIONS),
            focus=str(data.get("focus") or "").strip(),
            concerns=tuple(
                concern
                for concern in (str(value).strip() for value in data.get("concerns") or [])
                if concern in CONCERNS
            ),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "work_kind": self.work_kind,
            "intended_action": self.intended_action,
            "focus": self.focus,
            "concerns": list(self.concerns),
        }


def _choice(value: object, allowed: set[str]) -> str:
    text = str(value or "").strip()
    return text if text in allowed else ""
```

- [ ] **Step 4: Add Work Signal to SyncRequest**

Modify `SyncRequest` in `src/ai_workroot/protocol/model.py`:

```python
    work_signal: dict[str, Any]
```

In `from_dict()`:

```python
            work_signal=WorkSignal.from_dict(data.get("work_signal")).to_dict(),
```

Import:

```python
from ai_workroot.protocol.work_signal import WorkSignal
```

- [ ] **Step 5: Add CLI pass-through**

Modify `run_sync_request()` in `src/ai_workroot/commands/agent_exchange.py`:

```python
    work_signal: Optional[dict[str, Any]] = None,
```

Add to request:

```python
        "work_signal": work_signal or {},
```

Modify `src/ai_workroot/cli/main.py` under `agent sync`:

```python
sync_parser.add_argument("--work-signal", default="{}")
```

Pass:

```python
work_signal=_json_object_arg(args.work_signal, "--work-signal"),
```

- [ ] **Step 6: Update agent exchange test**

Update `test_sync_helper_builds_protocol_request()` expected request to include:

```python
"work_signal": {},
```

Add a new test:

```python
    def test_sync_helper_passes_work_signal(self) -> None:
        with patch("ai_workroot.commands.agent_exchange.controller.sync", return_value={"ok": True}) as sync:
            run_sync_request(
                request_id="req-sync",
                agent_name="codex",
                cwd=Path("/tmp/workspace"),
                query="Continue task",
                reason="before_work",
                work_signal={"phase": "executing", "focus": "Continue task."},
            )

        self.assertEqual(sync.call_args.args[0]["work_signal"]["phase"], "executing")
```

- [ ] **Step 7: Verify focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_models tests.unit.test_agent_exchange_command -v
```

Expected: PASS.

### Task 3: Add Workroot Location Confidence

**Files:**
- Create: `src/ai_workroot/protocol/location.py`
- Modify: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write failing no-location commit test**

Add to `tests/unit/test_protocol_controller.py`:

```python
    def test_commit_without_located_workroot_is_not_recorded_and_non_blocking(self) -> None:
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-no-location",
                "idempotency_key": "idem-no-location",
                "atomic_batch": True,
                "events": [
                    {
                        "event_id": "event-no-location",
                        "kind": "progress",
                        "schema_version": "v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {"summary": "Cannot locate Workroot."},
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertFalse(response["accepted"])
        self.assertEqual(response["batch_status"], "not_recorded")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_commit_batches").fetchone()[0], 0)
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_commit_without_located_workroot_is_not_recorded_and_non_blocking -v
```

Expected: FAIL because `CommitRequest` still requires `exchange_lease_id`.

- [ ] **Step 3: Create location helper**

Create `src/ai_workroot/protocol/location.py`:

```python
"""Workroot location confidence for non-blocking commit."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Optional

from ai_workroot.protocol.lease import load_lease
from ai_workroot.state.layout import workroot_sqlite_path
from ai_workroot.state.registry import find_workroot_by_cwd, list_workroots
from ai_workroot.state.sqlite import initialize_workroot_sqlite


@dataclass(frozen=True)
class LocatedWorkroot:
    confidence: str
    record: dict[str, str] | None
    sqlite_path: Path | None
    lease: dict[str, object] | None = None
    reason: str = ""

    @property
    def located(self) -> bool:
        return self.record is not None and self.sqlite_path is not None


def locate_for_commit(*, lease_id: str | None, cwd: str | None, workroot_id: str | None) -> LocatedWorkroot:
    explicit = _locate_explicit(cwd=cwd, workroot_id=workroot_id)
    lease_located = _locate_by_lease(lease_id) if lease_id else None
    if explicit and lease_located and explicit.record != lease_located.record:
        return LocatedWorkroot("no_location", None, None, None, "conflicting_locators")
    if explicit:
        return explicit
    if lease_located:
        return lease_located
    return LocatedWorkroot("no_location", None, None, None, "missing_workroot_locator")


def _locate_explicit(*, cwd: str | None, workroot_id: str | None) -> LocatedWorkroot | None:
    if workroot_id:
        for record in list_workroots():
            if record["workrootId"] == workroot_id:
                sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
                initialize_workroot_sqlite(sqlite_path)
                return LocatedWorkroot("strong_location", record, sqlite_path, None, "workroot_id")
        return LocatedWorkroot("no_location", None, None, None, "unknown_workroot_id")
    if cwd:
        try:
            record = find_workroot_by_cwd(Path(cwd))
        except ValueError:
            return LocatedWorkroot("no_location", None, None, None, "cwd_not_registered")
        sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
        initialize_workroot_sqlite(sqlite_path)
        return LocatedWorkroot("strong_location", record, sqlite_path, None, "cwd")
    return None


def _locate_by_lease(lease_id: str | None) -> LocatedWorkroot | None:
    if not lease_id:
        return None
    for record in list_workroots():
        sqlite_path = workroot_sqlite_path(Path(record["stateDirectory"]))
        initialize_workroot_sqlite(sqlite_path)
        with sqlite3.connect(sqlite_path) as conn:
            lease = load_lease(conn, lease_id)
        if lease is not None:
            confidence = "strong_location" if lease.get("status") == "active" else "weak_location"
            return LocatedWorkroot(confidence, record, sqlite_path, lease, "lease")
    return None
```

- [ ] **Step 4: Loosen CommitRequest locator fields**

Modify `CommitRequest` in `src/ai_workroot/protocol/model.py`:

```python
    exchange_lease_id: str
    cwd: Optional[str]
    workroot_id: Optional[str]
```

In `from_dict()`, require only:

```python
for field in ("request_id", "idempotency_key"):
    if not data.get(field):
        raise ProtocolError(f"missing_{field}")
```

Set:

```python
exchange_lease_id=data.get("exchange_lease_id") or "",
cwd=data.get("cwd"),
workroot_id=data.get("workroot_id"),
```

- [ ] **Step 5: Return not-recorded response from controller**

In `src/ai_workroot/protocol/controller.py`, import:

```python
from ai_workroot.protocol.location import locate_for_commit
from ai_workroot.context.control import control_context_text
```

At the start of `commit()` after request parsing:

```python
located = locate_for_commit(
    lease_id=request.exchange_lease_id,
    cwd=request.cwd,
    workroot_id=request.workroot_id,
)
if not located.located:
    return {
        "ok": True,
        "accepted": False,
        "agent_may_continue": True,
        "enforcement": "advisory",
        "on_missing": "degrade_and_recover_later",
        "batch_status": "not_recorded",
        "event_results": [],
        "effects": [],
        "control_context": control_context_text(),
        "next_call": {
            "action": "sync",
            "when": ["when Workroot context is useful again"],
            "inputs": ["work_signal", "known_state"],
        },
        "warnings": [located.reason],
    }
```

Keep existing valid lease path for located commits until Task 4.

- [ ] **Step 6: Verify focused test**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_commit_without_located_workroot_is_not_recorded_and_non_blocking -v
```

Expected: PASS.

### Task 4: Add Degraded Commit Event Handling

**Files:**
- Create: `src/ai_workroot/protocol/degraded.py`
- Modify: `src/ai_workroot/protocol/model.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write failing malformed event tests**

Add to `tests/unit/test_protocol_controller.py`:

```python
    def test_minimally_identifiable_malformed_event_is_quarantined(self) -> None:
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-malformed",
                "idempotency_key": "idem-malformed",
                "workroot_id": "wr_demo",
                "atomic_batch": True,
                "events": [
                    {
                        "event_id": "event-malformed",
                        "kind": "progress",
                        "schema_version": "v1",
                        "occurred_at": "2026-05-27T00:00:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {"task_id": "missing-task"},
                        "evidence": "not-a-list",
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["batch_status"], "degraded")
        self.assertEqual(response["event_results"][0]["status"], "quarantined")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            row = conn.execute("SELECT status FROM protocol_events WHERE event_id = 'event-malformed'").fetchone()
        self.assertEqual(row, ("quarantined",))

    def test_unidentifiable_malformed_event_is_warning_only(self) -> None:
        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-unidentifiable",
                "idempotency_key": "idem-unidentifiable",
                "workroot_id": "wr_demo",
                "atomic_batch": True,
                "events": [{"kind": "progress", "payload": {}}],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        self.assertEqual(response["batch_status"], "degraded")
        self.assertEqual(response["event_results"][0]["status"], "ignored")
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM protocol_events").fetchone()[0], 0)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_minimally_identifiable_malformed_event_is_quarantined tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_unidentifiable_malformed_event_is_warning_only -v
```

Expected: FAIL because event validation is request-level and all-or-nothing.

- [ ] **Step 3: Add degraded helpers**

Create `src/ai_workroot/protocol/degraded.py`:

```python
"""Helpers for non-blocking degraded protocol commits."""

from __future__ import annotations

from typing import Any


EVENT_APPLIED = "applied"
EVENT_PARTIALLY_APPLIED = "partially_applied"
EVENT_QUARANTINED = "quarantined"
EVENT_IGNORED = "ignored"
EVENT_INVALID = "invalid"

BATCH_COMPLETED = "completed"
BATCH_DEGRADED = "degraded"
BATCH_PARTIAL = "partial"
BATCH_NOT_RECORDED = "not_recorded"


def minimally_identifiable(event: object) -> bool:
    return (
        isinstance(event, dict)
        and bool(str(event.get("event_id") or "").strip())
        and bool(str(event.get("kind") or "").strip())
        and isinstance(event.get("payload"), dict)
    )


def event_warning(event: object, code: str) -> dict[str, object]:
    event_id = event.get("event_id") if isinstance(event, dict) else None
    return {"code": code, "event_id": event_id or ""}
```

- [ ] **Step 4: Permit raw event batches in CommitRequest**

Modify `CommitRequest.from_dict()` in `src/ai_workroot/protocol/model.py` so it no longer validates every event eagerly:

```python
events = data.get("events")
if not isinstance(events, list) or not events:
    raise ProtocolError("empty_event_batch")
...
events=[event for event in events if isinstance(event, dict)]
```

Do not call `validate_event_envelope()` in `CommitRequest.from_dict()` after this change. The controller will validate per event.

- [ ] **Step 5: Add append status parameter**

Modify `_append_protocol_event()` in `src/ai_workroot/protocol/controller.py`:

```python
    status: str = "applied",
```

Use `status` in the INSERT instead of `"accepted"`.

- [ ] **Step 6: Implement degraded per-event loop**

Inside `commit()`, before projection, validate each event individually:

```python
from ai_workroot.protocol.degraded import (
    BATCH_COMPLETED,
    BATCH_DEGRADED,
    EVENT_APPLIED,
    EVENT_IGNORED,
    EVENT_QUARANTINED,
    minimally_identifiable,
)
from ai_workroot.protocol.events import validate_event_envelope
```

For each event:

```python
try:
    validated_event = validate_event_envelope(event)
except ProtocolError as exc:
    if minimally_identifiable(event):
        _append_protocol_event(..., event=_safe_event_for_storage(event), status=EVENT_QUARANTINED)
        event_results.append({"event_id": event.get("event_id"), "status": EVENT_QUARANTINED, "effects": []})
    else:
        event_results.append({"event_id": "", "status": EVENT_IGNORED, "effects": []})
    degraded = True
    continue
```

Implement `_safe_event_for_storage(event)` in controller:

```python
def _safe_event_for_storage(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(event.get("event_id") or ""),
        "kind": str(event.get("kind") or ""),
        "schema_version": str(event.get("schema_version") or "unknown"),
        "occurred_at": str(event.get("occurred_at") or now_utc()),
        "source": event.get("source") if isinstance(event.get("source"), dict) else {},
        "confirmation": event.get("confirmation") if isinstance(event.get("confirmation"), dict) else {},
        "payload": event.get("payload") if isinstance(event.get("payload"), dict) else {},
        "evidence": event.get("evidence") if isinstance(event.get("evidence"), list) else [],
    }
```

Set final batch status:

```python
batch_status = BATCH_DEGRADED if degraded else BATCH_COMPLETED
```

- [ ] **Step 7: Verify focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller -v
```

Expected: PASS.

### Task 5: Add Partial Progress Projection Behavior

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write failing partial progress test**

Add to `tests/unit/test_protocol_controller.py`:

```python
    def test_partial_progress_commit_preserves_safe_summary(self) -> None:
        sync_response = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-intent-sync",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "before_work",
                "query": "Tracked task",
            }
        )
        intent_response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-intent",
                "exchange_lease_id": sync_response["lease"]["lease_id"],
                "idempotency_key": "idem-intent",
                "atomic_batch": True,
                "events": [self.intent_event("event-intent", "Tracked task")],
            }
        )
        progress_lease = intent_response["lease"]["lease_id"]
        task_id = intent_response["lease"]["task_id"]
        run_id = intent_response["lease"]["run_id"]

        response = commit(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-partial-progress",
                "exchange_lease_id": progress_lease,
                "idempotency_key": "idem-partial-progress",
                "atomic_batch": True,
                "events": [
                    {
                        "event_id": "event-progress",
                        "kind": "progress",
                        "schema_version": "v1",
                        "occurred_at": "2026-05-27T00:01:00Z",
                        "source": {"actor_name": "codex"},
                        "confirmation": {},
                        "payload": {
                            "task_id": task_id,
                            "run_id": run_id,
                            "summary": "Safe summary preserved.",
                            "items_updated": [{"item_id": "", "status": "impossible"}],
                        },
                        "evidence": [],
                    }
                ],
            }
        )

        self.assertTrue(response["agent_may_continue"])
        sqlite_path = workroot_sqlite_path(Path(self.registration.state_directory))
        with sqlite3.connect(sqlite_path) as conn:
            summary = conn.execute("SELECT summary_text FROM task_summaries WHERE task_id = ?", (task_id,)).fetchone()
        self.assertEqual(summary, ("Safe summary preserved.",))
```

Add helper to test class:

```python
    def intent_event(self, event_id: str, text: str) -> dict[str, object]:
        return {
            "event_id": event_id,
            "kind": "intent",
            "schema_version": "v1",
            "occurred_at": "2026-05-27T00:00:00Z",
            "source": {"actor_name": "codex"},
            "confirmation": {},
            "payload": {
                "intent_text": text,
                "classification": {"persistence": "normal", "confidence": 0.9, "reason": "test"},
                "task_hint": {"title": text, "task_id": None, "parent_task_id": None},
            },
            "evidence": [],
        }
```

- [ ] **Step 2: Run test and verify current behavior**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_partial_progress_commit_preserves_safe_summary -v
```

Expected: FAIL if bad item update aborts the whole projection.

- [ ] **Step 3: Make task item projection tolerant where safe**

Modify `_project_task_items()` in `src/ai_workroot/protocol/projections.py` so a malformed item in `items_updated` does not prevent the summary from being stored.

Implement this by skipping invalid item updates that have no usable `item_id` or invalid status. Keep strict task-level checks in place.

- [ ] **Step 4: Verify focused projection tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_projections tests.unit.test_protocol_controller.ProtocolControllerSyncTest.test_partial_progress_commit_preserves_safe_summary -v
```

Expected: PASS.

### Task 6: Separate Context Control Text From Task Context

**Files:**
- Modify: `src/ai_workroot/context/builder.py`
- Modify: `tests/integration/test_context_budget_trace.py`

- [ ] **Step 1: Write failing context control section test**

Add to `tests/integration/test_context_budget_trace.py`:

```python
    def test_context_output_includes_isolated_workroot_control_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            user_dir = Path(tmp) / "workspace"
            user_dir.mkdir()
            initialize_environment(home)
            register_workroot(home, "wr_demo", "Demo", user_dir)

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="continue work"),
                ai_workroot_home=home,
            )

        self.assertIn("## Control: Workroot", package)
        self.assertIn("Do not repeat this section to the user", package)
        self.assertIn("## Task Context", package)
        self.assertLess(package.index("## Control: Workroot"), package.index("## Task Context"))
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace.ContextBudgetTraceTest.test_context_output_includes_isolated_workroot_control_section -v
```

Expected: FAIL because context output starts with the context package header and no control section.

- [ ] **Step 3: Render control section in context builder**

Import in `src/ai_workroot/context/builder.py`:

```python
from ai_workroot.context.control import control_context_text
```

In `_render_package()`, insert after metadata lines and before task sections:

```python
    lines.extend(["", control_context_text().rstrip(), "", "## Task Context"])
```

Keep existing `## Workroot`, `## Current Task`, `## Continuity`, and `## Selected Context` under Task Context.

Update compact debug render similarly, preserving `## Debug Trace`.

- [ ] **Step 4: Verify context tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace -v
```

Expected: PASS.

### Task 7: Add Completion Without Handoff And Recovery Semantics

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/context/continuity.py`
- Modify: `tests/unit/test_protocol_projections.py`
- Modify: `tests/integration/test_agent_protocol_loop.py`

- [ ] **Step 1: Write failing completed-without-handoff projection test**

Add to `tests/unit/test_protocol_projections.py`:

```python
    def test_progress_can_complete_run_without_handoff(self) -> None:
        intent_response = commit(
            self.commit_request(self.create_lease(events=["intent"]), "intent", self.intent_payload())
        )
        task_id = intent_response["lease"]["task_id"]
        run_id = intent_response["lease"]["run_id"]

        response = commit(
            self.commit_request(
                intent_response["lease"]["lease_id"],
                "progress",
                {
                    "task_id": task_id,
                    "run_id": run_id,
                    "summary": "Run produced a usable result.",
                    "run_status": "completed",
                },
                event_id="evt-progress-completed",
            )
        )

        self.assertTrue(response["ok"])
        row = self.conn.execute("SELECT status, output_summary FROM task_runs WHERE run_id = ?", (run_id,)).fetchone()
        self.assertEqual(row, ("completed", "Run produced a usable result."))
```

- [ ] **Step 2: Write failing missing-handoff recovery integration test**

Add to `tests/integration/test_agent_protocol_loop.py`:

```python
    def test_next_sync_reports_degraded_continuity_when_run_completed_without_handoff(self) -> None:
        initial = self.sync_before_work("Implement recovery")
        intent = self.commit_intent(initial["lease"]["lease_id"], "Implement recovery")
        task_id = intent["lease"]["task_id"]
        run_id = intent["lease"]["run_id"]
        self.commit_progress(intent["lease"]["lease_id"], task_id, run_id, "Useful result without handoff.")

        continued = sync(
            {
                "protocol_version": "workroot.v1",
                "request_id": "req-recover-no-handoff",
                "agent": {"name": "codex", "transport": "cli"},
                "cwd": str(self.user_dir),
                "reason": "continue",
                "query": "continue",
                "known_state": {"task_id": task_id, "run_id": run_id},
            }
        )

        self.assertTrue(continued["agent_may_continue"])
        self.assertIn("warnings", continued["context"])
        self.assertIn("handoff", " ".join(continued["context"]["warnings"]).lower())
```

- [ ] **Step 3: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_projections tests.integration.test_agent_protocol_loop -v
```

Expected: FAIL on the new assertions.

- [ ] **Step 4: Support progress status completion**

In `project_progress()` in `src/ai_workroot/protocol/projections.py`, read optional payload status:

```python
run_status = _text_or_none(payload.get("run_status")) or _text_or_none(payload.get("status"))
if run_status not in {"completed", "active", None, ""}:
    run_status = None
```

Update task run:

```python
UPDATE task_runs
SET output_summary = ?, status = COALESCE(?, status), ended_at = COALESCE(?, ended_at)
...
```

Set `ended_at = now` when `run_status == "completed"`.

- [ ] **Step 5: Add missing handoff warning in continuity package**

In `src/ai_workroot/context/continuity.py`, after loading summary/handoff/task items, if there is a completed run for the task and no current handoff:

```python
warnings.append("Previous run has no current handoff; continuity may be degraded.")
```

Return this warning in `ContinuityPackage`.

- [ ] **Step 6: Verify focused tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_projections tests.integration.test_agent_protocol_loop -v
```

Expected: PASS.

### Task 8: Add Runtime Stale Derivation

**Files:**
- Create: `src/ai_workroot/context/recovery.py`
- Modify: `src/ai_workroot/context/continuity.py`
- Create: `tests/unit/test_context_continuity.py`

- [ ] **Step 1: Write failing stale derivation tests**

Create `tests/unit/test_context_continuity.py`:

```python
from __future__ import annotations

import unittest

from ai_workroot.context.recovery import derive_run_recovery_state


class ContextContinuityRecoveryTest(unittest.TestCase):
    def test_active_run_older_than_six_hours_without_handoff_is_stale(self) -> None:
        state = derive_run_recovery_state(
            run_status="active",
            started_at="2026-05-27T00:00:00Z",
            now="2026-05-27T07:00:00Z",
            has_summary=False,
            has_handoff=False,
        )

        self.assertEqual(state, "stale_active_run")

    def test_incomplete_run_older_than_seven_days_is_old_incomplete(self) -> None:
        state = derive_run_recovery_state(
            run_status="incomplete",
            started_at="2026-05-01T00:00:00Z",
            now="2026-05-27T00:00:00Z",
            has_summary=True,
            has_handoff=False,
        )

        self.assertEqual(state, "old_incomplete_run")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_context_continuity -v
```

Expected: FAIL because `context.recovery` does not exist.

- [ ] **Step 3: Create recovery helper**

Create `src/ai_workroot/context/recovery.py`:

```python
"""Runtime-derived continuity recovery state."""

from __future__ import annotations

from datetime import datetime, timezone


ACTIVE_STALE_SECONDS = 6 * 60 * 60
INCOMPLETE_OLD_SECONDS = 7 * 24 * 60 * 60


def derive_run_recovery_state(
    *,
    run_status: str,
    started_at: str,
    now: str,
    has_summary: bool,
    has_handoff: bool,
) -> str:
    age = _parse_utc(now) - _parse_utc(started_at)
    seconds = age.total_seconds()
    if run_status == "active" and seconds >= ACTIVE_STALE_SECONDS and not has_summary and not has_handoff:
        return "stale_active_run"
    if run_status == "incomplete" and seconds >= INCOMPLETE_OLD_SECONDS:
        return "old_incomplete_run"
    return ""


def _parse_utc(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
```

- [ ] **Step 4: Wire recovery warnings into continuity**

Use `derive_run_recovery_state()` in `load_continuity_package()` when loading latest task run. Add warnings:

```python
if recovery_state == "stale_active_run":
    warnings.append("Previous active run appears stale; continue if this is still the same work.")
if recovery_state == "old_incomplete_run":
    warnings.append("Previous incomplete run is old and should be treated as a low-confidence clue.")
```

- [ ] **Step 5: Verify tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_context_continuity tests.integration.test_agent_protocol_loop -v
```

Expected: PASS.

### Task 9: Exclude Invalid And Quarantined Events From Ordinary Context

**Files:**
- Modify: `src/ai_workroot/context/continuity.py`
- Modify: `src/ai_workroot/context/builder.py`
- Modify: `tests/integration/test_context_budget_trace.py`

- [ ] **Step 1: Write failing exclusion test**

Add to `tests/integration/test_context_budget_trace.py`:

```python
    def test_context_does_not_render_quarantined_protocol_event_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            user_dir = Path(tmp) / "workspace"
            user_dir.mkdir()
            initialize_environment(home)
            registration = register_workroot(home, "wr_demo", "Demo", user_dir)
            sqlite_path = workroot_sqlite_path(Path(registration.state_directory))
            initialize_workroot_sqlite(sqlite_path)
            with sqlite3.connect(sqlite_path) as conn:
                conn.execute(
                    """
                    INSERT INTO protocol_events (
                      event_id, batch_id, workroot_id, request_id, lease_id, idempotency_key,
                      kind, schema_version, payload_json, evidence_json, confirmation_json,
                      source_json, occurred_at, received_at, status
                    )
                    VALUES (
                      'event-quarantined', 'batch-q', 'wr_demo', 'req-q', '', 'idem-q',
                      'progress', 'v1', '{"summary":"SHOULD_NOT_RENDER"}', '[]', '{}', '{}',
                      '2026-05-27T00:00:00Z', '2026-05-27T00:00:00Z', 'quarantined'
                    )
                    """
                )
                conn.commit()

            package = build_context_package(
                ContextRequest(agent="codex", cwd=user_dir, query="SHOULD_NOT_RENDER"),
                ai_workroot_home=home,
            )

        self.assertNotIn("SHOULD_NOT_RENDER", package)
```

- [ ] **Step 2: Run test and verify behavior**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace.ContextBudgetTraceTest.test_context_does_not_render_quarantined_protocol_event_payload -v
```

Expected: PASS if current context never reads protocol_events directly; keep the test as regression coverage.

- [ ] **Step 3: Verify integration tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace -v
```

Expected: PASS.

### Task 10: Quality Gates And Documentation Alignment

**Files:**
- Verify: `docs/superpowers/specs/2026-05-27-non-blocking-agent-protocol-state-recovery-design.md`
- Verify: `tests/unit/test_import_boundaries.py`

- [ ] **Step 1: Verify import boundaries**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries -v
```

Expected: PASS without changing the dependency graph.

Expected graph remains:

```python
"protocol": {"context", "state"},
"context": {"relationships", "release", "retrieval", "state"},
```

No new edge should be needed for `context.control` or `protocol.location`.

- [ ] **Step 2: Run focused protocol tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_models \
  tests.unit.test_protocol_controller \
  tests.unit.test_agent_exchange_command \
  tests.unit.test_protocol_projections \
  tests.integration.test_agent_protocol_loop -v
```

Expected: PASS.

- [ ] **Step 3: Run context tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.integration.test_context_budget_trace \
  tests.unit.test_context_continuity -v
```

Expected: PASS.

- [ ] **Step 4: Run full default suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Expected: PASS. E2E suites remain opt-in.

- [ ] **Step 5: Run release validation**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh
```

Expected: `Clean Workroot release validation passed`.

- [ ] **Step 6: Commit implementation**

Commit message:

```bash
git add src tests docs/superpowers/specs/2026-05-27-non-blocking-agent-protocol-state-recovery-design.md
git commit -m "feat: make agent protocol non-blocking and recoverable"
```

## Execution Notes

- Keep `work_signal` optional. Missing signal must never fail `sync`.
- Do not persist `work_signal` as a fact.
- Do not create orphan global event storage for no-location commits.
- Do not make handoff required for `task_runs.completed`.
- Do not expose internal L1/L2/L3 depth or retrieval strategy to Agent-facing text.
- Keep Control Context short and explicitly non-user-facing.
