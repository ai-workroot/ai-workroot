# Task Management Continuity P0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete task-related continuity by adding structured protocol errors, TaskItem process control, and Inbox/temporary Task lifecycle.

**Architecture:** Keep `sync` read-only for semantic facts and keep `commit` as the only Agent fact entry. Add task item projection inside `protocol/projections.py` transactionally after `protocol_events` append, store query models in SQLite, and keep CLI as a thin transport adapter.

**Tech Stack:** Python 3.9 standard library, `sqlite3`, `argparse`, `dataclasses`, `unittest`, existing `ai_workroot.protocol`, `ai_workroot.state`, and `ai_workroot.context` packages.

---

## File Map

- Modify: `src/ai_workroot/protocol/errors.py`  
  Add reusable structured protocol error response helper.
- Modify: `src/ai_workroot/protocol/controller.py`  
  Return structured protocol errors from sync/commit validation and support P0.1 projections.
- Modify: `src/ai_workroot/protocol/projections.py`  
  Support temporary intent, TaskItem progress projections, promote/archive state transitions.
- Modify: `src/ai_workroot/context/continuity.py`  
  Include open and recent TaskItems in sync continuity context.
- Modify: `src/ai_workroot/state/sqlite.py`  
  Add `task_items` table and schema verification.
- Modify: `src/ai_workroot/work/model.py`  
  Add `TaskItem` model and status constants.
- Modify: `src/ai_workroot/work/operations.py`  
  Add transaction-friendly TaskItem helpers for non-protocol callers while keeping protocol direct SQL.
- Modify: `tests/unit/test_protocol_models.py`
- Modify: `tests/unit/test_protocol_schema.py`
- Modify: `tests/unit/test_protocol_projections.py`
- Modify: `tests/unit/test_agent_exchange_command.py`
- Modify: `tests/unit/test_work_operations.py`
- Modify: `tests/integration/test_agent_protocol_loop.py`
- Create: `docs/superpowers/specs/2026-05-26-task-management-continuity-p0-1-design.md`

## Tasks

### Task 1: Structured Protocol Error Responses

**Files:**
- Modify: `src/ai_workroot/protocol/errors.py`
- Modify: `src/ai_workroot/protocol/controller.py`
- Modify: `tests/unit/test_protocol_controller.py`
- Modify: `tests/unit/test_agent_exchange_command.py`

- [ ] Write failing tests:
  - `sync({"request_id":"bad"})` returns `ok=false`, `error.code=missing_protocol_version`, `directive.type=resync_required`.
  - `commit({"request_id":"bad"})` returns the same structured shape.
  - `run_commit_request()` returns JSON protocol error for malformed protocol request files.
- [ ] Run focused tests and verify failure.
- [ ] Add `protocol_error_response(code, details=None, next_action=None)` in `protocol/errors.py`.
- [ ] Catch `ProtocolError` around `SyncRequest.from_dict()` and `CommitRequest.from_dict()`.
- [ ] Keep transport JSON parse errors as CLI errors.
- [ ] Run focused tests and commit.

### Task 2: TaskItems Schema And Work Model

**Files:**
- Modify: `src/ai_workroot/state/sqlite.py`
- Modify: `src/ai_workroot/work/model.py`
- Modify: `src/ai_workroot/work/operations.py`
- Modify: `tests/unit/test_protocol_schema.py`
- Modify: `tests/unit/test_work_operations.py`

- [ ] Write failing schema test for `task_items`.
- [ ] Write failing work operation test for creating/updating a TaskItem.
- [ ] Add `task_items` table with status, ordering, summaries, and timestamps.
- [ ] Add `TaskItem` dataclass and status transition helper.
- [ ] Add `create_task_item()` and `update_task_item()` for work runtime callers.
- [ ] Run focused tests and commit.

### Task 3: TaskItems Protocol Projection

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `src/ai_workroot/context/continuity.py`
- Modify: `tests/unit/test_protocol_projections.py`
- Modify: `tests/integration/test_agent_protocol_loop.py`

- [ ] Write failing projection test for `commit(progress)` with `items_created`.
- [ ] Write failing projection test for `commit(progress)` with `items_updated` marking item `done`.
- [ ] Write failing integration assertion that next `sync(continue)` includes open and recently done TaskItems.
- [ ] Implement item create/update projection inside `project_progress()`.
- [ ] Bump task/run/context state versions after item projection.
- [ ] Load task item refs in `load_continuity_package()`.
- [ ] Run focused tests and commit.

### Task 4: Inbox Temporary Task Lifecycle

**Files:**
- Modify: `src/ai_workroot/protocol/projections.py`
- Modify: `tests/unit/test_protocol_projections.py`
- Modify: `tests/integration/test_agent_protocol_loop.py`

- [ ] Write failing test for `commit(intent, classification.persistence=temporary)` creating `Task(role=inbox, process_level=L0)`.
- [ ] Write failing test for state archive transition `active -> archived`.
- [ ] Write failing test for promoting inbox task to normal role/process level.
- [ ] Implement temporary task projection without adding a new Inbox entity.
- [ ] Align task state machine with spec.
- [ ] Implement role/process promotion through `state` event payload fields.
- [ ] Run focused tests and commit.

### Task 5: Backlog And Quality Gate

**Files:**
- Modify: `docs/superpowers/specs/2026-05-26-task-management-continuity-p0-1-design.md`

- [ ] Confirm deferred backlog is recorded in the design spec.
- [ ] Run focused task-management tests.
- [ ] Run unit, integration, smoke, release validator, and temporary Workroot doctor.
- [ ] Commit final formatting/doc updates if any.

## Verification Commands

```bash
PYTHONPATH=src python3 -m unittest \
  tests.unit.test_protocol_controller \
  tests.unit.test_agent_exchange_command \
  tests.unit.test_protocol_schema \
  tests.unit.test_work_operations \
  tests.unit.test_protocol_projections \
  tests.integration.test_agent_protocol_loop \
  tests.unit.test_import_boundaries -v

PYTHONPATH=src python3 -m unittest discover tests/unit -q
PYTHONPATH=src python3 -m unittest discover tests/integration -q
PYTHONPATH=src python3 -m unittest discover tests/smoke -q
PATH="$PWD/.venv/bin:$PATH" PYTHONPATH="$PWD/src" ./scripts/dev/validate-release.sh
TMP_HOME=$(mktemp -d) && AI_WORKROOT_HOME="$TMP_HOME" PYTHONPATH=src python3 -m ai_workroot bootstrap-dev --cwd . >/tmp/workroot-bootstrap-dev.out && AI_WORKROOT_HOME="$TMP_HOME" PYTHONPATH=src python3 -m ai_workroot doctor --cwd .
```
