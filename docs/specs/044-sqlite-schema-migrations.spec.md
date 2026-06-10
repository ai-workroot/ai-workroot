# Spec 044: SQLite Schema Migrations

## Status

Accepted

## Target

0.9.531

## Purpose

Define the active SQLite schema migration discipline for Clean Workroot.

This spec establishes the first production-style schema upgrade mechanism even
though 0.9.531 is still pre-production. Experimental dev database shapes before
this point are not compatibility contracts.

## Scope

Included:

- Per-Workroot SQLite schema creation and upgrades.
- Ordered migration records in `schema_migrations`.
- Fresh database initialization through the same migration runner used for
  upgrades.
- Tests that lock migration ordering, idempotency, and canonical schema
  ownership.

Excluded:

- External database engines.
- User-directory storage migration.
- Full compatibility for historical experimental dev database shapes.
- File/global migrations handled by `ai_workroot.state.migrations`.

## Storage Location

The SQLite database remains under managed state:

```text
<stateDirectory>/cache/workroot.sqlite
```

No SQLite schema migration may write runtime state into the user-selected
working directory.

## Architecture

`src/ai_workroot/state/sqlite.py` owns SQLite schema migrations.

The module exposes:

- `SCHEMA`: canonical DDL for the current SQLite shape.
- `SQLITE_SCHEMA_MIGRATIONS`: ordered migration registry.
- `SQLITE_SCHEMA_MIGRATION_IDS`: public ordered IDs for tests and diagnostics.
- `initialize_workroot_sqlite(path)`: creates the parent directory, enables WAL,
  and runs unapplied migrations.

`SCHEMA` must not write migration records. Migration records are written only by
the migration runner after a migration function succeeds.

`src/ai_workroot/state/migrations.py` remains separate. It is for file/global
state migrations and must not become the SQLite schema runner.

## Migration Model

Each SQLite migration has:

```text
migration_id
apply_fn(connection)
```

Rules:

- Migration IDs are stable strings with numeric prefixes, such as
  `010-context-runtime-schema`.
- Migrations run in registry order.
- A migration is skipped only when its ID already exists in
  `schema_migrations`.
- A successful migration records `migration_id` and `appliedAt`.
- `appliedAt` is UTC ISO-8601 seconds, for example
  `2026-06-09T12:00:00Z`.
- Migration functions must be idempotent when practical.
- Future schema changes must add a new migration ID and test. They must not be
  implemented by adding implicit `ALTER TABLE` calls to initialization.

## Fresh Database Behavior

An empty database uses the same path as an upgrade:

```text
initialize_workroot_sqlite(path)
  -> enable WAL
  -> run ordered SQLite migrations
  -> record each successful migration
```

The first migration creates the canonical base schema. Later migrations may be
no-ops on a fresh database if the current canonical schema already includes the
same shape, but they are still recorded through the runner so fresh installs and
upgrades share one discipline.

## Pre-Production Dev Schema Cleanup

Clean Workroot 0.9.531 does not promise full compatibility with historical
experimental dev schemas created before this migration runner existed.

Allowed:

- Clean or recreate local dev databases when they are older than the accepted
  migration contract.
- Keep targeted migration tests for old shapes that are still useful as
  regression guards.

Not allowed:

- Treat old experimental schema shapes as public compatibility requirements.
- Add broad legacy schema detection that complicates the current model without a
  current user-facing need.

## Failure Behavior

SQLite migration failures propagate to the caller.

Protocol and command layers may decide whether a storage failure should be
reported, quarantined, or treated as non-blocking for Agent work, but storage
must not silently mark a failed migration as applied.

## Acceptance Criteria

- Fresh initialization creates all required tables and indexes.
- Fresh initialization records all registered SQLite migrations exactly once.
- Re-running initialization does not duplicate or rewrite migration records.
- `SCHEMA` does not contain `INSERT ... schema_migrations` statements.
- Context runtime schema hardening is represented by
  `010-context-runtime-schema`.
- Existing targeted old-shape tests for indexed files, relationship targets,
  context candidates, and context recall hints continue to pass.

## Test Coverage

Required tests:

- Migration registry IDs are unique and ordered.
- Canonical schema text does not write migration markers.
- Fresh initialization records registered migrations once.
- Repeated initialization is idempotent.
- Current old-shape regression tests still accept projection/provider writes.
