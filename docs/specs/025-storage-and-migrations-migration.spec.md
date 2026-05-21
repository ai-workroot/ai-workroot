# Spec 025: Storage and Migrations Migration

## Status

Draft

## Priority

P0

## Background

Storage behavior is split between package storage modules and older script helpers. Clean Workroot needs package-owned SQLite schema, migration execution, registry locking, and managed-state layout verification.

## Goals

- Make package storage modules authoritative.
- Add explicit migration runner and migration records.
- Preserve per-Workroot DB scoping and document it.
- Keep registry writes concurrency safe.
- Back up existing SQLite files before destructive changes.

## Non-goals

- Do not migrate real user directories automatically.
- Do not introduce external databases.
- Do not add foreign key enforcement as a hard requirement for 0.9.530.

## Scope

### Included

- SQLite schema initialization and migration.
- Registry JSONL reads/writes and locks.
- Old DB fixture migration tests.
- Managed state layout verification.

### Excluded

- User-facing Work commands.
- Remote sync.
- Cloud storage.

## Dependencies

- Spec 003 Workroot Environment Managed State.
- Spec 013 Storage SQLite Schema.
- Spec 024 Work and Asset Runtime Migration.
- Spec 028 System Health, Validation, and Checkbot.

## Requirements

### Functional Requirements

FR-001: `storage/sqlite.py` must initialize all active Clean Workroot tables.

FR-002: A package migration runner must apply ordered migrations idempotently.

FR-003: Migration state must be recorded in `schema_migrations` or `PRAGMA user_version`.

FR-004: Existing old DB shapes used by tests must migrate without data loss for preserved fields.

FR-005: Registry writes must use a registry-level lock for init and bootstrap-dev.

FR-006: Duplicate user directory registration must be safe under concurrent init.

### Non-functional Requirements

NFR-001: Storage code must not own domain policy decisions.

NFR-002: Storage must use standard library dependencies only.

NFR-003: Managed state must stay outside the user-selected directory by default.

## Proposed Design

### Concepts

Canonical tables hold source-of-truth records. Derived tables hold indexes, FTS rows, candidates, traces, and caches.

### Data Model

Package schema includes:

```text
workroots
assets
tasks
agent_runs
work_actions
release_records
relationship_nodes
relationship_edges
indexed_files
indexed_chunks
context_candidates
context_packages
context_traces
schema_migrations
```

Logical relationships use IDs and indexes. Foreign key enforcement is not required for 0.9.530.

### File Layout

```text
src/ai_workroot/storage/sqlite.py
src/ai_workroot/storage/migrations.py
src/ai_workroot/storage/repositories.py
src/ai_workroot/storage/jsonl_registry.py
src/ai_workroot/storage/locks.py
tests/fixtures/sqlite/
```

SQLite lives at:

```text
AI_WORKROOT_HOME/workroots/<workroot_id>/cache/workroot.sqlite
```

### CLI / API

Storage migration is invoked by runtime init/bootstrap/doctor flows. It may later be exposed through `workroot doctor --repair` or `workroot migrate`, but not in this spec.

### Runtime Behavior

Initialization creates or opens SQLite, applies migrations, verifies required tables/indexes, and returns issues to runtime.

### Error Handling

Migration failure creates a backup before destructive change, returns actionable diagnostics, and does not write into user directory.

### Security / Privacy

Backups remain inside managed state. No backup is written into the user-selected directory.

### Compatibility

Old script schema tests are migrated to package storage tests. Legacy script schema helpers remain only until tests no longer depend on them.

## Acceptance Criteria

AC-001: Given an empty SQLite path under managed state, when package initialization runs, then all active tables exist.

AC-002: Given an old DB fixture, when package migrations run, then schema migrations are recorded and preserved fields remain queryable.

AC-003: Given two concurrent init attempts for the same directory, when both finish, then only one Workroot binding exists.

AC-004: Given a user directory, when storage initializes, then no SQLite file is written inside that user directory.

## Test Plan

### Unit Tests

- Migration ordering.
- Idempotent migration records.
- Registry lock behavior.
- Duplicate binding rejection.

### Integration Tests

- Empty DB initialization.
- Old DB fixture migration.
- Concurrent init/bootstrap-dev registry writes.

### Manual Verification

- Inspect SQLite tables with `sqlite3` or Python `sqlite_master`.
- Confirm DB path under `AI_WORKROOT_HOME`.

## Migration / Rollback

Back up DB before destructive migration. Rollback restores backup and removes the failed migration record if it was partially written.

## Observability / Debugging

Doctor reports schema version, missing tables, migration failures, and backup paths inside managed state.

## Task Breakdown

T1: Add package migration runner
- Change: Implement ordered migration execution.
- Files likely affected: `src/ai_workroot/storage/migrations.py`, `src/ai_workroot/storage/sqlite.py`.
- Verification: migration unit tests.

T2: Add old DB fixtures
- Change: Add minimal fixtures for old indexed files, graph tables, candidate tables, and schema records.
- Files likely affected: `tests/fixtures/sqlite/`, `tests/integration/`.
- Verification: old DB migration tests.

T3: Consolidate registry locking
- Change: Ensure init/bootstrap-dev write paths use package storage lock.
- Files likely affected: `src/ai_workroot/runtime/environment.py`, `src/ai_workroot/runtime/bootstrap.py`, `src/ai_workroot/storage/locks.py`.
- Verification: concurrency regression tests.

T4: Retire script storage authority
- Change: Convert tests from `scripts/workroot_sqlite.py` and `scripts/workroot_state.py` to package imports where parity exists.
- Files likely affected: `tests/`, `scripts/`.
- Verification: full unittest suite.

## Risks

- Migration order corrupts old fixture data.
- Concurrent registry tests are flaky if lock timeouts are too short.
- Old script tests mask package storage gaps.

## Open Questions

None.

