# Context Guide Amendment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the 0.9.529 Context Guide amendment: configurable modes, agent-aware token budgets, context confidence, richer debug traces, explicit Deep Mode, and short Native Agent Entry behavior.

**Architecture:** Keep the existing Python standard-library implementation and managed-state layout. Add a focused Context Guide configuration layer used by state initialization, CLI, Context Guide, debug trace, and doctor. Do not add remote calls, vector dependencies, full directory scans, or writes into the user-selected directory.

**Tech Stack:** Python standard library, `unittest`, SQLite FTS, Markdown/JSON managed state.

---

## File Map

- Modify: `scripts/workroot_context.py`
  - Add `ContextGuideConfig`, mode/budget resolution, confidence calculation, metadata rendering, Quality/Deep trace fields.
- Modify: `scripts/workroot_state.py`
  - Write the new `state/runtime-hints.json` schema during initialization.
- Modify: `scripts/workroot_cli.py`
  - Add `workroot context --mode`, `--deep`, `--target-tokens`, and `--max-latency-ms`.
- Modify: `scripts/workroot_doctor.py`
  - Validate runtime hints and report missing hints as built-in default behavior.
- Modify: `scripts/workroot_sqlite.py`
  - Add `domains` to `context_candidates_fts`.
- Modify: `scripts/workroot_candidates.py`
  - Populate candidate FTS `domains`.
- Modify: `scripts/workroot_agent_entry.py`
  - Keep entry files short and include context-failure fallback instructions.
- Modify tests:
  - `tests/test_workroot_context.py`
  - `tests/test_workroot_debug_trace.py`
  - `tests/test_workroot_doctor_0529.py`
  - `tests/test_workroot_init_cli.py`
  - `tests/test_workroot_candidates.py`

## Task 1: Runtime Hints and Budget Resolution

**Files:**
- Modify: `scripts/workroot_context.py`
- Modify: `scripts/workroot_state.py`
- Test: `tests/test_workroot_context.py`
- Test: `tests/test_workroot_state.py`

- [ ] **Step 1: Write failing tests**

Add tests asserting initialized `runtime-hints.json` contains `contextGuide.defaultMode`, `agentBudgets.codex`, `agentBudgets.claude`, `modes.standard`, `modes.quality`, and hot-path remote/vector denial fields. Add Context Guide tests asserting Codex and Claude receive different budget metadata.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_workroot_state tests.test_workroot_context -v
```

Expected: new tests fail because the old runtime hints schema and Context Package metadata are missing.

- [ ] **Step 3: Implement config and metadata**

Add default runtime hints schema in `workroot_context.py`, load `state/runtime-hints.json` when available, fall back to defaults when missing or malformed, and render `## Context Metadata`.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workroot_state tests.test_workroot_context -v
```

Expected: tests pass.

## Task 2: CLI Modes, Deep, and Override Bounds

**Files:**
- Modify: `scripts/workroot_cli.py`
- Modify: `scripts/workroot_context.py`
- Test: `tests/test_workroot_context.py`

- [ ] **Step 1: Write failing CLI tests**

Add subprocess tests for `workroot context --mode quality --debug`, `workroot context --deep`, and invalid token override beyond the configured hard limit.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_workroot_context -v
```

Expected: new tests fail because CLI flags are not yet accepted.

- [ ] **Step 3: Implement CLI flag wiring**

Add parser flags, extend `ContextRequest`, resolve requested/effective mode, and reject invalid budget overrides with actionable errors.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workroot_context -v
```

Expected: tests pass.

## Task 3: Confidence, Quality, and Debug Trace

**Files:**
- Modify: `scripts/workroot_context.py`
- Test: `tests/test_workroot_debug_trace.py`

- [ ] **Step 1: Write failing debug trace tests**

Add tests asserting debug trace includes `requestedMode`, `contextMode`, `modeSwitchReason`, `confidence`, `confidenceReasons`, `tokenBudget.source`, `qualitySoftLimitMs`, `deepExplicitlyRequested`, and candidate quality counts.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_workroot_debug_trace -v
```

Expected: new tests fail because trace fields are missing.

- [ ] **Step 3: Implement confidence and trace fields**

Compute confidence from active task, candidate counts, stale/filtered counts, candidate confidence, and FTS result quality. Escalate Standard to Quality locally when low confidence or when explicitly requested. Record trace fields.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workroot_debug_trace -v
```

Expected: tests pass.

## Task 4: Candidate FTS Domains and Doctor Checks

**Files:**
- Modify: `scripts/workroot_sqlite.py`
- Modify: `scripts/workroot_candidates.py`
- Modify: `scripts/workroot_doctor.py`
- Test: `tests/test_workroot_candidates.py`
- Test: `tests/test_workroot_doctor_0529.py`

- [ ] **Step 1: Write failing tests**

Add candidate tests verifying `context_candidates_fts` has a `domains` column and can search domain text. Add doctor tests for valid, missing, and malformed runtime hints.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_workroot_candidates tests.test_workroot_doctor_0529 -v
```

Expected: new tests fail because FTS domains and runtime hints doctor checks are missing.

- [ ] **Step 3: Implement schema and doctor checks**

Update SQLite schema and upsert logic for domain FTS. Add doctor runtime hints validation that passes when hints are absent, fails on malformed hints, and passes on valid hints.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workroot_candidates tests.test_workroot_doctor_0529 -v
```

Expected: tests pass.

## Task 5: Native Entry and Release Gates

**Files:**
- Modify: `scripts/workroot_agent_entry.py`
- Modify: `tests/test_workroot_agent_entry.py`
- Modify: `tests/test_0529_release_gates.py`

- [ ] **Step 1: Write failing tests**

Add tests confirming entry blocks stay short, include context-failure fallback instructions, and release gates check context mode/confidence/budget requirements.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_workroot_agent_entry tests.test_0529_release_gates -v
```

Expected: new tests fail until templates and gates are updated.

- [ ] **Step 3: Implement template and validation updates**

Update entry templates and release gate scans.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest tests.test_workroot_agent_entry tests.test_0529_release_gates -v
```

Expected: tests pass.

## Task 6: Final Verification

**Files:**
- All touched files.

- [ ] **Step 1: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_workroot_context tests.test_workroot_debug_trace tests.test_workroot_doctor_0529 tests.test_workroot_candidates tests.test_workroot_agent_entry tests.test_0529_release_gates tests.test_workroot_init_cli tests.test_workroot_state -v
```

Expected: tests pass.

- [ ] **Step 2: Run full clean-copy validation**

Run from a clean archive copy:

```bash
tmp=$(mktemp -d /tmp/ai-workroot-amendment-check.XXXXXX) && git archive HEAD | tar -x -C "$tmp" && cp -R docs "$tmp/docs" && cp -R scripts "$tmp/scripts" && cp -R tests "$tmp/tests" && (cd "$tmp" && python3 -m unittest discover -s tests && python3 scripts/validate_kernel.py --release && python3 -m py_compile scripts/*.py)
```

Expected: all tests pass, release validation passes, and scripts compile.

## Self-Review

- Spec coverage: Covers runtime hints, modes, budgets, confidence, CLI flags, debug trace, candidate FTS domains, doctor checks, entry file constraints, and release gates.
- Scope control: No vector DB, no remote calls, no full hot-path scans, no managed writes to user directories.
- Execution note: Implementation must use TDD for each task and avoid push, merge, tag, or release.
