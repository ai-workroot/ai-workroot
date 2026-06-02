# Protocol Runtime Continuity Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix three protocol/runtime continuity defects found in review without adding entities, directories, or compatibility layers.

**Architecture:** Keep SQLite as the canonical fact store and runtime files as rebuildable read views. Keep `sync` and `commit` as the stable Agent protocol actions. Keep commit idempotency semantic-hash based while restoring `request_hash` to its literal meaning.

**Tech Stack:** Python unittest, SQLite, Workroot protocol/controller/projection modules.

---

### Task 1: Runtime Current Task Activity

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Test: `tests/integration/test_runtime_views.py`

- [ ] Write a failing integration test that creates Task A, creates newer Task B, returns to Task A, commits a handoff, and expects `tasks/current.json` to point at Task A.
- [ ] Add a projection helper that touches `tasks.updated_at` for every task-scoped durable projection.
- [ ] Call the helper from progress, handoff, asset, decision, and task state projections.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.integration.test_runtime_views -v`.

### Task 2: Agent-Specific Guidance

**Files:**
- Modify: `src/ai_workroot/context/control.py`
- Modify: `src/ai_workroot/context/builder.py`
- Test: `tests/unit/test_context_wrapper_v2.py` or `tests/smoke/test_context_cli_smoke.py`

- [ ] Write a failing test that builds context for a non-Codex agent and expects guidance to use that agent name.
- [ ] Change `workroot_guidance_text` from a fixed constant to a small renderer that accepts `agent`.
- [ ] Pass `runtime.request.agent` from the context builder.
- [ ] Run the focused context tests.

### Task 3: Commit Batch Hash Semantics

**Files:**
- Modify: `src/ai_workroot/protocol/controller.py`
- Test: `tests/unit/test_protocol_commit_reliability_v2.py`

- [ ] Write a failing test proving `request_hash` and `semantic_hash` are stored separately.
- [ ] Store canonical raw request hash in `request_hash`.
- [ ] Keep `semantic_hash` as the idempotency comparison key.
- [ ] Preserve old-row fallback where `semantic_hash` may be empty.
- [ ] Run `PYTHONPATH=src python3 -m unittest tests.unit.test_protocol_commit_reliability_v2 -v`.

### Final Verification

- [ ] Run focused tests for runtime views, context guidance, and commit reliability.
- [ ] Run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- [ ] Run `PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh`.
- [ ] Run `rg -n "[^\x00-\x7F]" src scripts -S`.
- [ ] Run source marker leakage scan for active product code.
