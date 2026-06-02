# Workroot Agent Protocol Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Cleanly reshape the Agent protocol response around `sync`/`commit`, `workroot_guidance`, `workroot_contract`, and `workroot_view`.

**Architecture:** Keep the existing `protocol` package and SQLite task projections. Replace implementation-shaped response fields with a semantic response envelope, generate private LLM guidance as text, and provide one structured Workroot contract for Agent runtimes. Keep durable facts flowing only through `commit`.

**Tech Stack:** Python stdlib, argparse CLI, sqlite3, unittest, existing Workroot state/registry/layout modules.

**Status:** Implemented on `feat/0.9.531-agent-protocol-task-continuity`. Follow-up patch converged startup context onto the protocol focus/view path, added `continuation` CLI shorthand, and aligned `work_signal` wording.

---

## File Structure

- Modify `src/ai_workroot/protocol/response.py`: response envelope, guidance builder, contract builder, compact Workroot view.
- Modify `src/ai_workroot/protocol/controller.py`: call the new response builders and stop returning old top-level fields.
- Modify `src/ai_workroot/protocol/errors.py`: protocol errors should use the new envelope.
- Modify `src/ai_workroot/context/control.py`: update startup guidance wording to the new sync/commit abstraction.
- Modify `src/ai_workroot/context/builder.py`: render startup guidance with the new language and reduce old control wording.
- Modify tests under `tests/unit`, `tests/integration`, `tests/smoke`, and `tests/e2e` to assert the new contract.

## Task 1: Response Envelope Clean Break

**Files:**
- Modify: `src/ai_workroot/protocol/response.py`
- Test: `tests/unit/test_protocol_response_v2.py`

- [x] **Step 1: Write failing tests for new response keys**

Add or update tests so a protocol response contains `workroot_guidance`, `workroot_contract`, and `workroot_view`, and does not contain `control_context`, `directive`, `continuation_contract`, `next_call`, or `machine_contract`.

- [x] **Step 2: Run response tests and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_response_v2 -q
```

Expected: tests fail because production code still returns the old envelope.

- [x] **Step 3: Implement new response helpers**

Update `response.py` to expose:

- `semantic_response(...)`
- `guidance_text(...)`
- `workroot_contract_from_lease(...)`
- `empty_workroot_contract()`
- `workroot_view(...)`
- `empty_workroot_view()`
- `result_payload(...)`
- `default_recovery()`

The response top-level keys must be:

```text
schema_version, protocol_version, server_version, ok, agent_may_continue,
workroot_guidance, workroot_contract, workroot_view, result, recovery, error
```

- [x] **Step 4: Run response tests and verify pass**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_response_v2 -q
```

Expected: tests pass.

## Task 2: Controller Sync/Commit Response Migration

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Test: `tests/unit/test_protocol_controller.py`
- Test: `tests/unit/test_protocol_sync_focus_v2.py`
- Test: `tests/unit/test_protocol_commit_reliability_v2.py`
- Test: `tests/unit/test_protocol_task_continuity_v2.py`

- [x] **Step 1: Update controller tests for `workroot_contract`**

Replace assertions on:

- `directive.type`
- `continuation_contract.lease_id`
- `continuation_contract.allowed_commit_kinds`
- `next_call.suggested_action`
- `machine_contract.debug_refs.task_id`

with assertions on:

- `workroot_contract.next_exchange`
- `workroot_contract.commit_contract`
- `workroot_contract.state_refs`
- `workroot_view.focus`
- `workroot_view.task_brief`
- `result.status`

- [x] **Step 2: Run controller/focus/task tests and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_controller \
  tests.unit.test_protocol_sync_focus_v2 \
  tests.unit.test_protocol_commit_reliability_v2 \
  tests.unit.test_protocol_task_continuity_v2 \
  -q
```

Expected: tests fail because controller still builds old responses.

- [x] **Step 3: Update `controller.py` response assembly**

Make `_sync_response`, `_commit_response`, `_not_recorded_response`, `_sync_unavailable_response`, and `_recovery_response` build:

- natural-language `workroot_guidance`
- structured `workroot_contract`
- compact `workroot_view`

Do not expose old top-level fields.

- [x] **Step 4: Run controller/focus/task tests and verify pass**

Run the same unittest command as Step 2.

Expected: tests pass.

## Task 3: Error Envelope Migration

**Files:**
- Modify: `src/ai_workroot/protocol/errors.py`
- Test: `tests/unit/test_protocol_response_v2.py`
- Test: `tests/unit/test_agent_exchange_command.py`
- Test: `tests/smoke/test_cli_discovery.py`

- [x] **Step 1: Update error tests**

Protocol errors should return the new response envelope with:

- `ok=false`
- `agent_may_continue=true`
- `workroot_guidance` containing a sync/retry instruction
- `workroot_contract.next_exchange.action="sync"`
- `result.status="resync_required"`
- `error.code=<expected>`

- [x] **Step 2: Run error-related tests and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_response_v2 \
  tests.unit.test_agent_exchange_command \
  tests.smoke.test_cli_discovery \
  -q
```

Expected: tests fail on old `directive`/`machine_contract` assumptions.

- [x] **Step 3: Update `protocol_error_response`**

Return the new semantic envelope and route retry guidance through `workroot_guidance` and `workroot_contract`.

- [x] **Step 4: Run error-related tests and verify pass**

Run the same unittest command as Step 2.

Expected: tests pass.

## Task 4: CLI and Shorthand Test Migration

**Files:**
- Modify: `tests/smoke/test_clean_cli_workflow.py`
- Modify: `tests/unit/test_agent_exchange_command.py`
- Modify: `tests/e2e/live_protocol.py`
- Modify: `tests/e2e/live_protocol_cases.py`

- [x] **Step 1: Update CLI tests to consume `workroot_contract`**

Lease extraction must read:

```python
response["workroot_contract"]["commit_contract"]["lease_id"]
```

Task/run refs must read:

```python
response["workroot_contract"]["state_refs"]["task_ref"]
response["workroot_contract"]["state_refs"]["run_ref"]
```

Effects must read:

```python
response["workroot_contract"]["debug"]["effects"]
```

- [x] **Step 2: Run CLI/smoke/e2e unit wrappers and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.unit.test_agent_exchange_command \
  tests.smoke.test_clean_cli_workflow \
  tests.e2e.live_protocol_cases \
  -q
```

Expected: tests fail until protocol response migration is complete.

- [x] **Step 3: Adjust CLI response expectations only**

Do not change CLI command names. Keep:

```text
workroot agent sync
workroot agent commit
```

- [x] **Step 4: Run CLI/smoke/e2e unit wrappers and verify pass**

Run the same unittest command as Step 2.

Expected: tests pass.

## Task 5: Startup Guidance Wording

**Files:**
- Modify: `src/ai_workroot/context/control.py`
- Modify: `src/ai_workroot/templates/native_agent_entry/AGENTS.md.template`
- Modify: `src/ai_workroot/templates/native_agent_entry/CLAUDE.md.template`
- Test: `tests/unit/test_agent_entry.py`
- Test: `tests/integration/test_context_budget_trace.py`
- Test: `tests/unit/test_context_wrapper_v2.py`

- [x] **Step 1: Update context tests**

Startup context should mention `Workroot Guidance`, `sync`, and `commit`, and should not teach handoff as a standalone protocol concept.

- [x] **Step 2: Run context/entry tests and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.unit.test_agent_entry \
  tests.integration.test_context_budget_trace \
  tests.unit.test_context_wrapper_v2 \
  -q
```

Expected: tests fail on old wording.

- [x] **Step 3: Update startup guidance text**

Use natural language:

- sync to align with Workroot;
- commit meaningful facts/checkpoints/current state;
- keep guidance private;
- do not expose Workroot internals to the user.

- [x] **Step 4: Run context/entry tests and verify pass**

Run the same unittest command as Step 2.

Expected: tests pass.

## Task 6: Integration Loop Migration

**Files:**
- Modify: `tests/integration/test_agent_protocol_loop.py`
- Modify: `tests/unit/test_protocol_projections.py`

- [x] **Step 1: Update integration helpers**

Helper methods should read lease/task/run/effects from `workroot_contract`.

- [x] **Step 2: Run integration/projection tests and verify failure**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.integration.test_agent_protocol_loop \
  tests.unit.test_protocol_projections \
  -q
```

Expected: tests fail before response migration completes.

- [x] **Step 3: Keep projection behavior unchanged**

Do not change task projection semantics except for response field names and guidance wording.

- [x] **Step 4: Run integration/projection tests and verify pass**

Run the same unittest command as Step 2.

Expected: tests pass.

## Task 7: Full Verification

**Files:**
- No production edits expected.

- [x] **Step 1: Run focused protocol suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_response_v2 \
  tests.unit.test_context_wrapper_v2 \
  tests.unit.test_protocol_sync_focus_v2 \
  tests.unit.test_protocol_commit_reliability_v2 \
  tests.unit.test_protocol_task_continuity_v2 \
  tests.unit.test_protocol_controller \
  tests.unit.test_protocol_projections \
  tests.integration.test_agent_protocol_loop \
  tests.smoke.test_clean_cli_workflow \
  -q
```

Expected: all tests pass.

- [x] **Step 2: Run full unittest suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Expected: all tests pass.

- [x] **Step 3: Run release validation**

Run:

```bash
PATH=.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src scripts/dev/validate-release.sh
```

Expected: validation passes.

## Self-Review

- Spec coverage: covers response contract cleanup, guidance renderer, Workroot contract, context wording, task process semantics, and tests.
- Scope: does not implement L1/L2/L3 context recall strategy.
- Clean break: old response fields are intentionally removed from the protocol response.
- Data model: no new domain entities are introduced by the bridge cleanup; existing protocol/task SQLite projections remain the fact/query model.
- Risk: changing response field names requires broad test updates, but keeps task projection behavior stable.
