# Task Owner Continuity Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent Workroot from binding durable assets and decisions to the wrong task when task ownership is ambiguous.

**Architecture:** Keep context recall broad, but make write ownership strict. `protocol/focus.py` should issue task-bound write leases only when the owner is high-confidence; otherwise it may issue a workroot-scope capture lease for assets or decisions so facts can be indexed without polluting the task graph. Projection remains responsible for writing facts from accepted leases, while tests verify the selected task owner is semantically correct.

**Tech Stack:** Python 3 standard library, SQLite, `unittest`, existing Workroot protocol controller and E2E harness.

---

### Task 1: Add Focus Regression Tests

**Files:**
- Modify: `tests/unit/test_protocol_sync_focus_v2.py`

- [ ] **Step 1: Write failing tests for strict write ownership**

Add tests showing that a new asset request with multiple active tasks must not fall back to the latest task, while explicit task language still binds to the right owner:

```python
def test_new_asset_with_multiple_tasks_uses_workroot_scope_when_owner_unclear(self) -> None:
    self.insert_task_graph(
        task_id="task-founder",
        run_id="run-founder",
        title="Founder operating task",
        summary="Founder task summary.",
        handoff_next_action="Continue founder work.",
    )
    self.insert_task_graph(
        task_id="task-engineering",
        run_id="run-engineering",
        title="Engineering task",
        summary="Runtime views are rebuildable projections, not canonical state.",
        handoff_next_action="Keep durable events authoritative before implementation resumes.",
    )

    response = self.sync_request(
        request_id="req-sync-new-asset-no-owner",
        reason="before_task_switch",
        query="Create docs/technical-risk-note.md with a compact risk note and preserve it as an asset.",
        work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
    )

    self.assertEqual(response["workroot_view"]["focus"], "workroot_capture")
    self.assertTrue(response["workroot_contract"]["commit_contract"]["durable_commit_allowed"])
    self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], None)
    self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])

def test_new_asset_with_explicit_task_language_binds_owner(self) -> None:
    self.insert_task_graph(
        task_id="task-founder",
        run_id="run-founder",
        title="Founder operating task",
        summary="Founder task summary.",
        handoff_next_action="Continue founder work.",
    )
    self.insert_task_graph(
        task_id="task-engineering",
        run_id="run-engineering",
        title="Engineering continuity task",
        summary="Inspect protocol continuity, runtime views, and asset indexing behavior.",
        handoff_next_action="Keep durable events authoritative before implementation resumes.",
    )

    response = self.sync_request(
        request_id="req-sync-new-asset-clear-owner",
        reason="before_task_switch",
        query="Create engineering continuity task docs/technical-risk-note.md with a compact risk note and preserve it as an asset.",
        work_signal={"phase": "switching", "work_kind": "task", "intended_action": "plan"},
    )

    self.assertEqual(response["workroot_view"]["focus"], "continuation")
    self.assertEqual(response["workroot_contract"]["state_refs"]["task_ref"], "task-engineering")
    self.assertIn("asset", response["workroot_contract"]["commit_contract"]["allowed_commit_kinds"])
```

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2.ProtocolSyncFocusV2Test.test_new_asset_with_multiple_tasks_requires_clear_owner tests.unit.test_protocol_sync_focus_v2.ProtocolSyncFocusV2Test.test_new_asset_with_explicit_task_language_binds_owner -v
```

Expected: at least the unclear-owner test fails because the current code binds to the latest task.

### Task 2: Make Asset Ownership Strict

**Files:**
- Modify: `src/ai_workroot/protocol/focus.py`
- Test: `tests/unit/test_protocol_sync_focus_v2.py`

- [ ] **Step 1: Remove latest-task fallback for asset continuation**

Change `_resolve_asset_continuation()` so ambiguous asset requests become workroot-scope capture unless `_clear_top_candidate()` finds a clear semantic owner. Do not call `_latest_current_normal_task_candidate()` from this function.

- [ ] **Step 2: Require stronger clear-owner threshold**

Keep existing task and asset matching, but make task-bound asset write binding require a clear top candidate with enough semantic score. The owner may come from explicit task language, an existing asset path owner, or clear task title/goal/summary overlap.

- [ ] **Step 3: Support workroot-scope asset projection**

Allow an accepted workroot-scope asset event to create or update the asset, index its text, and create a context candidate with `workroot` domains. It must not create a task relationship edge.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2.ProtocolSyncFocusV2Test.test_new_asset_with_multiple_tasks_requires_clear_owner tests.unit.test_protocol_sync_focus_v2.ProtocolSyncFocusV2Test.test_new_asset_with_explicit_task_language_binds_owner -v
```

Expected: both tests pass.

### Task 3: Align Existing Tests With Strict Ownership

**Files:**
- Modify: `tests/unit/test_protocol_sync_focus_v2.py`

- [ ] **Step 1: Update old fallback tests**

Replace the old expectation that a new asset with multiple tasks binds to the latest task. Cross-task summary requests should remain ambiguous or unbound unless the request clearly names a task.

- [ ] **Step 2: Run all focus tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_sync_focus_v2 -v
```

Expected: all focus tests pass.

### Task 4: Add E2E Ownership Assertions

**Files:**
- Modify: `tests/e2e/live_task_continuity.py`
- Modify: `tests/e2e/live_task_continuity_cases.py`

- [ ] **Step 1: Extend `LiveRoundScript` with expected asset owner**

Add an optional `expected_asset_owners` field mapping asset path to expected task title token or `workroot`.

- [ ] **Step 2: Include asset owner rows in DB summary**

Add a summary helper that returns asset path to owning task titles through `relationship_edges`. The E2E harness should detect wrong task ownership, not only asset existence.

- [ ] **Step 3: Add mixed-complexity ownership expectations**

Set expectations:

```text
results/operating-brief.md -> founder
docs/technical-risk-note.md -> engineering
results/customer-interview-plan.md -> founder
reports/research-synthesis.md -> metrics
results/executive-summary.md -> workroot
```

- [ ] **Step 4: Run E2E harness unit tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest tests.e2e.live_task_continuity_cases -v
```

Expected: harness tests pass and include a case that fails on wrong asset ownership.

### Task 5: Full Verification

**Files:**
- No source edits expected.

- [ ] **Step 1: Run full unit/integration tests**

Run:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 2: Run release validation**

Run:

```bash
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH=src scripts/dev/validate-release.sh
```

Expected: release validator passes.

- [ ] **Step 3: Run source hygiene scan**

Run:

```bash
rg -n "[\\u4e00-\\u9fff]" src scripts -S
rg -n "founder|operator|customer|interview|prospect|paid pilot|operating brief|executive summary|research synthesis|technical risk" src scripts -S
```

Expected: no Chinese in `src/` or `scripts/`; no E2E scenario business text in active source.
