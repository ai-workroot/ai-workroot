# Protocol Task Continuity Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair the Workroot Agent Protocol and task-continuity loop so long-running work resumes the same task, records useful assets/indexes/views, and gives the LLM copyable protocol instructions.

**Architecture:** Keep SQLite at `<stateDirectory>/cache/workroot.sqlite` as the canonical fact store. `sync` remains read-only, `commit` remains the durable fact entrance, and derived runtime files are rebuildable read views under existing semantic directories.

**Tech Stack:** Python standard library, `sqlite3`, `argparse`, `unittest`, existing `ai_workroot.protocol`, `ai_workroot.context`, `ai_workroot.retrieval`, `ai_workroot.state`, and CLI modules.

---

## File Map

- Modify `src/ai_workroot/protocol/focus.py`: prefer current task continuity over new-work when durable markers appear.
- Modify `src/ai_workroot/protocol/projections.py`: attach duplicate intents to current tasks, reuse active runs, dedupe task items, resolve logical assets, and index text assets.
- Modify `src/ai_workroot/protocol/response.py`: use stable LLM-facing shape names, especially `continuation`.
- Modify `src/ai_workroot/protocol/packet.py`: render natural-language packet sections and exact `call.command` templates.
- Modify `src/ai_workroot/commands/agent_exchange.py`: return structured protocol responses for missing commit shape inputs and missing lease.
- Modify `src/ai_workroot/cli/main.py`: tolerate plain-text `--known-state` and `--work-signal`.
- Create `src/ai_workroot/state/runtime_views.py`: write rebuildable read views from SQLite.
- Modify `src/ai_workroot/protocol/controller.py`: refresh runtime views after commit outcomes.
- Modify `src/ai_workroot/context/builder.py`: refresh context read views after context build.
- Modify `tests/unit/test_protocol_sync_focus_v2.py`: add continuity-over-durable-marker tests.
- Modify `tests/unit/test_protocol_task_continuity_v2.py`: add duplicate intent, run reuse, task item dedupe, asset indexing tests.
- Modify `tests/unit/test_protocol_packet.py`: add command-template and stable-shape tests.
- Modify `tests/unit/test_agent_exchange_command.py`: add CLI adapter tolerance tests.
- Create `tests/integration/test_runtime_views.py`: verify read-view files.
- Modify `tests/e2e/live_task_continuity.py`: use per-round deltas and task proliferation validation.
- Modify `docs/architecture/003-runtime-layout.md`: document semantic read views and canonical SQLite.

## Task 1: Focus Resolution And Intent Attachment

**Files:**
- Modify: `src/ai_workroot/protocol/focus.py`
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `tests/unit/test_protocol_sync_focus_v2.py`
- Modify: `tests/unit/test_protocol_task_continuity_v2.py`

- [ ] **Step 1: Add failing focus test**

Add a test showing that an active task plus a durable follow-up query such as "review the founder operating plan" resolves as continuation, not new work.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2.ProtocolSyncFocusV2Test.test_durable_followup_prefers_current_active_task -v
```

Expected: FAIL because current resolver returns `new_work`.

- [ ] **Step 2: Implement focus resolver order**

Update `resolve_sync_focus()` so durable markers ask `_resolve_continuation()` before returning `new_work`. Explicit new-task markers may still create new work.

- [ ] **Step 3: Add failing duplicate intent test**

Add a test that creates a task, then commits a second similar `start_work` intent under a later lease and verifies task count stays at one and run count stays bounded.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2.ProtocolTaskContinuityV2Test.test_repeated_start_work_attaches_to_existing_task -v
```

Expected: FAIL because `project_intent()` currently derives a new task id from the second event id.

- [ ] **Step 4: Implement intent attachment and run reuse**

In `project_intent()`, resolve an existing active task from lease refs, latest active/incomplete run, latest current handoff, or normalized title/summary similarity before creating a new task. If an existing task is attached, reuse the latest active/incomplete run or create one only when none exists.

- [ ] **Step 5: Verify task continuity tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2 tests.unit.test_protocol_task_continuity_v2 -v
```

Expected: PASS.

## Task 2: Task Item Deduplication And Continuation Shape Naming

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/protocol/response.py`
- Modify: `tests/unit/test_protocol_task_continuity_v2.py`

- [ ] **Step 1: Add failing task-item dedupe test**

Add a test that commits the same done item title twice under the same task/run and verifies only one item row exists with refreshed summary.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2.ProtocolTaskContinuityV2Test.test_checkpoint_items_dedupe_by_title_under_task -v
```

Expected: FAIL because item ids are currently event-id based.

- [ ] **Step 2: Implement item lookup by normalized title**

In `_project_task_items()`, if no explicit `item_id` exists, find an existing item by normalized title under the same task and update it. Keep transition rules.

- [ ] **Step 3: Update continuation shape naming**

Change LLM-facing response shape from `continuation_checkpoint` to `continuation`; keep adapter support for old data where necessary.

- [ ] **Step 4: Verify task item and response tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2 tests.unit.test_protocol_models tests.unit.test_protocol_response_v2 -v
```

Expected: PASS.

## Task 3: Packet And CLI Adapter Repair

**Files:**
- Modify: `src/ai_workroot/protocol/packet.py`
- Modify: `src/ai_workroot/commands/agent_exchange.py`
- Modify: `src/ai_workroot/cli/main.py`
- Modify: `tests/unit/test_protocol_packet.py`
- Modify: `tests/unit/test_agent_exchange_command.py`

- [ ] **Step 1: Add failing packet command tests**

Add tests that require `packet["call"]["command"]` and rendered Markdown natural-language "Exact next call" sections for checkpoint, continuation, asset, and sync packets.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_packet -v
```

Expected: FAIL until `call.command` and rendered packet sections exist.

- [ ] **Step 2: Implement packet command templates**

Move exact CLI templates into `call.command`, keep `adapter_hint` only as compatibility if existing tests require it, and render a compact natural-language preface before JSON.

- [ ] **Step 3: Add failing CLI tolerance tests**

Add tests for plain-text `--known-state` and `--work-signal`, missing lease, and missing continuation fields.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_agent_exchange_command -v
```

Expected: FAIL until tolerant parsing and structured missing-field responses are implemented.

- [ ] **Step 4: Implement CLI tolerance**

Accept plain text JSON-object args as notes/focus. For shape-native commit calls, return protocol responses instead of raising local `ValueError` for missing lease or missing required semantic fields.

- [ ] **Step 5: Verify protocol adapter tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_packet tests.unit.test_agent_exchange_command tests.smoke.test_cli_discovery -v
```

Expected: PASS.

## Task 4: Asset Identity, Content Hash, And FTS

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/retrieval/providers/sqlite_fts.py`
- Modify: `tests/unit/test_protocol_task_continuity_v2.py`

- [ ] **Step 1: Add failing asset indexing test**

Add a test that creates a user-visible text asset, commits it twice to the same path, and verifies one logical asset, non-empty `content_hash`, one indexed file, and indexed chunks.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2.ProtocolTaskContinuityV2Test.test_asset_commit_uses_path_identity_and_indexes_text -v
```

Expected: FAIL because asset ids are currently event-derived and file chunks are not indexed.

- [ ] **Step 2: Implement path-safe asset identity**

Resolve relative paths under the registered user directory. Derive a stable asset id from normalized path when no explicit id exists. Reject path escapes as non-projecting warnings.

- [ ] **Step 3: Implement content hash and chunk indexing**

Read text assets with safe size limits, compute hash, upsert `indexed_files`, split deterministic chunks, and upsert `indexed_chunks_fts`.

- [ ] **Step 4: Verify asset tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_task_continuity_v2 tests.integration.test_context_budget_trace -v
```

Expected: PASS.

## Task 5: Runtime Read Views

**Files:**
- Create: `src/ai_workroot/state/runtime_views.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `src/ai_workroot/context/builder.py`
- Create: `tests/integration/test_runtime_views.py`
- Modify: `docs/architecture/003-runtime-layout.md`

- [ ] **Step 1: Add failing runtime view integration test**

Create a test that runs sync, commit intent, commit checkpoint, commit handoff, and context build, then asserts derived files exist under `state/`, `tasks/`, `handoffs/`, and `context/`.

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_runtime_views -v
```

Expected: FAIL because views are not written.

- [ ] **Step 2: Implement runtime view writer**

Create focused functions that read SQLite and write rebuildable JSON/Markdown views:

- `state/current.json`
- `tasks/current.json`
- `tasks/active.json`
- `handoffs/current.md`
- `handoffs/current.json`
- `assets/manifest.json`
- `relationships/summary.json`
- `indexes/manifest.json`
- `context/latest.md`
- `context/latest-trace.json`
- `diagnostics/protocol-friction.json`

- [ ] **Step 3: Wire view writer**

Call the writer after commit responses and after context build. Do not read view files as canonical input.

- [ ] **Step 4: Verify runtime tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_runtime_views tests.integration.test_context_budget_trace -v
```

Expected: PASS.

## Task 6: E2E Harness Delta Validation

**Files:**
- Modify: `tests/e2e/live_task_continuity.py`
- Modify: `tests/e2e/live_task_continuity_cases.py` if needed

- [ ] **Step 1: Add harness-level tests or focused helper tests where practical**

Extract DB summary delta comparison into deterministic helpers and test that historical quarantine does not fail a later clean round.

- [ ] **Step 2: Implement per-round delta validation**

Capture before/after summaries around each live round and validate new quarantine/invalid events, task proliferation, command friction, runtime views, and user-space pollution by delta.

- [ ] **Step 3: Update audit output**

Include command failure reasons, start-work count, task proliferation metrics, runtime view file counts, and FTS/index counts.

- [ ] **Step 4: Verify E2E harness unit path**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.live_task_continuity_cases -v
```

Expected: PASS without remote live execution unless opt-in env vars are set.

## Final Verification

- [ ] **Focused suite**

```bash
PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_sync_focus_v2 \
  tests.unit.test_protocol_task_continuity_v2 \
  tests.unit.test_protocol_packet \
  tests.unit.test_agent_exchange_command \
  tests.integration.test_runtime_views \
  tests.integration.test_agent_protocol_loop \
  tests.integration.test_context_budget_trace \
  tests.smoke.test_cli_discovery \
  -v
```

- [ ] **Full default suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

- [ ] **Optional live E2E after local suite passes**

Run the single-role 50-round live task continuity E2E only after local tests are green and without deleting the existing run artifacts.
