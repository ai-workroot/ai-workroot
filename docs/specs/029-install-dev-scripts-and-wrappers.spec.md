# Spec 029: Install, Dev Scripts, and Wrappers

## Status

Draft

## Priority

P1

## Background

Install scripts and developer scripts currently live under generic `scripts/`. The 0.9.530 architecture wants user installation separated from developer tooling, while retaining simple wrapper scripts for compatibility.

## Goals

- Move or wrap user installation under `install/`.
- Keep `scripts/` wrappers thin.
- Move developer utilities under `scripts/dev/`.
- Make wrapper behavior explicit in docs.
- Keep installation sudo/admin-free by default.

## Non-goals

- Do not build a GUI installer.
- Do not create a full first-run consumer setup application.
- Do not remove compatibility wrappers until docs and tests are updated.

## Scope

### Included

- `install/unix/install.sh`.
- `install/windows/install.ps1`.
- `scripts/install.sh` and `scripts/install.ps1` wrappers.
- `scripts/bootstrap-dev.sh` and `scripts/bootstrap-dev.ps1` wrappers.
- Developer validation utilities under `scripts/dev/`.

### Excluded

- Package publishing to PyPI.
- GitHub release creation.

## Dependencies

- Spec 015 Installation Scripts.
- Spec 023 Active Package CLI and Legacy Isolation.
- Spec 028 System Health, Validation, and Checkbot.

## Requirements

### Functional Requirements

FR-001: User install scripts must install or update the `workroot` package/wrapper without sudo/admin by default.

FR-002: Repeated install must be idempotent.

FR-003: Install script help must state whether it is a wrapper installer or full setup.

FR-004: bootstrap-dev scripts must call package `bootstrap-dev` behavior.

FR-005: Developer scripts must live under `scripts/dev/` unless they are compatibility wrappers.

### Non-functional Requirements

NFR-001: Shell scripts must pass syntax checks.

NFR-002: PowerShell scripts must pass parser checks when `pwsh` is available.

NFR-003: Scripts must not write managed state into user directories by default.

## Proposed Design

### Concepts

Install script: user-facing wrapper installer.

Developer script: repository maintenance or validation tool.

Compatibility wrapper: script retained for old paths but delegating to the active package command.

### File Layout

```text
install/unix/install.sh
install/windows/install.ps1
scripts/install.sh
scripts/install.ps1
scripts/bootstrap-dev.sh
scripts/bootstrap-dev.ps1
scripts/dev/validate-release.sh
```

### CLI / API

Install output should describe:

```text
installed wrapper location
workroot --help command
no sudo/admin required by default
```

### Runtime Behavior

Scripts locate repository/package entry point and execute package commands. They do not implement product business logic.

### Error Handling

Scripts fail with clear missing Python, missing repository, or permission messages. They do not silently fall back to global privileged installs.

### Security / Privacy

Scripts must not read user content directories unless the user passes them explicitly. Smoke tests use temporary directories.

### Compatibility

Old script paths may remain as wrappers with warnings or docs links.

## Acceptance Criteria

AC-001: Given `bash -n scripts/install.sh`, when it runs, then syntax passes.

AC-002: Given temp install dir, when install script runs twice, then the second run succeeds without changing user config.

AC-003: Given bootstrap-dev wrapper, when it runs with temporary `AI_WORKROOT_HOME`, then package bootstrap-dev initializes state and no commit/tag/push occurs.

AC-004: Given script docs, when reviewed, then install is described as wrapper installation, not full GUI setup.

## Test Plan

### Unit Tests

- None required for shell-only wrappers beyond parser/smoke tests.

### Integration Tests

- Unix install temp-dir smoke.
- bootstrap-dev wrapper temp-state smoke.
- Optional PowerShell parser test when available.

### Manual Verification

- Run `workroot --help` from installed wrapper path.
- Confirm no sudo/admin required.

## Migration / Rollback

Add new `install/` scripts first, then make old script paths delegate. Rollback by restoring old wrappers while keeping package CLI unchanged.

## Observability / Debugging

Scripts print invoked package command and target install path in verbose/help mode.

## Task Breakdown

T1: Add install directory scripts
- Change: Move or copy wrapper installer logic into `install/unix` and `install/windows`.
- Files likely affected: `install/`, `scripts/install.*`.
- Verification: syntax and temp install smoke.

T2: Thin old wrappers
- Change: Make old install/bootstrap script paths delegate and document compatibility.
- Files likely affected: `scripts/install.sh`, `scripts/install.ps1`, `scripts/bootstrap-dev.*`.
- Verification: wrapper smoke tests.

T3: Move developer utilities
- Change: Move dev-only scripts under `scripts/dev/` or document why retained.
- Files likely affected: `scripts/dev/`, docs.
- Verification: release surface audit.

## Risks

- Moving scripts breaks existing test paths.
- PowerShell validation remains unavailable locally.
- Wrapper docs imply more setup than implemented.

## Open Questions

None.

