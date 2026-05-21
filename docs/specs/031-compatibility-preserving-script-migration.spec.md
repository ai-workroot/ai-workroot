# Spec 031: Compatibility-Preserving Script Migration

## Status

Draft

## Priority

P0

## Background

The 0.9.530 Clean Workroot architecture reset has moved major foundations into `src/ai_workroot/`, but several mature legacy behaviors still live in `scripts/`. The remaining migration must finish the architecture direction without breaking existing local compatibility. The first completed version should make source modules the implementation owner while keeping old script paths callable. A later version can remove compatibility after separate review.

## Goals

- Move remaining script-owned behavior into package-owned modules under `src/ai_workroot/`.
- Preserve old script entry points, imports, and legacy command behavior during Part 1.
- Make old Public Seed behavior explicitly legacy and compatibility-scoped.
- Keep Clean Workroot primary CLI and docs free of Public Seed as active architecture.
- Archive original script implementations for history after wrapper conversion.
- Define a separate Part 2 path for compatibility removal.

## Non-goals

- Do not remove old script compatibility in Part 1.
- Do not delete legacy Public Seed capability before package ownership and regression tests exist.
- Do not reintroduce `space/`, `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md` as active Clean Workroot architecture.
- Do not create a tag, release, or merge.
- Do not introduce remote LLM, remote embedding, vector database, or cloud service dependencies.

## Scope

### Included

- `scripts/workroot_client.py` compatibility migration.
- `scripts/workroot_cli.py` compatibility migration.
- Small legacy helper script migration.
- Legacy operation manifest migration.
- Package release validation migration where safe.
- Wrapper tests, package-first tests, and legacy compatibility tests.
- Historical archive snapshots under `docs/history/0.9.530/scripts/`.

### Excluded

- Removing compatibility paths.
- Renaming user-facing product concepts beyond already accepted Clean Workroot terminology.
- Rewriting mature legacy behavior into a new product model in the same step as file movement.
- GUI installer or C-end first-run application.

## Dependencies

- Spec 016 Source Layout Migration.
- Spec 023 Active Package CLI and Legacy Isolation.
- Spec 024 Work and Asset Runtime Migration.
- Spec 028 System Health, Validation, and Checkbot.
- Spec 030 Test Suite and Public Seed Quarantine.
- `docs/dev/0.9.530/final-compatibility-preserving-script-migration-design.md`.

## Requirements

### Functional Requirements

FR-001: Remaining script-owned behavior must move into package modules under `src/ai_workroot/`.

FR-002: `scripts/workroot_client.py` must remain import-compatible for Part 1.

FR-003: `scripts/workroot_cli.py` must remain callable for Part 1.

FR-004: Clean commands invoked through script compatibility must delegate to package Clean Workroot behavior.

FR-005: Legacy Public Seed commands must remain available for compatibility but hidden from primary Clean Workroot help.

FR-006: Small helper scripts must remain callable with their current command-line arguments.

FR-007: Original script implementations must be archived under `docs/history/0.9.530/scripts/` before or when wrappers replace them.

FR-008: `src/ai_workroot/core/` must not own legacy command recipes after the migration; legacy recipes belong under a legacy runtime/CLI boundary.

FR-009: Package tests must become authoritative for migrated behavior.

FR-010: Wrapper tests must prove old script paths still work.

### Non-functional Requirements

NFR-001: Part 1 must be behavior-preserving.

NFR-002: The migration must proceed in small steps with targeted tests after each step.

NFR-003: Clean Mode must continue to keep managed state outside user-selected directories by default.

NFR-004: The active package architecture must remain local-first.

NFR-005: Compatibility modules must be clearly named as legacy to avoid confusing them with active Clean Workroot domain modules.

NFR-006: Rollback must be possible by reverting the last migration commit because old callable surfaces remain.

## Proposed Design

### Concepts

Part 1: the compatibility-preserving migration. The implementation owner moves into `src/ai_workroot/`; wrappers keep old paths working.

Part 2: the future compatibility-removal migration. It is a separate branch/version and requires separate approval.

Legacy Seed: the package namespace for old Public Seed behavior preserved for compatibility.

Wrapper: a script file that imports package behavior and exposes the old command/import surface.

Archive snapshot: a historical copy under `docs/history/0.9.530/scripts/`; it is not active product code.

### Data Model

No new product data model is required by this Spec. The migration may move existing legacy dataclasses and record helpers into:

```text
ai_workroot.runtime.legacy_seed.models
ai_workroot.runtime.legacy_seed.client
ai_workroot.runtime.legacy_seed.registries
```

Canonical Clean Workroot data models remain governed by Specs 005 through 013.

### File Layout

Target package layout:

```text
src/ai_workroot/runtime/legacy_seed/
  __init__.py
  client.py
  models.py
  time.py
  filesystem.py
  registries.py
  batch.py
  session.py
  task_creation.py
  task_listing.py
  setup.py
  profile.py
  upgrade.py
  registry_tools.py
  operation_manifest.py
  sqlite_rebuild.py
src/ai_workroot/cli/legacy_seed.py
src/ai_workroot/runtime/release_validation.py
```

Script compatibility files remain:

```text
scripts/workroot_client.py
scripts/workroot_cli.py
scripts/new_task.py
scripts/list_tasks.py
scripts/setup_workroot.py
scripts/update_usage_direction.py
scripts/upgrade_workroot.py
scripts/add_registry_row.py
scripts/rebuild_sqlite.py
scripts/validate_kernel.py
```

Historical snapshots live in:

```text
docs/history/0.9.530/scripts/
```

No migration step may write managed Workroot state into a user-selected directory by default.

### CLI / API

Part 1 preserves:

```text
python scripts/workroot_cli.py <clean-command>
python scripts/workroot_cli.py <legacy-command>
python scripts/new_task.py ...
python scripts/list_tasks.py ...
python scripts/setup_workroot.py ...
python scripts/update_usage_direction.py ...
python scripts/upgrade_workroot.py ...
python scripts/add_registry_row.py ...
python scripts/rebuild_sqlite.py
python scripts/validate_kernel.py --release
```

Clean package CLI remains:

```text
python -m ai_workroot init
python -m ai_workroot list
python -m ai_workroot status
python -m ai_workroot context
python -m ai_workroot doctor
python -m ai_workroot bootstrap-dev
```

Primary help must not present legacy Public Seed commands as active Clean Workroot commands.

### Runtime Behavior

Package modules perform behavior. Scripts delegate.

For old behavior, `runtime/legacy_seed` may preserve Public Seed file layout behavior, but it must be named and tested as compatibility behavior. It must not become the active Clean Workroot path.

### Error Handling

Wrapper errors should match existing behavior where practical. Package-owned errors may improve messages, but compatibility tests must cover critical failure behavior such as duplicate registry entries, invalid task IDs, missing registries, and failed batch rollback.

### Security / Privacy

No compatibility wrapper may bypass existing Clean Mode rules for Clean commands. Legacy Public Seed commands are allowed to operate on legacy Public Seed layouts only because they are compatibility behavior.

### Compatibility

Compatibility is a hard requirement for Part 1. Removal is deferred to Part 2.

## Acceptance Criteria

AC-001:
Given a test imports `scripts/workroot_client.py`
When it accesses legacy public names such as `WorkrootClient`, `now_utc`, and `slugify`
Then the import still succeeds through a wrapper.

AC-002:
Given a user invokes `python scripts/workroot_cli.py init`
When the command runs with a temporary `AI_WORKROOT_HOME`
Then it delegates to package Clean Workroot init behavior.

AC-003:
Given a user invokes a legacy hidden command through `scripts/workroot_cli.py`
When the command is still within Part 1 compatibility scope
Then the command remains available and is tested as legacy behavior.

AC-004:
Given a small helper script was migrated
When its old script path is invoked
Then it accepts the same arguments and produces compatible output.

AC-005:
Given `python -m ai_workroot --help`
When primary help is rendered
Then legacy Public Seed commands are absent from primary help.

AC-006:
Given a script implementation has been replaced by a wrapper
When the migration commit is inspected
Then the original implementation is preserved under `docs/history/0.9.530/scripts/`.

AC-007:
Given the full validation suite runs
When Part 1 is complete
Then package tests, legacy compatibility tests, wrapper tests, compile checks, release doctor, and release validation pass.

## Test Plan

### Unit Tests

- Package import tests for `ai_workroot.runtime.legacy_seed`.
- Legacy helper tests converted to package imports.
- Wrapper re-export tests for `scripts/workroot_client.py`.
- Import-boundary tests that keep Clean Workroot modules separate from legacy seed modules.

### Integration Tests

- Legacy `WorkrootClient` task/run/action/artifact/checkpoint/invalidation/mind/session/batch behavior through package module.
- Script wrapper invocation for each small helper.
- Legacy CLI command invocation through `scripts/workroot_cli.py`.
- Clean CLI delegation through `scripts/workroot_cli.py`.

### Manual Verification

- Run Clean Mode smoke with a temporary `AI_WORKROOT_HOME`.
- Run a legacy Public Seed fixture smoke if fixtures exist.
- Confirm primary package help remains Clean Workroot only.
- Confirm historical archives are not executable active code.

## Migration / Rollback

Migrate one capability group per commit. If a phase fails, revert the last commit. Because Part 1 keeps old script paths callable, rollback does not require user-facing command migration.

Do not remove compatibility until Part 2.

## Observability / Debugging

The final handoff must include:

- script import audit;
- wrapper list;
- package-owned module list;
- legacy command compatibility status;
- validation command outputs;
- known limitations before Part 2.

`doctor --release` and release validation should continue to detect active-root Public Seed regressions.

## Task Breakdown

T1: Baseline audit
- Change: Run tests, compile checks, release doctor, release validation, and script import audit.
- Files likely affected: none.
- Verification: Baseline commands pass before migration.

T2: Add legacy seed package shell
- Change: Create `src/ai_workroot/runtime/legacy_seed/` modules with no behavior change.
- Files likely affected: `src/ai_workroot/runtime/legacy_seed/__init__.py`.
- Verification: Import-boundary tests and compile checks pass.

T3: Move neutral helpers from `workroot_client.py`
- Change: Move dataclasses, time helpers, slug helpers, registry helpers, and filesystem helpers into package modules.
- Files likely affected: `src/ai_workroot/runtime/legacy_seed/models.py`, `time.py`, `registries.py`, `filesystem.py`, `scripts/workroot_client.py`.
- Verification: `tests/test_registry_store.py` and `tests/test_workroot_client.py`.

T4: Move `WorkrootClient`
- Change: Move the legacy `WorkrootClient` facade into `ai_workroot.runtime.legacy_seed.client`; keep script re-export compatibility.
- Files likely affected: `src/ai_workroot/runtime/legacy_seed/client.py`, `scripts/workroot_client.py`, tests.
- Verification: legacy client and CLI tests pass.

T5: Move small helper scripts
- Change: Move helper script behavior into package modules and keep script wrappers.
- Files likely affected: `task_creation.py`, `task_listing.py`, `setup.py`, `profile.py`, `upgrade.py`, `registry_tools.py`, `sqlite_rebuild.py`, corresponding scripts.
- Verification: targeted helper tests plus wrapper invocation tests.

T6: Move legacy CLI parser/dispatch
- Change: Move legacy command parsing and dispatch into `src/ai_workroot/cli/legacy_seed.py`; keep `scripts/workroot_cli.py` wrapper.
- Files likely affected: `src/ai_workroot/cli/legacy_seed.py`, `scripts/workroot_cli.py`.
- Verification: CLI tests, command discovery tests, package help tests.

T7: Move legacy operation manifest out of core
- Change: Move operation recipes into `runtime/legacy_seed/operation_manifest.py`; keep core extension concepts stable.
- Files likely affected: `src/ai_workroot/core/extensions.py`, `src/ai_workroot/runtime/legacy_seed/operation_manifest.py`.
- Verification: architecture contract and CLI discovery tests.

T8: Move release validation authority
- Change: Move package-owned release validation logic into `runtime/release_validation.py`; keep `scripts/validate_kernel.py` callable.
- Files likely affected: `src/ai_workroot/runtime/release_validation.py`, `scripts/validate_kernel.py`.
- Verification: release gate tests, public seed surface tests, release doctor.

T9: Archive script snapshots
- Change: Store original script implementations under `docs/history/0.9.530/scripts/`.
- Files likely affected: `docs/history/0.9.530/scripts/`.
- Verification: archive paths exist for converted wrappers.

T10: Final Part 1 validation
- Change: Run full checkbot and produce review handoff.
- Files likely affected: docs handoff only if requested.
- Verification: full unittest, py_compile, release doctor, validate kernel, release script, diff check.

## Risks

- A legacy behavior in `workroot_client.py` is missed during movement.
- Wrappers become too thick and continue to hide product logic in scripts.
- Tests still validate only old script behavior instead of package behavior.
- Legacy Public Seed language leaks back into Clean Workroot primary help.
- Archival snapshots are mistaken for active code.

## Open Questions

None.

Part 1 preserves compatibility. Part 2 removes compatibility only after separate approval.
