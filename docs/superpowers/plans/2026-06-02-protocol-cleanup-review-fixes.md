# Protocol Cleanup Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the four approved protocol cleanup issues without adding new domain entities or expanding the architecture.

**Architecture:** Keep SQLite as the canonical fact store while bounding diagnostic context persistence. Keep Workroot location owned by protocol controller/location, keep projections deterministic, keep LLM-facing protocol responses clean, and reserve non-atomic commit batches for a later protocol version.

**Tech Stack:** Python 3, unittest, SQLite, existing `ai_workroot` protocol/state/context modules.

---

### Task 1: Bound Context Package Persistence

**Files:**
- Modify: `src/ai_workroot/context/builder.py`
- Modify: `src/ai_workroot/state/sqlite.py`
- Test: `tests/integration/test_context_budget_trace.py`

- [ ] **Step 1: Write failing tests**

Add tests that build a large context package and assert:

```python
rendered = conn.execute("SELECT rendered FROM context_packages ORDER BY rowid DESC LIMIT 1").fetchone()[0]
trace = json.loads(conn.execute("SELECT debug_json FROM context_traces ORDER BY rowid DESC LIMIT 1").fetchone()[0])
self.assertLessEqual(len(rendered.encode("utf-8")), 64 * 1024)
self.assertTrue(trace["renderedPreview"]["truncated"])
self.assertEqual(trace["renderedPreview"]["maxBytes"], 64 * 1024)
```

Add a retention test that writes more than the configured maximum and verifies old `context_packages`, `context_traces`, `candidate_selections`, and `budget_trim_decisions` are pruned.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace -v
```

Expected: new tests fail because `context_packages.rendered` is currently unbounded and no preview metadata exists.

- [ ] **Step 3: Implement minimal code**

Add a bounded preview helper in `context/builder.py` and use it before inserting into `context_packages`. Add `created_at` to `context_packages` through schema creation and migration. After inserting trace data, prune old context runtime rows by `workroot_id`, keeping the latest 100 packages.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace -v
```

Expected: all context budget trace tests pass.

### Task 2: Propagate Explicit Workroot Home Through Commit and Asset Projection

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `src/ai_workroot/protocol/location.py`
- Modify: `src/ai_workroot/protocol/projections.py`
- Test: `tests/unit/test_protocol_controller.py`
- Test: `tests/unit/test_protocol_task_continuity_v2.py`

- [ ] **Step 1: Write failing tests**

Add a commit test that creates a temporary AI Workroot home without setting `AI_WORKROOT_HOME`, calls `sync(..., ai_workroot_home=home)`, then calls `commit(..., ai_workroot_home=home)` and expects the event to apply.

Add an asset test that commits an asset with explicit `ai_workroot_home=home` and verifies `indexed_files` / `indexed_chunks` are populated from the located user directory.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller tests.unit.test_protocol_task_continuity_v2 -v
```

Expected: new tests fail before implementation because commit/location/projection use the default registry.

- [ ] **Step 3: Implement minimal code**

Add `ai_workroot_home` to `commit`, `locate_for_commit`, `_locate_explicit`, and `_locate_by_lease`. Pass located `userDirectory` into `apply_projection`, then into `project_asset` and `_index_asset_file_if_text`. Remove projection-time `list_workroots()` lookup for asset indexing.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller tests.unit.test_protocol_task_continuity_v2 -v
```

Expected: tests pass.

### Task 3: Reserve Non-Atomic Commit Batches for Next Protocol Version

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Test: `tests/unit/test_protocol_controller.py`
- Document: `docs/architecture/003-runtime-layout.md`

- [ ] **Step 1: Write failing test**

Add a test where `atomic_batch=false` returns `unsupported_atomic_batch_mode`, `agent_may_continue=true`, `result.status=rejected`, and writes no `protocol_events`.

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller -v
```

Expected: new test fails because `atomic_batch=false` is currently accepted.

- [ ] **Step 3: Implement minimal code**

After parsing `CommitRequest`, reject `atomic_batch=False` with a protocol response before locating or writing durable state.

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_controller -v
```

Expected: test passes.

### Task 4: Remove Debug Pollution From Protocol Responses

**Files:**
- Modify: `src/ai_workroot/protocol/response.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Test: `tests/unit/test_protocol_response_v2.py`
- Test: `tests/unit/test_protocol_controller.py`

- [ ] **Step 1: Write failing tests**

Add tests that sync and commit responses do not contain `workroot_contract.debug`, `effects`, or `event_results`, while `state_refs` and `commit_contract` remain present.

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_response_v2 tests.unit.test_protocol_controller -v
```

Expected: new tests fail because debug is currently returned.

- [ ] **Step 3: Implement minimal code**

Remove `debug` from `workroot_contract_from_lease` output and remove response insertion of `effects` / `event_results`. Keep durable `protocol_event_effects` writes unchanged.

- [ ] **Step 4: Run tests to verify pass**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_response_v2 tests.unit.test_protocol_controller -v
```

Expected: tests pass.

### Task 5: Final Verification

**Files:**
- No additional production files unless focused tests expose regressions.

- [ ] **Step 1: Run full test suite**

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run release validation**

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src scripts/dev/validate-release.sh
```

Expected: release validation passes.

- [ ] **Step 3: Run source hygiene scans**

```bash
rg -n "[^\\x00-\\x7F]" src scripts -S
rg -n "Founder|founder|onboarding|customer|metrics|activation|executive|pricing|asset recall|cross-task" src scripts -S
```

Expected: both scans produce no output.
