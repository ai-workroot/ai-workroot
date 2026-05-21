# Spec 023: Active Package CLI and Legacy Isolation

## Status

Draft

## Priority

P0

## Background

AI Workroot now has a package CLI at `ai_workroot.cli.main`, but older command behavior still exists in `scripts/workroot_cli.py`. Clean Workroot users must see a small current command surface, while old Public Seed capabilities must remain available only as explicitly legacy behavior until replaced.

## Goals

- Make package CLI the active Clean Workroot command surface.
- Keep primary help limited to `init`, `list`, `status`, `context`, `doctor`, and `bootstrap-dev`.
- Move or hide legacy seed commands under an explicit legacy boundary.
- Keep script entry points as wrappers or legacy adapters only.
- Preserve old capability tests while making package CLI tests authoritative for Clean Workroot.

## Non-goals

- Do not implement all Work/Asset commands in this spec.
- Do not delete legacy command implementations before replacement specs complete.
- Do not create a tag, release, or merge.

## Scope

### Included

- `src/ai_workroot/cli/` command organization.
- `scripts/workroot_cli.py` delegation or legacy isolation.
- CLI help text and command discovery tests.
- Wrapper compatibility behavior.

### Excluded

- Work/Asset runtime implementation.
- Context Control internals.
- Storage schema changes beyond CLI wiring needs.

## Dependencies

- Spec 014 CLI User Flows.
- Spec 016 Source Layout Migration.
- Spec 024 Work and Asset Runtime Migration.
- Existing `ai_workroot.runtime.*` functions.

## Requirements

### Functional Requirements

FR-001: `python -m ai_workroot --help` must show Clean Workroot primary commands only.

FR-002: `workroot --help` must resolve to the package CLI when installed.

FR-003: Clean commands invoked through `scripts/workroot_cli.py` must delegate to package behavior or produce equivalent output.

FR-004: Legacy seed commands must be hidden from default help or exposed only under `workroot legacy ...`.

FR-005: Legacy commands must show clear legacy wording if invoked directly.

### Non-functional Requirements

NFR-001: CLI modules must not import SQLite/storage implementations directly.

NFR-002: CLI output must use Clean Workroot wording, not Public Seed as active architecture.

NFR-003: Wrapper behavior must be testable without mutating real user state.

## Proposed Design

### Concepts

Primary command: a Clean Workroot command supported as current user flow.

Legacy command: a compatibility command for old Public Seed behavior, not part of current Clean Workroot primary UX.

### File Layout

Target:

```text
src/ai_workroot/cli/main.py
src/ai_workroot/cli/commands/init.py
src/ai_workroot/cli/commands/list.py
src/ai_workroot/cli/commands/status.py
src/ai_workroot/cli/commands/context.py
src/ai_workroot/cli/commands/doctor.py
src/ai_workroot/cli/commands/bootstrap_dev.py
src/ai_workroot/cli/commands/legacy.py
scripts/workroot_cli.py
```

`scripts/workroot_cli.py` remains only as a wrapper or legacy adapter.

### CLI / API

Primary commands:

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

Legacy boundary:

```text
workroot legacy task ...
workroot legacy run ...
workroot legacy action ...
workroot legacy artifact ...
workroot legacy retrieval-card ...
workroot legacy checkpoint ...
workroot legacy invalidation ...
workroot legacy session ...
workroot legacy continue ...
workroot legacy batch ...
```

If a legacy command is not yet reachable through package CLI, it may remain hidden in `scripts/workroot_cli.py` with tests labeled legacy.

### Runtime Behavior

The CLI parses arguments and calls runtime functions. Business decisions stay in runtime/core/indexing/storage/agent modules.

### Error Handling

Invalid Clean Workroot commands return concise CLI errors. Legacy commands return clear legacy warnings when invoked.

### Security / Privacy

No CLI command may print absolute managed-state paths in Native Agent Entry files. Smoke tests must use temporary `AI_WORKROOT_HOME`.

### Compatibility

The installed `workroot` command remains package-based. Existing script-based tests are migrated gradually to package tests or legacy tests.

## Acceptance Criteria

AC-001: Given a clean checkout, when `python -m ai_workroot --help` runs, then primary help contains only Clean Workroot primary commands.

AC-002: Given `scripts/workroot_cli.py init`, when invoked with a temporary `AI_WORKROOT_HOME`, then behavior matches package init and does not write managed state into the user directory.

AC-003: Given a legacy task command, when default package help is shown, then the legacy command is absent from primary help.

AC-004: Given a legacy command is still supported, when invoked through its legacy path, then the output identifies it as legacy compatibility.

## Test Plan

### Unit Tests

- Parser tests for primary commands.
- Parser tests for mutually exclusive Native Agent Entry flags.
- Import-boundary test that CLI does not import storage directly.

### Integration Tests

- Package CLI init/list/status/context/doctor/bootstrap-dev smoke.
- Script wrapper delegation tests for primary commands.

### Manual Verification

- Run `python -m ai_workroot --help`.
- Run `scripts/workroot_cli.py --help`.

## Migration / Rollback

Migrate primary commands first. Keep old script command code behind legacy boundary until replacement behavior passes package tests. Rollback by restoring script command handling while keeping package CLI unchanged.

## Observability / Debugging

CLI smoke output should be captured by checkbot. `doctor --release` should flag primary help if Public Seed active commands are exposed.

## Task Breakdown

T1: Split package command modules if needed
- Change: Move command parser/action code from `cli/main.py` into `cli/commands/*` without behavior change.
- Files likely affected: `src/ai_workroot/cli/main.py`, `src/ai_workroot/cli/commands/*.py`.
- Verification: CLI parser unit tests and `python -m ai_workroot --help`.

T2: Add legacy command boundary
- Change: Define `legacy` namespace or hidden adapter rules.
- Files likely affected: `src/ai_workroot/cli/commands/legacy.py`, `scripts/workroot_cli.py`.
- Verification: Help text tests.

T3: Delegate script Clean commands
- Change: Make script primary commands call package CLI/runtime.
- Files likely affected: `scripts/workroot_cli.py`.
- Verification: Script wrapper smoke tests.

T4: Move tests into package/legacy categories
- Change: Convert package command tests to `ai_workroot` imports; label old command tests as legacy.
- Files likely affected: `tests/smoke/`, `tests/legacy/`, existing CLI tests.
- Verification: Full unittest suite.

## Risks

- Script and package CLI behavior drift.
- Legacy command discoverability confuses Clean Workroot users.
- Tests continue to validate only script behavior.

## Open Questions

None.
