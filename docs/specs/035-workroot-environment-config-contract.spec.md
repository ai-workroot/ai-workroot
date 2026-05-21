# Spec: Workroot Environment Config Contract

## Status

Draft

## Priority

P1

## Background

`AI_WORKROOT_HOME/config.json` is the human-readable global environment summary for technical administrators and future migration tooling. It should not become a large registry or knowledge store, but it should expose enough state to understand environment identity, version, maintenance mode, registered Workroot counts, and recent health checks.

## Goals

- Keep `config.json` small, readable, and stable.
- Preserve user-defined custom fields when updating config.
- Record registered and active Workroot counts.
- Record last registry update and last doctor run timestamps with second precision.
- Reserve maintenance fields for future upgrade locks.

## Non-goals

- Do not store per-Workroot knowledge in global config.
- Do not store full Workroot registry records in config.
- Do not store user profile data in global config.
- Do not make config the source of truth for Workroot records.

## Scope

### Included

- Minimal environment identity fields.
- Version/schema/layout fields.
- Summary counters.
- Doctor status summary.
- Maintenance lock placeholder.

### Excluded

- Full registry data.
- Agent integration mode per Workroot.
- Global knowledge body store.
- Cloud configuration.

## Dependencies

- `src/ai_workroot/runtime/environment.py`
- `src/ai_workroot/runtime/doctor.py`
- `src/ai_workroot/storage/jsonl_registry.py`

## Requirements

### Functional Requirements

FR-001: `initialize_environment` must create `config.json` if missing.

FR-002: Existing custom config keys must be preserved.

FR-003: `config.json` must include `kind`, `environmentId`, `version`, `schemaVersion`, `layoutVersion`, `mode`, `createdAt`, and `updatedAt`.

FR-004: `config.json` must include summary counts for registered and active Workroots.

FR-005: Workroot registration must refresh summary counts.

FR-006: Doctor must record last doctor status and timestamp.

FR-007: Timestamps must use UTC ISO-8601 with second precision.

### Non-functional Requirements

NFR-001: Config writes must be local-only.

NFR-002: Config must not include absolute per-Workroot state lists by default.

NFR-003: Config must remain small enough for quick human inspection.

## Proposed Design

### Concepts

- WorkrootEnvironment config: global, human-readable summary.
- Registry: source of truth for Workroot records.
- Maintenance: reserved global state for future migration/upgrade locks.

### Data Model

```json
{
  "kind": "WorkrootEnvironment",
  "environmentId": "env_local_default",
  "version": "0.9.530",
  "schemaVersion": "0.9.530",
  "layoutVersion": "0.9.530",
  "mode": "clean",
  "createdAt": "2026-05-21T00:00:00Z",
  "updatedAt": "2026-05-21T00:00:00Z",
  "summary": {
    "registeredWorkrootCount": 1,
    "activeWorkrootCount": 1,
    "lastRegistryUpdatedAt": "2026-05-21T00:00:00Z",
    "lastDoctorStatus": "PASS",
    "lastDoctorRunAt": "2026-05-21T00:00:00Z",
    "lastMigrationId": null,
    "lastMigrationAt": null
  },
  "maintenance": {
    "status": "idle",
    "operation": null,
    "operationId": null,
    "startedAt": null,
    "updatedAt": null,
    "message": null,
    "blocksWrites": true,
    "blocksContextGeneration": false
  }
}
```

### File Layout

`config.json` lives under `AI_WORKROOT_HOME`, never inside user-selected directories.

### CLI / API

No user-facing CLI is added in this spec. Runtime APIs:

- `ensure_environment_config`
- `refresh_environment_registry_summary`
- `record_environment_doctor_summary`

### Runtime Behavior

Environment initialization creates or merges config. Registration refreshes counts. Doctor records health summary.

### Error Handling

Malformed config should be treated as empty for this layer; lower-level state repair/backups remain covered by state tests.

### Security / Privacy

Config must not include user knowledge, sensitive content, or full per-Workroot metadata lists.

### Compatibility

Existing custom fields remain. Removed experimental keys such as `workroots`, `policies`, `paths`, `layout`, and `agentIntegration` are not kept in the minimal contract.

## Acceptance Criteria

AC-001:
Given an empty AI_WORKROOT_HOME
When a Workroot is initialized
Then config includes environment identity, UTC timestamps, summary counts, and maintenance status.

AC-002:
Given custom config keys
When another Workroot is initialized
Then custom keys remain and summary counts are refreshed.

AC-003:
Given doctor runs
When it completes
Then config records last doctor status and timestamp.

## Test Plan

### Unit Tests

- Environment helper tests if split later.

### Integration Tests

- Covered through CLI smoke tests.

### Manual Verification

- Inspect temporary `AI_WORKROOT_HOME/config.json` after smoke runs.

## Migration / Rollback

No schema migration is required. Existing unknown keys are preserved unless explicitly removed from the minimal contract.

## Observability / Debugging

Config itself is the human-readable summary. Doctor also reports status through CLI.

## Task Breakdown

T1: Define config helpers
- Change: Add config creation and merge helpers.
- Files likely affected: `src/ai_workroot/runtime/environment.py`
- Verification: CLI smoke tests.

T2: Refresh registry counts
- Change: Update summary during Workroot registration.
- Files likely affected: `src/ai_workroot/runtime/environment.py`
- Verification: repeated init smoke.

T3: Record doctor status
- Change: Update config summary after doctor runs.
- Files likely affected: `src/ai_workroot/runtime/doctor.py`
- Verification: doctor summary smoke.

## Risks

- Config may grow into a duplicate registry if not kept constrained.
- Future maintenance lock behavior needs stricter write blocking semantics.

## Open Questions

None.
