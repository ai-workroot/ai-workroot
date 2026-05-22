# Spec 029: Install, Dev Scripts, and Wrappers

## Status

Accepted for 0.9.530; compatibility wrapper notes superseded by `041-runnable-legacy-compat-removal.spec.md`

## Priority

P1

## Background

Install scripts and developer scripts previously lived under generic `scripts/`. The 0.9.530 architecture separated user installation from developer tooling. Spec 041 removes runnable compatibility wrappers from active paths.

## Goals

- Move or wrap user installation under `install/`.
- Keep `scripts/` limited to developer/release/review helpers.
- Move developer utilities under `scripts/dev/`.
- Make wrapper behavior explicit in docs.
- Keep installation sudo/admin-free by default.

## Non-goals

- Do not build a GUI installer.
- Do not create a full first-run consumer setup application.
- Do not restore compatibility wrappers as active paths after Spec 041.

## Scope

### Included

- `install/unix/install.sh`.
- `install/windows/install.ps1`.
- `scripts/dev/bootstrap-dev.sh` and `scripts/dev/bootstrap-dev.ps1` wrappers.
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

FR-005: Developer scripts must live under `scripts/dev/`.

### Non-functional Requirements

NFR-001: Shell scripts must pass syntax checks.

NFR-002: PowerShell scripts must pass parser checks when `pwsh` is available.

NFR-003: Scripts must not write managed state into user directories by default.

## Proposed Design

### Concepts

Install script: user-facing wrapper installer.

Developer script: repository maintenance or validation tool.

Compatibility wrapper: historical 0.9.530 transition script retained for old paths. Removed from active paths by Spec 041.

### File Layout

```text
install/unix/install.sh
install/windows/install.ps1
scripts/dev/bootstrap-dev.sh
scripts/dev/bootstrap-dev.ps1
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

Old script paths are not active wrappers after Spec 041. Historical source may remain only in non-runnable archive form.

## Acceptance Criteria

AC-001: Given `bash -n install/unix/install.sh`, when it runs, then syntax passes.

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

Add new `install/` scripts first. After Spec 041, rollback is a branch revert, not restoring active old wrappers.

## Observability / Debugging

Scripts print invoked package command and target install path in verbose/help mode.

## Task Breakdown

T1: Add install directory scripts
- Change: Move or copy wrapper installer logic into `install/unix` and `install/windows`.
- Files likely affected: `install/`.
- Verification: syntax and temp install smoke.

T2: Keep developer wrappers package-based
- Change: Ensure bootstrap-dev scripts delegate to package behavior and remain developer-only.
- Files likely affected: `scripts/dev/bootstrap-dev.*`.
- Verification: bootstrap-dev smoke tests.

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
