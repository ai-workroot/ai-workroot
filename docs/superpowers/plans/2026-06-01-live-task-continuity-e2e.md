# Live Task Continuity E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in five-role live Codex E2E suite that audits Workroot task continuity over 10-20 rounds per role.

**Architecture:** Keep all new behavior inside the E2E harness. Register a new `live-task-continuity` runner suite, build reusable role/round scenario definitions, run Codex in sandboxed user directories, wrap the `workroot` command for command/output audit, and summarize SQLite/runtime/user-space state after every round.

**Tech Stack:** Python `unittest`, existing Workroot CLI, existing E2E sandbox safety helpers, SQLite audit queries, Codex CLI remote execution.

---

### Task 1: Harness Contract Tests

**Files:**
- Create: `tests/e2e/live_task_continuity_cases.py`
- Modify: `tests/e2e/safety_cases.py`

- [ ] **Step 1: Write failing tests**

Add tests for the scenario matrix, wrapper artifact location, runtime pollution detection, empty database summary, and runner registration.

- [ ] **Step 2: Run focused tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.e2e.live_task_continuity_cases tests.e2e.safety_cases -q
```

Expected: fail because the `live_task_continuity` module and runner suite are not implemented yet.

### Task 2: E2E Harness Module

**Files:**
- Create: `tests/e2e/live_task_continuity.py`

- [ ] **Step 1: Implement scenario definitions**

Create five role scenarios and round scripts. The default round count is 10; accepted range is 1-20.

- [ ] **Step 2: Implement audited Workroot wrapper**

Create a sandbox `run-root/bin/workroot` wrapper that writes command records and command stdout/stderr artifacts under the current round transcript directory.

- [ ] **Step 3: Implement database and user-space audit helpers**

Summarize protocol/task/asset/context tables and detect runtime pollution while allowing declared user-visible asset paths.

- [ ] **Step 4: Implement live runner**

Initialize one Workroot per role, run Codex per round, preserve transcripts, audit after each round, and write summary JSON plus Markdown audit.

### Task 3: Runner Integration

**Files:**
- Modify: `tests/e2e/runner.py`

- [ ] **Step 1: Register suite**

Add `live-task-continuity -> tests.e2e.live_task_continuity_cases`.

- [ ] **Step 2: Remote opt-in**

Require `AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1` for this suite.

- [ ] **Step 3: Rounds option**

Add `--rounds` to set `AI_WORKROOT_E2E_LIVE_TASK_ROUNDS` for the selected live task suite.

### Task 4: Verification

**Files:**
- Test-only changes

- [ ] **Step 1: Run focused harness tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.e2e.live_task_continuity_cases tests.e2e.safety_cases -q
```

- [ ] **Step 2: Run protocol-focused tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest tests.e2e.live_protocol_cases tests.e2e.live_task_continuity_cases tests.e2e.safety_cases -q
```

- [ ] **Step 3: Run full local tests if focused tests pass**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -q
```

- [ ] **Step 4: Optional live run**

```bash
AI_WORKROOT_RUN_E2E=1 AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m tests.e2e.runner --suite live-task-continuity --rounds 10
```
