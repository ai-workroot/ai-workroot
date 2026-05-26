# Spec 024: Work and Asset Runtime Migration

## Status

Draft

## Priority

P0

## Background

Earlier 0.9.530 work used temporary compatibility owners for mature Public Seed capabilities. Spec 041 removes runnable legacy compatibility from active paths. The important product capabilities must remain owned by active Clean Workroot capability modules under `src/ai_workroot/`.

## Goals

- Move Work process capabilities into package runtime and core modules.
- Move artifact/decision/mind/knowledge-like outputs into Asset concepts.
- Preserve batch transaction and rollback behavior.
- Keep the useful legacy capabilities represented in active Work and Asset runtime behavior.
- Add package-first tests for each preserved capability.

## Non-goals

- Do not create team collaboration features.
- Do not preserve `Mind` or `Memory` as formal active domain terms.
- Do not publish user-facing files into the user directory unless explicitly authorized.

## Scope

### Included

- Task, AgentRun, WorkAction, WorkCheckpoint, RetrievalCard, InvalidationRecord, OperationTransaction, and HandoffPackage through the separate `handoff/` capability.
- Asset creation and publication metadata.
- Session summarize and continue/handoff behavior.
- Batch transaction rollback.

### Excluded

- Full UI.
- Remote sync.
- Vector retrieval.

## Dependencies

- Spec 005 Core Model.
- Spec 006 Asset Model.
- Spec 007 Release Control.
- Spec 013 Storage SQLite Schema.
- Spec 023 Active Package CLI and Legacy Isolation.

## Requirements

### Functional Requirements

FR-001: Package runtime must create and update Task records.

FR-002: Package runtime must create AgentRun and WorkAction records associated with tasks.

FR-003: Package runtime must record WorkCheckpoint records through `work/` and HandoffPackage records through `handoff/`.

FR-004: Package runtime must map legacy artifacts, decisions, knowledge, and results into Asset records with `asset_type`.

FR-005: Batch operations must be atomic or rollback recorded partial changes.

FR-006: Continue/session summarize behavior must produce package-owned handoff/context state, not root Public Seed files.

### Non-functional Requirements

NFR-001: Runtime functions must use storage repositories, not ad hoc file writes.

NFR-002: User-selected directories remain clean by default.

NFR-003: Work/Asset operations must be local-first and deterministic.

## Proposed Design

### Concepts

Work owns process records. Asset owns user-value records. Release Control overlays recall/release state over Work and Asset targets.

### Data Model

Canonical package models:

```text
Task
AgentRun
WorkAction
WorkCheckpoint
RetrievalCard
InvalidationRecord
OperationTransaction
HandoffPackage
Asset
AssetPublication
AssetSurface
```

Legacy `mind`, `knowledge`, `decision`, and `artifact` rows map to `Asset.asset_type`.

### File Layout

```text
src/ai_workroot/work/operations.py
src/ai_workroot/handoff/operations.py
src/ai_workroot/assets/operations.py
src/ai_workroot/release/operations.py
src/ai_workroot/state/sqlite.py
src/ai_workroot/work/model.py
src/ai_workroot/assets/model.py
```

No Work/Asset runtime state is written into the user directory by default.

### CLI / API

Future package commands may include:

```text
workroot task ...
workroot asset ...
workroot release ...
```

They are introduced only after package runtime behavior and tests are ready.

### Runtime Behavior

Runtime service functions load records, apply core invariants, persist canonical rows, update indexes, and return structured results for CLI formatting.

### Error Handling

Invalid IDs, missing Workroots, missing tasks, unsafe paths, and failed batch steps produce structured runtime errors. Batch failures record rollback evidence.

### Security / Privacy

Private/internal assets stay in managed state by default. User-directory publication requires explicit target surface and authorization.

### Compatibility

Runnable legacy script commands are removed from active paths by Spec 041. Historical source remains available for inspection under `docs/history/public-seed/code-archive/`.

## Acceptance Criteria

AC-001: Given a registered Workroot, when a package runtime task is created, then the task is stored under managed state and not in the user directory.

AC-002: Given an artifact-like legacy record, when migrated to package runtime, then it becomes an Asset record with equivalent provenance and visibility metadata.

AC-003: Given a batch operation fails mid-way, when rollback runs, then partial writes are removed or marked rolled back and an OperationTransaction records the outcome.

AC-004: Given legacy task tests, when package equivalents pass, then legacy tests are either moved under `tests/legacy/` or replaced.

## Test Plan

### Unit Tests

- Task lifecycle invariants.
- Asset lifecycle and publication policy.
- OperationTransaction rollback state.
- Legacy-to-Asset mapping.

### Integration Tests

- Task/run/action/checkpoint/handoff persistence through package storage.
- Batch apply and rollback.
- Continue/session summarize managed-state output.

### Manual Verification

- Use temporary `AI_WORKROOT_HOME` and user directory.
- Confirm no task/asset control files appear in user directory by default.

## Migration / Rollback

Migrate one capability group at a time. Keep the Public Seed client compatibility wrapper callable until package tests exist. Rollback by disabling package command exposure while preserving legacy adapter.

## Observability / Debugging

Work operations should produce diagnostic events where useful. Batch rollback should be inspectable by doctor/checkbot.

## Task Breakdown

T1: Add storage repositories for Work records
- Change: Implement repository functions for tasks/runs/actions/checkpoints/handoffs.
- Files likely affected: `src/ai_workroot/state/sqlite.py`, `src/ai_workroot/state/sqlite.py`.
- Verification: repository integration tests.

T2: Add Work runtime service
- Change: Implement package runtime operations equivalent to legacy task/run/action basics.
- Files likely affected: `src/ai_workroot/work/operations.py`.
- Verification: package Work integration tests.

T3: Add Asset runtime service
- Change: Implement asset create/update/publication metadata and legacy mapping.
- Files likely affected: `src/ai_workroot/assets/operations.py`.
- Verification: asset integration tests.

T4: Preserve batch rollback
- Change: Port transaction journal/rollback behavior from legacy client.
- Files likely affected: `src/ai_workroot/work/operations.py`, `src/ai_workroot/state/sqlite.py`.
- Verification: failure rollback tests.

T5: Verify capability parity after legacy removal
- Change: Ensure Work/Asset runtime tests cover capabilities formerly represented by Public Seed scripts.
- Files likely affected: `src/ai_workroot/work/operations.py`, `src/ai_workroot/assets/operations.py`, `tests/unit/`, `tests/integration/`.
- Verification: full unittest suite.

## Risks

- Hidden behavior in the legacy Workroot client is missed.
- Asset mapping drops provenance or visibility.
- Batch rollback semantics regress during migration.

## Open Questions

None.
