# Spec: Migrations

## Status

Draft

## Priority

P0

## Background

AI Workroot managed state will evolve across versions. Bootstrap creates the first state, migrations evolve it, doctor verifies it, and runtime commands use it. 0.9.529 needs a migration system before the managed state layout, SQLite schema, Context Guide cache, and graph tables can be reliable.

## Goals

- Provide ordered, idempotent state schema migrations.
- Track migration application per AI Workroot home and per Workroot.
- Support rollback or clear recovery on failure.
- Run doctor after migrations.
- Preserve Clean Mode boundaries during migration.

## Non-goals

- This Spec does not define every future migration.
- This Spec does not support remote migrations or hosted migration services.
- This Spec does not migrate user assets unless a future explicit user-authorized migration requires it.
- This Spec does not perform automatic self-upgrade of the runtime.

## Scope

### Included

- Migration metadata.
- Migration ordering.
- Idempotency rules.
- Failure handling and rollback.
- Doctor verification after migration.
- Global and per-Workroot schema migration distinction.

### Excluded

- Bootstrap phase details, covered by `004-bootstrap-process.spec.md`.
- Release versioning policy, covered by `014-release-and-test-gates.spec.md`.
- Specific SQLite table definitions, covered by `013-sqlite-cache-and-provenance-graph.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `004-bootstrap-process.spec.md`
- `006-doctor-command.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`

## Requirements

### Functional Requirements

FR-001: Migrations must be identified by stable, ordered IDs.

FR-002: Migrations must record applied status in managed state.

FR-003: Migrations must support global AI Workroot home scope.

FR-004: Migrations must support per-Workroot state scope.

FR-005: Migration execution must be idempotent.

FR-006: Migration execution must acquire a migration lock.

FR-007: Migration failure must leave state either unchanged or marked as failed with recovery instructions.

FR-008: Migration execution must not write managed state into user directories.

FR-009: Doctor must run after successful migrations.

FR-010: Runtime commands must refuse to use state that requires unapplied P0 migrations.

### Non-functional Requirements

NFR-001: Migrations must work offline.

NFR-002: Migrations must be deterministic and testable.

NFR-003: Migrations must avoid data loss by default.

NFR-004: Migration records must be human-inspectable.

NFR-005: Migration failure messages must be actionable.

## Proposed Design

### Concepts

- Migration ID: Ordered identifier such as `0001_initial_managed_state`.
- Migration scope: `global` or `workroot`.
- Migration status: `pending`, `applied`, `failed`, or `rolled_back`.
- Migration lock: Prevents concurrent schema changes.
- Recovery plan: Human-readable next step after failure.

### Data Model

Global migration registry:

```json
{
  "migrationId": "0001_initial_global_state",
  "scope": "global",
  "status": "applied",
  "startedAt": "2026-05-19T00:00:00Z",
  "completedAt": "2026-05-19T00:00:01Z",
  "checksum": "sha256:...",
  "error": null
}
```

Per-Workroot migration registry:

```json
{
  "migrationId": "0002_context_candidates_table",
  "scope": "workroot",
  "workrootId": "wr_example",
  "status": "applied",
  "startedAt": "2026-05-19T00:00:00Z",
  "completedAt": "2026-05-19T00:00:01Z",
  "checksum": "sha256:...",
  "error": null
}
```

### File Layout

Migration state:

```text
<AI_WORKROOT_HOME>/
  migrations/
    global.jsonl
    locks/
    history/
  workroots/<workrootId>/
    migrations/
      applied.jsonl
      locks/
      backups/
```

SQLite migration tracking may also exist inside `global.sqlite` and `workroot.sqlite`, but file records remain the inspection layer.

### CLI / API

Required internal API:

```text
list_pending_migrations(scope, workroot_id)
apply_migrations(scope, workroot_id)
record_migration_status(record)
```

CLI behavior:

```bash
workroot doctor
workroot bootstrap-dev
workroot init
workroot status
```

These commands must detect pending required migrations.

### Runtime Behavior

Migration flow:

1. Resolve managed state path.
2. Acquire migration lock.
3. Read applied migration records.
4. Determine pending migrations.
5. Create pre-migration backup for files or SQLite objects that will be modified.
6. Apply migrations in order.
7. Verify idempotency marker.
8. Record success or failure.
9. Release lock.
10. Run doctor after success.

### Error Handling

- If lock cannot be acquired, report the existing lock and suggested retry.
- If backup fails, do not apply the migration.
- If migration fails after changes, attempt rollback when the migration declares rollback support.
- If rollback is not possible, mark migration failed and block runtime commands that require the migrated schema.
- If doctor fails after migration, mark state as migrated but not healthy.

### Security / Privacy

Migration backups may include managed state summaries and indexes. They must remain under managed state and must not be copied into the user directory. Migration logs must avoid writing secrets.

### Compatibility

Migrations must tolerate missing optional directories from earlier pre-0.9.529 public seed layouts. Future XDG path migration must be added as an explicit migration.

## Acceptance Criteria

AC-001:
Given pending migrations
When migrations run
Then they are applied in stable ID order.

AC-002:
Given an already applied migration
When migrations run again
Then the migration is skipped without changing state.

AC-003:
Given a migration fails before changes
When migration exits
Then no migration success record is written.

AC-004:
Given a migration fails after partial changes
When rollback is available
Then the pre-migration state is restored and failure is recorded.

AC-005:
Given a Clean Mode Workroot
When migrations run
Then no managed state is written into the user directory.

AC-006:
Given migrations succeed
When doctor runs
Then doctor validates migrated state.

## Test Plan

### Unit Tests

- Test migration ordering.
- Test applied migration skip behavior.
- Test lock acquisition and release.
- Test failure record generation.
- Test Clean Mode boundary guard in migration writer.

### Integration Tests

- Apply initial migration to an empty AI Workroot home.
- Apply per-Workroot SQLite table migration.
- Simulate a failed migration and verify rollback or failed status.
- Run doctor after migration.

### Manual Verification

- Inspect migration history files.
- Re-run init/bootstrap against migrated state.
- Confirm no user directory state artifacts are created.

## Migration / Rollback

This Spec defines migration and rollback behavior. Each migration must declare:

- migration ID;
- scope;
- files or tables affected;
- backup strategy;
- rollback support;
- doctor checks that prove success.

If rollback is not supported for a migration, it must state that explicitly and provide manual recovery instructions.

## Observability / Debugging

Migration logs must show migration ID, scope, start time, end time, status, affected managed-state paths, and doctor result. Debug mode may show detailed stack traces for developers, but default output should be concise.

## Task Breakdown

T1: Add migration registry
- Change: Create migration record format and read/write helpers.
- Files likely affected: future migration module, tests.
- Verification: Unit tests read and append records.

T2: Add migration runner
- Change: Apply ordered migrations with locks and backup hooks.
- Files likely affected: migration module.
- Verification: Unit tests for ordering, idempotency, and lock behavior.

T3: Add initial migrations
- Change: Add initial global, Workroot, SQLite, graph, and context candidate migrations.
- Files likely affected: migration definitions.
- Verification: Integration test creates full 0.9.529 state.

T4: Add runtime migration gate
- Change: Runtime commands detect missing required migrations.
- Files likely affected: CLI module, runtime state module.
- Verification: CLI test refuses outdated state.

T5: Add doctor after migration
- Change: Run doctor and record result after successful migration.
- Files likely affected: migration module, doctor module.
- Verification: Integration test confirms doctor runs after migration.

## Risks

- Migration complexity can grow before the state model stabilizes.
- Rollback for SQLite schema changes must be designed carefully.
- Path migrations may be difficult if users customize `AI_WORKROOT_HOME`.

## Open Questions

None.
