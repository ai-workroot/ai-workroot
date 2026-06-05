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
- Record last registry update and last doctor run UTC timestamps with second precision.
- Record a default display time zone for user-visible generated files and logs.
- Reserve maintenance fields for future upgrade locks.
- Provide global Context Control defaults for token budgets and diagnostic logging.

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
- Context Control default budgets and diagnostic logging controls.

### Excluded

- Full registry data.
- Agent integration mode per Workroot.
- Global knowledge body store.
- Cloud configuration.

## Dependencies

- `src/ai_workroot/state/environment.py`
- `src/ai_workroot/capabilities/system_health/doctor.py`
- `src/ai_workroot/state/jsonl.py`

## Requirements

### Functional Requirements

FR-001: `initialize_environment` must create `config.json` if missing.

FR-002: Existing custom config keys must be preserved.

FR-003: `config.json` must include `kind`, `environmentId`, `version`, `schemaVersion`, `layoutVersion`, `mode`, `createdAt`, and `updatedAt`.

FR-004: `config.json` must include summary counts for registered and active Workroots.

FR-005: Workroot registration must refresh summary counts.

FR-006: Doctor must record last doctor status and timestamp.

FR-007: Canonical timestamps in `config.json` must use UTC ISO-8601 with second precision. User-visible local timestamps must be rendered at output/log boundaries from the configured time zone.

FR-008: `config.json` must include global Context Control defaults for `defaultTargetTokens` and `defaultHardTokenLimit`.

FR-009: Context diagnostic logging must be disabled by default and must not include rendered Context Packages unless explicitly enabled.

FR-010: Context diagnostic logs must be written under the per-Workroot managed state directory, not inside the user-selected directory.

FR-011: `config.json` must include `time.timezone` and `time.locale`.

FR-012: New environments must default `time.timezone` from `AI_WORKROOT_TIMEZONE` when set, otherwise from the operating system time zone, otherwise UTC.

### Non-functional Requirements

NFR-001: Config writes must be local-only.

NFR-002: Config must not include absolute per-Workroot state lists by default.

NFR-003: Config must remain small enough for quick human inspection.

NFR-004: Context diagnostic logging must be bounded by retention settings so it does not grow without limit.

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
  "time": {
    "timezone": "Asia/Shanghai",
    "locale": "zh-CN"
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
  },
  "summary": {
    "registeredWorkrootCount": 1,
    "activeWorkrootCount": 1,
    "lastRegistryUpdatedAt": "2026-05-21T00:00:00Z",
    "lastDoctorStatus": "PASS",
    "lastDoctorRunAt": "2026-05-21T00:00:00Z",
    "lastMigrationId": null,
    "lastMigrationAt": null
  },
  "contextControl": {
    "defaultTargetTokens": 1200,
    "defaultHardTokenLimit": 2400,
    "diagnosticLogging": {
      "enabled": false,
      "includeRenderedPackage": false,
      "includeTraceSummary": true,
      "includeRetrievalSummary": true,
      "includeTokenEstimate": true,
      "retentionDays": 7,
      "maxEntriesPerWorkroot": 200
    }
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
- `load_context_control_config`

`workroot context` uses explicit CLI token flags first. If `--target-tokens` or `--hard-token-limit` is omitted, it uses global Context Control defaults from `AI_WORKROOT_HOME/config.json`.

### Runtime Behavior

Environment initialization creates or merges config. Registration refreshes counts. Doctor records health summary.

The environment time zone is captured once in `config.json` unless the user changes it. Canonical managed config timestamps remain UTC-only. User-visible generated timestamps are rendered from UTC at output boundaries using the configured time zone and locale.

Context generation reads global Context Control defaults. When diagnostic logging is enabled, each context request writes a JSONL diagnostic record to:

```text
AI_WORKROOT_HOME/workroots/<workroot_id>/logs/context-requests.jsonl
```

The record may include budget source, token estimate, selected candidate IDs, release drops, fallback behavior, mode plan, and trim steps. The full rendered Context Package is included only when `includeRenderedPackage` is explicitly true.

Diagnostic logs are observability artifacts rather than canonical state. For human analysis they include `displayTime` rendered with `time.timezone`, and they include `createdAt` for sorting, pruning, and cross-time-zone debugging.

### Error Handling

Malformed config should be treated as empty for this layer; lower-level state repair/backups remain covered by state tests.

### Security / Privacy

Config must not include user knowledge, sensitive content, or full per-Workroot metadata lists.

Diagnostic logs can include user-derived context summaries and, if explicitly enabled, rendered Context Packages. They must stay in managed state and must not be written into user-selected directories.

### Compatibility

Existing custom fields remain. Removed experimental keys such as `workroots`, `policies`, `paths`, `layout`, and `agentIntegration` are not kept in the minimal contract.

Existing configs without `contextControl` receive default values on the next environment config merge.

## Acceptance Criteria

AC-001:
Given an empty AI_WORKROOT_HOME
When a Workroot is initialized
Then config includes environment identity, UTC canonical timestamps, time zone config, summary counts, and maintenance status.

AC-002:
Given custom config keys
When another Workroot is initialized
Then custom keys remain and summary counts are refreshed.

AC-003:
Given doctor runs
When it completes
Then config records last doctor status and timestamp.

AC-004:
Given context budget defaults in config
When `workroot context` runs without token flags
Then the rendered package and trace use the configured target and hard limits.

AC-005:
Given context budget defaults in config
When `workroot context` runs with token flags
Then the CLI token flags override config and the trace records CLI as the budget source.

AC-006:
Given context diagnostic logging is enabled without rendered package logging
When context generation runs
Then a summary record is written under managed state logs and no logs directory is created in the user-selected directory.

AC-007:
Given `AI_WORKROOT_TIMEZONE=Asia/Shanghai`
When a Workroot is initialized
Then `config.json` contains `time.timezone=Asia/Shanghai`, canonical timestamps end with `Z`, and no local top-level time fields are written.

## Test Plan

### Unit Tests

- Environment helper tests if split later.
- Context Control config merge helper tests if split later.

### Integration Tests

- Covered through CLI smoke tests.
- Context budget and diagnostic logging integration tests.

### Manual Verification

- Inspect temporary `AI_WORKROOT_HOME/config.json` after smoke runs.
- Inspect temporary `AI_WORKROOT_HOME/workroots/<workroot_id>/logs/context-requests.jsonl` after diagnostic smoke runs.

## Migration / Rollback

No schema migration is required. Existing unknown keys are preserved unless explicitly removed from the minimal contract.

## Observability / Debugging

Config itself is the human-readable summary. Doctor also reports status through CLI.

Context diagnostic logs are opt-in observability artifacts. They provide explainable retrieval and token budget evidence without changing normal context output.

## Task Breakdown

T1: Define config helpers
- Change: Add config creation and merge helpers.
- Files likely affected: `src/ai_workroot/state/environment.py`
- Verification: CLI smoke tests.

T2: Refresh registry counts
- Change: Update summary during Workroot registration.
- Files likely affected: `src/ai_workroot/state/environment.py`
- Verification: repeated init smoke.

T3: Record doctor status
- Change: Update config summary after doctor runs.
- Files likely affected: `src/ai_workroot/capabilities/system_health/doctor.py`
- Verification: doctor summary smoke.

T4: Add Context Control defaults
- Change: Merge default token budgets and diagnostic logging controls into config.
- Files likely affected: `src/ai_workroot/state/environment.py`
- Verification: environment config smoke.

T5: Use global Context Control budgets
- Change: Resolve context token budgets from CLI flags, then config, then code defaults.
- Files likely affected: `src/ai_workroot/entrypoints/cli/main.py`, `src/ai_workroot/capabilities/context/builder.py`
- Verification: context CLI smoke.

T6: Add opt-in diagnostic logging
- Change: Write bounded context request summaries to per-Workroot managed logs when enabled.
- Files likely affected: `src/ai_workroot/capabilities/context/builder.py`
- Verification: context budget trace integration tests.

## Risks

- Config may grow into a duplicate registry if not kept constrained.
- Future maintenance lock behavior needs stricter write blocking semantics.
- Rendered package logging can expose user content if enabled; keep it explicitly opt-in and bounded.

## Open Questions

None.
