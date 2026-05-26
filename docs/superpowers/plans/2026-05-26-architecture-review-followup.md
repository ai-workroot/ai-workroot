# Architecture Review Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden 0.9.530 capability ownership after architecture review without a large Context Control split.

**Architecture:** Handoff is its own capability, Release Control owns release filtering, Retrieval stays focused on candidates and indexes, and `shared/` is reduced so it cannot become a new `core/`. `context/builder.py` remains the Context Control entrypoint with clearer ownership comments and release imports moved to `release.filter`.

**Tech Stack:** Python 3.9 standard library, `unittest`, AST import boundary checks, existing release doctor validation.

---

### Task 1: Branch And Review Baseline

- [x] Confirm the starting branch is clean.
- [x] Create local branch `refactor/architecture-review-followup` from `main`.
- [x] Do not push the branch during implementation.

### Task 2: Fix Release Doctor CWD

**Files:**
- `tests/smoke/test_doctor_cli_smoke.py`
- `src/ai_workroot/cli/main.py`

- [x] Add a failing smoke test showing `workroot doctor --release --cwd <empty-dir>` fails from repo cwd.
- [x] Confirm the test fails because release doctor validates the repo cwd.
- [x] Change CLI doctor dispatch to call `run_release_doctor(Path(args.cwd))`.
- [x] Re-run the focused test and confirm it passes.

### Task 3: Add Handoff Capability

**Files:**
- `src/ai_workroot/handoff/__init__.py`
- `src/ai_workroot/handoff/model.py`
- `src/ai_workroot/handoff/operations.py`
- `src/ai_workroot/state/sqlite.py`
- `src/ai_workroot/work/operations.py`
- `tests/unit/test_handoff_operations.py`
- `tests/unit/test_work_operations.py`
- `tests/e2e/longrun.py`

- [x] Add failing tests for `ai_workroot.handoff.operations.create_handoff`.
- [x] Add failing assertions that `work.operations` no longer exposes `create_handoff`.
- [x] Add `HandoffPackage`.
- [x] Move handoff insert/update logic into `handoff.operations`.
- [x] Add optional `target` and `body` columns to `handoffs` through idempotent schema initialization.
- [x] Update E2E imports to use `ai_workroot.handoff.operations.create_handoff`.
- [x] Re-run handoff and work unit tests.

### Task 4: Move Release Filtering To Release Control

**Files:**
- `src/ai_workroot/release/filter.py`
- `src/ai_workroot/retrieval/providers/context_recall_hint_provider.py`
- `src/ai_workroot/retrieval/providers/release_provider.py`
- `src/ai_workroot/context/builder.py`
- release/context tests

- [x] Add failing import-boundary tests that reject `retrieval/providers/release_provider.py` and release filter symbols inside `retrieval/`.
- [x] Add failing import-boundary test that rejects any `retrieval/` import of `ai_workroot.release`.
- [x] Move `CandidateReleaseTargetResolver`, filter reports, and filter functions into `release/filter.py`.
- [x] Update `context/builder.py` to import release filtering from `ai_workroot.release.filter`.
- [x] Move release-aware recall hint materialization orchestration into `context/builder.py`.
- [x] Keep `context/builder.py` as one file and add concise section comments for future split seams.
- [x] Delete `retrieval/providers/release_provider.py`.
- [x] Re-run release target resolver, recall hint, context release filtering, context retrieval selection, and negative release tests.

### Task 5: Reduce Shared Model Surface

**Files:**
- `src/ai_workroot/relationships/model.py`
- `src/ai_workroot/relationships/operations.py`
- `src/ai_workroot/shared/model.py`
- model/import boundary tests

- [x] Add failing boundary test that `shared/model.py` must not exist.
- [x] Move `SourceRef` into `relationships/model.py`.
- [x] Update relationship operations and model tests to import `SourceRef` from `relationships.model`.
- [x] Remove active tests for unused shared value objects.
- [x] Delete `shared/model.py`.
- [x] Re-run capability model and import boundary tests.

### Task 6: Update Release Doctor And Docs

**Files:**
- `src/ai_workroot/diagnostics/doctor.py`
- `tests/smoke/test_clean_release_validator.py`
- active architecture and spec docs

- [x] Add release doctor checks for `src/ai_workroot/handoff` and `src/ai_workroot/release/filter.py`.
- [x] Update fake repo release doctor smoke fixtures.
- [x] Update active architecture docs so Work no longer owns handoff packages and Retrieval no longer owns release filters.
- [x] Update docs to describe `shared/` as extensions and reserved standard-library contracts only.
- [x] Re-run release validator smoke and current docs contract tests.

### Task 7: Final Verification

- [x] Run focused tests touched above.
- [x] Run `PYTHONPATH=src python3 -m unittest discover`.
- [x] Run `PYTHONPATH=src python3 -m compileall -q src tests scripts`.
- [x] Run `PYTHONPATH=src PATH="$PWD/.venv/bin:$PATH" scripts/dev/validate-release.sh`.
- [x] Confirm CLI version remains `AI Workroot 0.9.530`.
- [x] Confirm branch is local only.
