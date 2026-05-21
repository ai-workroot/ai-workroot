# 0.9.529 Hardening Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and superpowers:verification-before-completion. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix the remaining 0.9.529 review findings on `feat/0.9.529-clean-native-context-foundation` without merging, tagging, or releasing.

**Architecture:** Keep Clean Mode and the 0.9.529 design intact. Add targeted guards and tests around concurrency, token limits, candidate retrieval fairness, safety filtering, graph signal semantics, SQLite migrations, CLI behavior, and debug trace observability. Defer large `workroot_context.py` modularization to a later branch and keep this iteration localized.

**Tech Stack:** Python standard library, `unittest`, SQLite FTS5, local Git/GitHub CLI workflow.

---

### Task 1: Registry Locking

**Files:**
- Modify: `scripts/workroot_state.py`
- Modify: `scripts/workroot_bootstrap.py`
- Test: `tests/test_workroot_init_cli.py`
- Test: `tests/test_workroot_bootstrap_dev.py`

- [x] Write failing tests for concurrent duplicate init and concurrent bootstrap-dev.
- [x] Add a managed-home registry lock under `<AI_WORKROOT_HOME>/concurrency/locks/registry.lock`.
- [x] Re-read registry state inside the lock before writing.
- [x] Verify concurrent tests pass.

### Task 2: Token Estimation And Hard Limit

**Files:**
- Modify: `scripts/workroot_context.py`
- Test: `tests/test_workroot_context.py`

- [x] Write failing tests for English, CJK, code/no-whitespace, and final fallback hard-limit behavior.
- [x] Replace whitespace token estimation with a conservative local estimator.
- [x] Add final fallback rendering when optional content trimming is insufficient.
- [x] Record hard-limit trim steps and final fallback in debug trace.

### Task 3: Candidate Pool Fairness

**Files:**
- Modify: `scripts/workroot_context.py`
- Test: `tests/test_workroot_context.py`

- [x] Write failing tests showing explicit, FTS, graph, and active-task candidates are not starved by many always candidates.
- [x] Collect source buckets before global truncation.
- [x] Prioritize explicit/FTS/graph/active-task sources before recent always saturation.
- [x] Verify selected candidates include prioritized sources.

### Task 4: Safety Filtering

**Files:**
- Modify: `scripts/workroot_candidates.py`
- Modify: `scripts/workroot_context.py`
- Test: `tests/test_workroot_candidates.py`
- Test: `tests/test_workroot_context.py`

- [x] Write failing repository-level tests for blocked safety policies.
- [x] Add `include_blocked_safety` only for debug/audit callers.
- [x] Keep Context Guide blocked safety drops visible in debug trace.
- [x] Verify never-auto, needs-confirmation, and sensitive policies are covered.

### Task 5: Graph Signal Semantics

**Files:**
- Modify: `scripts/workroot_context.py`
- Test: `tests/test_workroot_context.py`

- [x] Write failing test that selected-node pseudo signals do not render under Graph Signals.
- [x] Render only real relation-backed edge signals.
- [x] Record graph seed explanations separately in trace.

### Task 6: SQLite Migration And Scoping

**Files:**
- Modify: `scripts/workroot_sqlite.py`
- Modify: `scripts/workroot_candidates.py`
- Test: `tests/test_workroot_sqlite.py`
- Test: `tests/test_workroot_candidates.py`

- [x] Write failing old-DB migration tests.
- [x] Add `schema_migrations` and idempotent migration records.
- [x] Preserve per-Workroot DB invariant for graph tables and test it.
- [x] Scope `mark_candidates_used` by `workroot_id`.

### Task 7: CLI Fixes And Legacy Help Isolation

**Files:**
- Modify: `scripts/workroot_cli.py`
- Test: `tests/test_workroot_init_cli.py`
- Test: `tests/test_workroot_context.py`
- Test: `tests/test_workroot_cli_discovery.py`

- [x] Write failing tests for mutually exclusive Native Agent Entry flags.
- [x] Add `workroot context --hard-token-limit`.
- [x] Hide legacy seed commands from default help while keeping them callable.
- [x] Verify quickstart and manifest still document legacy behavior.

### Task 8: Test Audit Cleanup

**Files:**
- Move/Rename: `scripts/test_new_task.py`
- Modify: `docs/release-checklist.md`
- Modify: `tests/test_0529_release_gates.py`

- [x] Move or rename the test-like script outside `scripts/test_*.py`.
- [x] Update validation docs and tests.
- [x] Run audit commands to verify no test-like files outside `tests/`.

### Task 9: Maintainability Follow-up

**Files:**
- Modify: `docs/release-checklist.md` or add a follow-up plan note.

- [x] Record that `workroot_context.py` should be split into budget/token/render/trace modules in a separate branch.
- [x] Avoid broad modular refactor in this iteration.

### Task 10: Final Verification

**Commands:**
- `python3 -m unittest discover -s tests -v`
- `python3 scripts/validate_kernel.py --release`
- `python3 -m py_compile scripts/*.py`
- `git diff --check origin/main...HEAD`
- Clean Mode smoke
- duplicate userDirectory smoke
- unsafe Workroot ID smoke
- Native Agent Entry smoke
- bootstrap-dev smoke, including second run
- SQLite schema report
- Context Guide behavior report with safety candidates, FTS match, graph relation, weak query-only node, and hard token trim

- [x] Commit fixes with a clear message.
- [x] Push `feat/0.9.529-clean-native-context-foundation`.
