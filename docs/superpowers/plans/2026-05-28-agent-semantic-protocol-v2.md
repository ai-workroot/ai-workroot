# Agent Semantic Protocol v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved `0.9.531` Workroot Agent semantic protocol v2: clean response envelope, read-mostly context wrapper, sync focus resolution, reliable commit transactions, canonical task continuity projections, and non-blocking Agent behavior.

**Architecture:** Keep the existing `cli -> commands -> protocol -> projections/context/state` layering. Add small protocol helpers inside `src/ai_workroot/protocol/` for response construction and focus classification; keep durable writes centralized in `protocol/controller.py`; keep storage schema upgrades in `state/sqlite.py`; keep context rendering read-mostly in `context/builder.py`.

**Tech Stack:** Python 3 standard library, `argparse`, `sqlite3`, `unittest`, existing Workroot state registry and SQLite schema helpers.

---

## File Structure

- Create `src/ai_workroot/protocol/response.py`
  - Owns v2 response envelope constants and builders.
  - Ensures no top-level `lease`, `state_vector`, `contract`, or `observed_versions`.
- Create `src/ai_workroot/protocol/focus.py`
  - Owns runtime-only interaction classification and accepted-projection focus resolution.
  - Reads `tasks`, `task_runs`, `task_summaries`, `handoffs`, and `task_items`; does not write facts.
- Modify `src/ai_workroot/protocol/controller.py`
  - Rewire `sync` to use focus classification and v2 responses.
  - Rewire `commit` to use `BEGIN IMMEDIATE`, semantic idempotency, safe lease decisioning, all-or-none projection, terminal `response_json`, and v2 responses.
- Modify `src/ai_workroot/protocol/lease.py`
  - Add local state version scopes, atomic state version bump, and a lease safety decision that compares versions before expiration policy.
- Modify `src/ai_workroot/protocol/events.py`
  - Add semantic commit normalization/hash and canonical event validation helpers.
- Modify `src/ai_workroot/protocol/projections.py`
  - Align run/task statuses, `context:task:<id>` version bumps, incomplete run handling, `safe_to_stop` completion behavior, and strict canonical progress schema.
- Modify `src/ai_workroot/commands/agent_exchange.py`
  - Keep shorthand conversion at command-adapter boundary; support `done/open/blocked` shorthand mapping into canonical `items_created`.
- Modify `src/ai_workroot/context/control.py`
  - Keep the Work Signal capsule concise and model-readable; avoid JSON-only protocol text.
- Modify `src/ai_workroot/context/continuity.py`
  - Return accepted projection continuity fields in the v2 `task_context` shape.
- Modify `src/ai_workroot/context/builder.py`
  - Ensure `workroot context` is read-mostly and tells Agent to call `workroot agent sync` before durable commit.
- Modify `src/ai_workroot/state/sqlite.py`
  - Add/upgrade `protocol_commit_batches` fields: `semantic_hash`, `normalized_request_json`, `created_at`, `error_json`.
  - Add `updated_by_event_id` and `reason` to `state_versions`.
  - Add schema marker `009-agent-protocol-task-continuity`.
- Modify `src/ai_workroot/__init__.py` and `src/ai_workroot/state/model.py`
  - Align package/environment version to `0.9.531`.
- Modify tests under `tests/unit/`, `tests/integration/`, and `tests/smoke/`
  - Replace old response shape expectations with v2 envelope expectations.
  - Add focused RED tests before each implementation block.

Do not create commits during this execution pass; the branch already contains prior uncommitted work that the user wants to review together.

---

### Task 1: Response Envelope Clean Break

**Files:**
- Create: `src/ai_workroot/protocol/response.py`
- Modify: `src/ai_workroot/protocol/errors.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Test: `tests/unit/test_protocol_response_v2.py`
- Test: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write failing envelope tests**

Add tests that call `sync` and assert:

```python
for key in (
    "schema_version",
    "protocol_version",
    "server_version",
    "ok",
    "agent_may_continue",
    "control_context",
    "work_focus",
    "task_context",
    "directive",
    "continuation_contract",
    "next_call",
    "result",
    "recovery",
    "error",
    "machine_contract",
):
    self.assertIn(key, response)
for removed in ("lease", "state_vector", "contract", "observed_versions"):
    self.assertNotIn(removed, response)
self.assertEqual(response["schema_version"], "workroot.agent_semantic_response.v1")
self.assertEqual(response["protocol_version"], "workroot.v1")
self.assertEqual(response["server_version"], "0.9.531")
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_response_v2 -q
```

Expected: FAIL because `protocol.response` does not exist and current responses still expose old top-level fields.

- [ ] **Step 3: Implement v2 response builders**

Implement `semantic_response()`, `result_payload()`, `continuation_contract()`, `machine_contract()`, and helper response constructors in `src/ai_workroot/protocol/response.py`. Update `protocol_error_response()` so parseable protocol errors use the same top-level envelope.

- [ ] **Step 4: Rewire sync/commit response construction**

Replace `_sync_response()`, `_not_recorded_response()`, and commit response literals in `controller.py` with the new response builders. Preserve machine-only IDs under `machine_contract.debug_refs` and lease/state version details under `continuation_contract.lease_id` and `machine_contract`.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_response_v2 tests.unit.test_protocol_controller -q
```

Expected: PASS for new response tests after updating legacy assertions to v2 shape.

---

### Task 2: Read-Mostly Context Wrapper and Version Alignment

**Files:**
- Modify: `src/ai_workroot/context/builder.py`
- Modify: `src/ai_workroot/context/control.py`
- Modify: `src/ai_workroot/commands/build_context.py`
- Modify: `src/ai_workroot/__init__.py`
- Modify: `src/ai_workroot/state/model.py`
- Test: `tests/unit/test_context_wrapper_v2.py`
- Test: `tests/smoke/test_clean_cli_workflow.py`

- [ ] **Step 1: Write failing context wrapper tests**

Add tests that call `build_context()` after initializing a workroot and assert no row is added to `exchange_leases`, `protocol_events`, `tasks`, or `task_runs`. Assert rendered context contains `workroot agent sync` guidance and does not contain `observed_versions`, `state_vector`, or SQLite paths.

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_context_wrapper_v2 -q
```

Expected: FAIL if the context wrapper lacks the v2 control guidance or leaks machine internals.

- [ ] **Step 3: Implement read-mostly context behavior**

Keep context construction read-only for protocol facts. Update control text so the model sees a concise private capsule:

```text
Use privately. Do not repeat to the user.
Continue helping if Workroot cannot persist.
Call `workroot agent sync` before durable commits.
Commit only summary-level facts at meaningful checkpoints.
```

- [ ] **Step 4: Align version constants**

Set `src/ai_workroot/__init__.py` and `WorkrootEnvironment.version` to `0.9.531`.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_context_wrapper_v2 tests.smoke.test_clean_cli_workflow -q
```

Expected: PASS after smoke expectations are updated to the v2 response shape.

---

### Task 3: Sync Classification, Focus Resolver, and Work Signal

**Files:**
- Create: `src/ai_workroot/protocol/focus.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `src/ai_workroot/context/continuity.py`
- Test: `tests/unit/test_protocol_sync_focus_v2.py`
- Test: `tests/integration/test_agent_protocol_loop.py`

- [ ] **Step 1: Write failing sync/focus tests**

Add tests for:

```text
sync unavailable returns ok=true, agent_may_continue=true, result.status=not_recorded
quick signal + quick query returns answer_without_persistence with no lease
quick signal + durable query is overridden and returns commit_required
continue without known_state uses latest current handoff
continue without known_state uses latest active/incomplete run
invalid known_state does not claim active task
ambiguous focus disables durable commit
guarded action disables durable commit and asks user
sync never creates Task/TaskRun/Handoff/TaskSummary
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2 -q
```

Expected: FAIL because current `sync` creates old response shape and requires `known_state.task_id` for continuation.

- [ ] **Step 3: Implement focus classification**

In `protocol/focus.py`, implement deterministic marker-based classification using `reason`, `query`, `known_state`, `work_signal`, and accepted projection candidates. Return a `FocusResolution` carrying `kind`, `confidence`, `summary`, `why`, `task_id`, `run_id`, `directive_type`, and allowed commit kinds.

- [ ] **Step 4: Rewire sync pipeline**

Update `controller.sync()`:

```text
validate request
locate workroot or return unavailable response
open SQLite
classify interaction
resolve focus from accepted projections
build task_context
mint lease only when durable_commit_allowed=true and focus confidence is high/medium or new durable work needs intent
return v2 response
```

- [ ] **Step 5: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2 tests.integration.test_agent_protocol_loop -q
```

Expected: PASS with integration loop updated to read `continuation_contract.lease_id` and `machine_contract.debug_refs`.

---

### Task 4: Commit Reliability, Idempotency, and Lease Safety

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `src/ai_workroot/protocol/events.py`
- Modify: `src/ai_workroot/protocol/lease.py`
- Modify: `src/ai_workroot/state/sqlite.py`
- Test: `tests/unit/test_protocol_commit_reliability_v2.py`
- Test: `tests/unit/test_protocol_idempotency.py`
- Test: `tests/unit/test_protocol_lease.py`
- Test: `tests/unit/test_protocol_schema.py`

- [ ] **Step 1: Write failing reliability tests**

Add tests for:

```text
BEGIN IMMEDIATE is used
idempotency lookup is inside transaction
same idempotency key + same semantic hash returns stored response_json exactly
same idempotency key + different semantic hash returns idempotency_key_conflict
semantic hash excludes request_id
semantic hash excludes generated event_id and occurred_at
semantic hash includes exchange_lease_id
applying/null response returns recovery response without projection
expired lease + unchanged versions applies progress with warning
expired lease + changed versions returns resync_required without projection
state transition never safe-projects under expired lease
state_versions scopes are local: event_log, workroot, task:<id>, run:<id>, context:task:<id>
state_versions bump uses atomic upsert increment
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_commit_reliability_v2 -q
```

Expected: FAIL because current commit uses `request_hash`, `BEGIN`, old batch statuses, and old lease expiration handling.

- [ ] **Step 3: Upgrade schema**

In `state/sqlite.py`, create new columns if missing:

```sql
ALTER TABLE protocol_commit_batches ADD COLUMN semantic_hash TEXT;
ALTER TABLE protocol_commit_batches ADD COLUMN normalized_request_json TEXT;
ALTER TABLE protocol_commit_batches ADD COLUMN created_at TEXT;
ALTER TABLE protocol_commit_batches ADD COLUMN error_json TEXT;
ALTER TABLE state_versions ADD COLUMN updated_by_event_id TEXT;
ALTER TABLE state_versions ADD COLUMN reason TEXT;
```

For fresh databases, define required v2 columns directly and insert migration marker `009-agent-protocol-task-continuity`.

- [ ] **Step 4: Implement semantic hash**

Add `semantic_commit_request()` and `semantic_commit_hash()` to `protocol/events.py`. Exclude `request_id`, transport/debug metadata, generated event ids, and generated timestamps; include `protocol_version`, `action=commit`, resolved `workroot_id`, `exchange_lease_id`, `atomic_batch`, event kind/schema/payload/evidence/confirmation.

- [ ] **Step 5: Implement transaction algorithm**

In `controller.commit()`:

```text
locate workroot, return not_recorded if unavailable
open connection
BEGIN IMMEDIATE
compute semantic hash using resolved workroot_id
lookup protocol_commit_batches by workroot_id + idempotency_key
same hash + response_json => return stored JSON exactly
same hash + applying/null => return recovery response, no projection
different hash => return idempotency_key_conflict
insert applying batch
validate lease inside transaction
validate all canonical events
decide projection safety
append events
apply all projections or none
bump state_versions in same transaction
build terminal v2 response
store response_json and terminal status
COMMIT
```

- [ ] **Step 6: Implement lease safety**

Compare current versions to observed versions before expiration policy. Permit expired-but-version-stable `progress` and `handoff` to project with `warnings=["lease_expired_safe_projection"]`; reject/resync expired state transitions and changed-version leases.

- [ ] **Step 7: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_commit_reliability_v2 tests.unit.test_protocol_idempotency tests.unit.test_protocol_lease tests.unit.test_protocol_schema -q
```

Expected: PASS with all legacy expectations updated to v2 status/result fields.

---

### Task 5: Task Continuity Canonical Projections

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `src/ai_workroot/context/continuity.py`
- Test: `tests/unit/test_protocol_task_continuity_v2.py`
- Test: `tests/unit/test_agent_exchange_command.py`
- Test: `tests/unit/test_protocol_projections.py`

- [ ] **Step 1: Write failing task continuity tests**

Add tests for:

```text
Task status does not accept completed
Task close uses status=closed and close_reason=completed metadata
TaskRun status accepts completed and incomplete
completed run returns safe_to_stop and no required handoff
completed run without handoff returns continuity warning
incomplete run recommends/needs handoff
temporary intent creates inbox Task
temporary promote mutates same Task metadata
temporary promote does not create a new Task
progress canonical items_created/items_updated project
progress shorthand done/open/blocked maps only in adapter
projection rejects shorthand payload if bypassing adapter
state task completed status is rejected
state task closed status is accepted
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2 -q
```

Expected: FAIL on incomplete run, closed close_reason, shorthand open/blocked mapping, and v2 response shape.

- [ ] **Step 3: Implement projection alignment**

Update projection logic:

```text
progress.run_status supports active/completed/incomplete
completed run -> directive safe_to_stop, no required_before_stop, optional handoff warning
incomplete run -> directive continue_task, required_before_stop includes handoff
Task.status rejects completed and accepts closed
Task close_reason is stored in metadata_json when provided
context:task:<id> is bumped for context-changing facts
event_log is bumped for accepted protocol events
```

- [ ] **Step 4: Keep shorthand at adapter boundary**

Update `build_commit_request_from_shorthand()` so `--done`, `--open`, and `--blocked` produce canonical `items_created`. Ensure raw `done/open/blocked` in a canonical event is rejected by projection.

- [ ] **Step 5: Verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2 tests.unit.test_agent_exchange_command tests.unit.test_protocol_projections -q
```

Expected: PASS.

---

### Task 6: End-to-End CLI Loop and Full Verification

**Files:**
- Modify: `tests/smoke/test_clean_cli_workflow.py`
- Modify: `tests/integration/test_agent_protocol_loop.py`
- Modify: `tests/e2e/live_protocol_cases.py` if assertions depend on old response shape.

- [ ] **Step 1: Update CLI loop assertions**

Update all tests and smoke flows to use:

```python
lease_id = response["continuation_contract"]["lease_id"]
task_id = response["machine_contract"]["debug_refs"]["task_id"]
run_id = response["machine_contract"]["debug_refs"]["run_id"]
status = response["result"]["status"]
```

Never assert old top-level `lease`, `contract`, `state_vector`, or `batch_status`.

- [ ] **Step 2: Run focused protocol suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_response_v2 \
  tests.unit.test_protocol_sync_focus_v2 \
  tests.unit.test_protocol_commit_reliability_v2 \
  tests.unit.test_protocol_task_continuity_v2 \
  tests.unit.test_protocol_models \
  tests.unit.test_protocol_schema \
  tests.unit.test_protocol_lease \
  tests.unit.test_protocol_idempotency \
  tests.unit.test_protocol_controller \
  tests.unit.test_protocol_projections \
  tests.unit.test_agent_exchange_command \
  tests.integration.test_agent_protocol_loop \
  tests.smoke.test_clean_cli_workflow \
  -q
```

Expected: PASS.

- [ ] **Step 3: Run full test suite**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -q
```

Expected: PASS or report pre-existing unrelated failures with exact file/test names.

- [ ] **Step 4: Run release validation if available**

Run:

```bash
scripts/dev/validate-release.sh
```

Expected: PASS. If the script is unavailable or requires an external dependency, report the blocker and the tests already run.

- [ ] **Step 5: Final review**

Inspect:

```bash
git diff -- src/ai_workroot tests docs/superpowers/plans
git status --short
```

Confirm:

```text
No top-level response compatibility aliases remain.
sync creates no durable task facts.
commit is the only durable Agent fact entry.
commit idempotency replay returns stored response exactly.
Task/TaskRun/temporary inbox semantics match v2.
context wrapper is read-mostly and model-facing.
```
