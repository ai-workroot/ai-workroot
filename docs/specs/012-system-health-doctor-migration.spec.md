# Spec 012 — System Health, Doctor, Maintenance, Migration

Status: accepted
Target: 0.9.530

## Purpose

Define diagnostics, maintenance, migration, and release validation.

## Doctor

Doctor is read-only by default.

Checks:

- WorkrootEnvironment exists.
- EnvironmentConfig schema valid.
- registry exists and is lockable.
- duplicate active directory binding absent.
- WorkrootRegistration points to valid state directory.
- Workroot state has expected structure.
- Native Entry is safe.
- generated entry files are ignored under bootstrap-dev.
- SQLite schema valid.
- relationship tables valid.
- release records valid.
- redacted/deleted content not present in ordinary indexes/context.
- index manifests and health valid.
- migrations recorded.
- Public Seed active root retired.

## Maintenance

Maintenance actions are explicit:

```text
reindex
compact
backup
restore
prune
repair
```

Doctor may recommend these but not run them by default.

## Migration

MigrationRecord fields:

```text
migration_id
scope
version
status
started_at
completed_at
backup_ref
error
```

Scopes:

```text
environment
workroot
storage
index
```

## Release validation

Before tag:

- full tests pass;
- smoke tests pass;
- negative tests pass;
- docs/specs are consistent;
- active root free of retired seed files;
- branch final report produced.

## Acceptance

- `workroot doctor` runs clean in a fresh Clean Workroot.
- Doctor reports registry/index/schema/release/native-entry state.
- Doctor does not mutate without explicit flag.
- Migration records exist and are queryable.
