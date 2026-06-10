# Focused Hardening Groups 1-2 Design

## Scope

This hardening pass closes the confirmed Group 1 and Group 2 review findings on the current feature branch. It does not introduce a new version number, tag, release, MCP implementation, vector database, remote embedding dependency, or runnable legacy compatibility layer.

Work Continuity Control and Agent Operation Entry remain a separate follow-up design tracked in `docs/dev/current-todo.md`.

## Goals

1. Keep live-agent E2E safe by default.
2. Make smoke tests independent from the developer machine.
3. Remove ambiguous context diagnostic timestamp naming.
4. Keep release validation language aligned with retired Public Seed state.
5. Make ContextRecallHint visible as a first-class Retrieval & Index Control concept without over-DDD modeling.
6. Remove active package support for old compatibility managed-state initialization.
7. Tighten canonical UTC time values and writes in active SQLite/runtime paths while keeping simple field names.
8. Prevent global index refresh from silently creating missing per-Workroot SQLite databases.

## Non-Goals

- Do not delete archived history under `docs/history/`.
- Do not remove historical Public Seed documents.
- Do not run live E2E or remote model calls.
- Do not run destructive cleanup.
- Do not redesign WorkrootEnvironment or the source layout.
- Do not force backwards-compatible migrations for pre-user local databases beyond in-place schema normalization needed by current tests.

## Group 1 Design

### G1-1 Live-agent E2E Sandbox and Remote LLM Opt-In

`tests/e2e/live_agent.py` must never default `CODEX_HOME` to the real user home. It will set `CODEX_HOME` under the E2E run root, using `run_root/home/.codex`.

The `live-agent` E2E suite will require two opt-ins:

- `AI_WORKROOT_RUN_E2E=1`
- `AI_WORKROOT_E2E_ALLOW_REMOTE_LLM=1`

The runner blocks `live-agent` before discovery when the remote-LLM opt-in is missing. The live helper also checks this directly so bypassing the runner still fails closed.

Tests:

- Contract test runner rejects `live-agent` without `AI_WORKROOT_E2E_ALLOW_REMOTE_LLM`.
- Unit/contract test verifies the live helper uses sandbox `CODEX_HOME` in its environment preparation path without invoking Codex.

### G1-2 Smoke Git Identity

Smoke tests that create temporary Git repos must configure local `user.name` and `user.email` before `git commit`. This keeps tests stable on clean machines and CI containers.

Test:

- Existing smoke test becomes self-contained and no longer depends on global Git config.

### G1-3 Context Diagnostic Timestamp Naming

Context diagnostic logs write:

- `displayTime`
- `createdAt`

`displayTime` is the configured environment-local display instant. `createdAt` stays canonical. Pruning reads `createdAt`; this branch does not keep legacy diagnostic timestamp fallback.

Tests:

- Diagnostic log test asserts `displayTime` exists and legacy ambiguous timestamp fields are absent.
- Pruning uses `createdAt`.

### G1-4 Retired Public Seed Runtime Validation Wording

Release validation may continue rejecting accidental `.workroot/runtime/cache` and `.workroot/runtime/logs` files, but comments and diagnostics must identify these as retired Public Seed generated-state residue, not current runtime.

Tests:

- Existing release validator tests continue to pass.

### G1-5 ContextRecallHint Retrieval Concept

`ContextRecallHint` is already implemented in the indexing provider as the active Context Card equivalent. To avoid losing the concept again, add a lightweight core value model in `core/retrieval.py` with no storage dependency. The provider imports this core model instead of owning the concept itself.

Tests:

- Unit test validates the core `ContextRecallHint` model is importable without infrastructure imports.
- Existing hint materialization tests continue to pass.

## Group 2 Design

### G2-1 Retire Active `runtime/state.py`

`src/ai_workroot/runtime/state.py` contains old compatibility managed-state initialization and creates old `user/`, `knowledge/`, `graph/`, and `contextGuide` structures. It must no longer be active behavior.

The active package file will be reduced to a non-runnable sentinel module that raises a clear `RuntimeError` if old initializer entry points are called. It will not contain old layout constants or write code.

`tests/unit/test_state.py` will be rewritten to validate current active environment/init behavior instead of old compatibility state.

Acceptance:

- No active source file contains old runtime layout strings such as `knowledge/facts`, `graph/exports`, `contextGuide`, or writes legacy local time fields through `runtime/state.py`.
- Import boundary tests fail if old compatibility initializer names are referenced outside historical docs.

### G2-2 Time Model Cleanup

Canonical persisted time in active managed state uses simple field names and UTC `Z` values. Python dataclass fields and function parameters use snake_case names such as `created_at`, `updated_at`, and `occurred_at`; JSON and SQLite contracts use canonical camelCase names such as `createdAt`, `updatedAt`, and `occurredAt`.

In this pass:

- `schema_migrations` uses `appliedAt` with UTC `Z` values.
- Migration insert values use `strftime('%Y-%m-%dT%H:%M:%SZ','now')`.
- `context_candidates` uses `updatedAt` and `lastUsedAt`.
- `context_recall_hints` uses `createdAt` and `updatedAt`.
- `time_events` uses `occurredAt` plus `timezoneId` and `localDate` for timeline semantics.
- Runtime/provider dataclasses expose snake_case Python names.
- SQLite helpers only ensure current columns exist; this branch does not preserve pre-user legacy time-column migrations.
- Core value objects use simple snake_case names for machine-readable time fields.

Tests:

- SQLite schema test asserts canonical simple columns and migration markers.
- Candidate provider tests assert upserts and context usage update canonical simple columns.
- ContextRecallHint tests assert simple fields round-trip and materialize correctly.
- Import boundary test scans active source for `datetime('now')`, verbose `*Utc` time field names, and old compatibility state writes.

### G2-3 Global Index Refresh Has No DB Creation Side Effect

Global index refresh is projection maintenance, not repair. It must not call `initialize_workroot_sqlite()` for missing per-Workroot databases.

Behavior:

- If a registered Workroot DB is missing, skip it.
- Write a global index health warning under `global-index/health.jsonl`.
- Do not create `cache/workroot.sqlite`.
- Query functions remain read-only over JSONL projections.

Tests:

- Refreshing workroot/task/asset/time indexes with a missing DB does not create the DB.
- A health warning is written for skipped missing DB.
- Existing refresh tests with present DB continue to pass.

## Implementation Order

1. Add/adjust tests for Group 1.
2. Implement Group 1 minimal changes.
3. Run targeted contract/smoke/integration tests.
4. Add/adjust tests for Group 2 state retirement.
5. Retire `runtime/state.py` and rewrite `tests/unit/test_state.py`.
6. Add/adjust tests for UTC schema/provider behavior.
7. Implement SQLite/provider/runtime time cleanup.
8. Add/adjust tests for global index no-create behavior.
9. Implement global index skip/warning behavior.
10. Run full focused validation.

## Validation Commands

Targeted during development:

```bash
PYTHONPATH=src python3 -m unittest tests.contracts.test_e2e_opt_in_policy -v
PYTHONPATH=src python3 -m unittest tests.smoke.test_clean_release_validator -v
PYTHONPATH=src python3 -m unittest tests.integration.test_context_budget_trace -v
PYTHONPATH=src python3 -m unittest tests.unit.test_state -v
PYTHONPATH=src python3 -m unittest tests.unit.test_context_recall_hints -v
PYTHONPATH=src python3 -m unittest tests.unit.test_global_indexes -v
PYTHONPATH=src python3 -m unittest tests.integration.test_environment_storage -v
PYTHONPATH=src python3 -m unittest tests.unit.test_import_boundaries -v
```

Final:

```bash
python3 -m py_compile $(find src scripts tests -name "*.py")
PYTHONPATH=src python3 -m unittest discover -s tests/contracts -v
PYTHONPATH=src python3 -m unittest discover -s tests/unit -v
PYTHONPATH=src python3 -m unittest discover -s tests/integration -v
PYTHONPATH=src python3 -m unittest discover -s tests/negative -v
PYTHONPATH=src python3 -m unittest discover -s tests/smoke -v
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
git diff --check
```

Live-agent E2E is not part of final validation unless explicitly requested.
