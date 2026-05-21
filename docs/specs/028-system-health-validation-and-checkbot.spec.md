# Spec 028: System Health, Validation, and Checkbot

## Status

Draft

## Priority

P0

## Background

0.9.530 needs a package-owned release validation path. `scripts/compat/validate_kernel.py` remains useful as a historical baseline, but it cannot be the final authority for Clean Workroot release readiness. The project also needs a repeatable checkbot command for branch checkpoints without tagging or releasing.

## Goals

- Make `python -m ai_workroot doctor --release` the package release validator.
- Keep `scripts/dev/validate-release.sh` as checkbot wrapper.
- Ensure ignored local files such as `.idea/`, `AGENTS.md`, and `CLAUDE.md` do not fail release surface checks.
- Ensure tracked root Public Seed active files fail release checks.
- Produce exact validation outputs for review handoff.

## Non-goals

- Do not tag or create releases.
- Do not replace CI provider setup in this spec.
- Do not require PowerShell on systems where it is unavailable.

## Scope

### Included

- Package release doctor checks.
- Checkbot script behavior.
- Release surface checks.
- Validation command documentation.
- Smoke test orchestration with temporary state.

### Excluded

- GitHub release creation.
- Remote review automation.

## Dependencies

- Spec 012 System Health Doctor Migration.
- Spec 017 Release Validation.
- Spec 022 CI and Release Gates.
- Spec 030 Test Suite and Public Seed Quarantine.

## Requirements

### Functional Requirements

FR-001: Package release doctor must fail tracked root `AGENTS.md`, `CLAUDE.md`, `space/`, `.workroot/`, and `.idea/`.

FR-002: Package release doctor must allow ignored local `AGENTS.md`, `CLAUDE.md`, and `.idea/`.

FR-003: Checkbot must run compile, unittest, release doctor, release validator, and git diff whitespace checks.

FR-004: Checkbot must not commit, tag, push, merge, or create releases.

FR-005: Checkbot smoke tests must use temporary `AI_WORKROOT_HOME`.

### Non-functional Requirements

NFR-001: Checkbot output must be copyable into review handoff.

NFR-002: Validation must not depend on user-local managed state.

NFR-003: Validation must be deterministic across repeated runs.

## Proposed Design

### Concepts

Doctor is a diagnostic runtime command. Checkbot is a developer validation wrapper.

### Data Model

Doctor results use structured findings:

```text
check_id
status
severity
message
suggested_action
evidence
```

### File Layout

```text
src/ai_workroot/runtime/doctor.py
src/ai_workroot/core/health.py
scripts/dev/validate-release.sh
docs/dev/0.9.530/checkbot.md
tests/smoke/
tests/negative/
```

### CLI / API

```text
python -m ai_workroot doctor --release
scripts/dev/validate-release.sh
```

### Runtime Behavior

Release doctor inspects tracked files through Git where available, validates import boundaries, checks dependency red lines, and verifies Public Seed quarantine rules.

### Error Handling

Missing optional tools are warnings unless the checked behavior is required. Validation scripts exit nonzero only on required failures.

### Security / Privacy

Smoke tests must not inspect or mutate real `AI_WORKROOT_HOME`. Output must not include private paths except temporary test paths.

### Compatibility

`scripts/compat/validate_kernel.py --release` may remain in checkbot as baseline until package release doctor fully supersedes it.

## Acceptance Criteria

AC-001: Given ignored local `.idea/`, when release doctor runs, then it passes the release surface check.

AC-002: Given tracked root `AGENTS.md`, when release doctor runs, then it fails with actionable diagnostic.

AC-003: Given checkbot is run, when all checks pass, then it exits 0 without changing Git history.

AC-004: Given a missing optional PowerShell parser, when checkbot runs on macOS/Linux, then it reports the limitation without failing required checks.

## Test Plan

### Unit Tests

- Doctor result rendering.
- Tracked vs ignored path classification.
- Import boundary scanner.

### Integration Tests

- Release doctor with temporary Git fixtures.
- Checkbot script dry run or real run in repo.
- Clean Mode smoke under temp `AI_WORKROOT_HOME`.

### Manual Verification

- Run package release doctor.
- Run `scripts/dev/validate-release.sh`.

## Migration / Rollback

Add package release doctor checks before removing historical validator from the gate. Rollback keeps `validate_kernel.py` as baseline while preserving new doctor tests.

## Observability / Debugging

Checkbot prints each command before execution and captures exit status. Doctor output lists PASS/WARN/FAIL findings.

## Task Breakdown

T1: Expand release doctor
- Change: Add checks for tracked root files, import boundaries, dependency red lines, and validation surface.
- Files likely affected: `src/ai_workroot/runtime/doctor.py`.
- Verification: doctor unit/integration tests.

T2: Harden checkbot wrapper
- Change: Ensure checkbot uses package validator and temp state smokes.
- Files likely affected: `scripts/dev/validate-release.sh`.
- Verification: smoke validator test.

T3: Add checkbot docs
- Change: Document commands and non-release behavior.
- Files likely affected: `docs/dev/0.9.530/checkbot.md`.
- Verification: docs scan.

T4: Add Git surface fixtures
- Change: Test tracked vs ignored root files.
- Files likely affected: `tests/negative/`, `tests/smoke/`.
- Verification: full unittest suite.

## Risks

- Release validation becomes too strict for ignored local files.
- Checkbot accidentally depends on local user environment.
- Historical validator conflicts with Clean Workroot release doctor.

## Open Questions

None.
