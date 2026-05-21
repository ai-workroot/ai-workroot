# Spec 030: Test Suite and Public Seed Quarantine

## Status

Draft

## Priority

P0

## Background

The repository still has tests that import legacy scripts directly and historical materials that must not be confused with active Clean Workroot architecture. The test suite must prove both package behavior and legacy preservation without keeping Public Seed active.

## Goals

- Split tests by purpose.
- Make package tests authoritative for active Clean Workroot behavior.
- Keep legacy tests explicitly legacy.
- Preserve Public Seed evidence only as history or fixtures.
- Add negative tests preventing active root regression.

## Non-goals

- Do not delete legacy capability evidence without matrix coverage.
- Do not make Public Seed active again.
- Do not require a release tag.

## Scope

### Included

- Test directory organization.
- Legacy test labeling.
- Public Seed quarantine fixtures.
- Docs/spec status checks.
- Release/checkbot validation tests.

### Excluded

- CI provider setup unless needed for local validation.
- Full historical documentation rewrite beyond quarantine markers.

## Dependencies

- Spec 016 Source Layout Migration.
- Spec 019 Full Test and Migration Plan.
- Spec 022 CI and Release Gates.
- Specs 023 through 029.

## Requirements

### Functional Requirements

FR-001: All test-like Python files must live under `tests/` or be renamed so they are not collected as tests.

FR-002: Package behavior tests must import `ai_workroot.*`, not `scripts.*`.

FR-003: Legacy tests may import `scripts.*` only under explicit legacy naming or directory.

FR-004: Negative tests must fail if root tracked `space/`, `.workroot/`, `AGENTS.md`, `CLAUDE.md`, or `.idea/` returns as active architecture.

FR-005: Docs/spec checks must ensure 0.9.530 specs remain accepted/draft with consistent reading order.

### Non-functional Requirements

NFR-001: Full test suite must run through `python3 -m unittest discover -s tests -v`.

NFR-002: Smoke tests must use temporary `AI_WORKROOT_HOME`.

NFR-003: Tests must not depend on the developer's real GitHub, SSH, or global environment.

## Proposed Design

### Concepts

Active test: validates current Clean Workroot package behavior.

Legacy test: validates preserved Public Seed compatibility only.

Negative test: prevents forbidden architecture regression.

### File Layout

```text
tests/unit/
tests/integration/
tests/smoke/
tests/negative/
tests/legacy/
tests/fixtures/
```

### CLI / API

Standard test command:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

### Runtime Behavior

Tests create temporary state. No test should write into real `AI_WORKROOT_HOME` or the developer's user directories.

### Error Handling

If an optional platform tool is missing, test reports skip with reason only for optional checks.

### Security / Privacy

Test fixtures must not contain local absolute paths, private user names, or real managed-state paths.

### Compatibility

Legacy tests remain until package parity is proven. They are moved or renamed rather than silently removed.

## Acceptance Criteria

AC-001: Given `git ls-files`, when scanned for test-like files outside `tests/`, then none are found except explicitly documented helper scripts.

AC-002: Given package tests, when run, then active Clean Workroot behavior is covered through `ai_workroot.*` imports.

AC-003: Given legacy tests, when run, then their path or name clearly marks legacy compatibility.

AC-004: Given root tracked Public Seed files, when release validation tests run, then they fail.

AC-005: Given ignored local `AGENTS.md`, `CLAUDE.md`, or `.idea/`, when validation runs, then it does not fail release surface checks.

## Test Plan

### Unit Tests

- Import-boundary checks.
- Docs/spec reading order checks.
- Release surface path classifier.

### Integration Tests

- Package storage/runtime/context flows.
- Legacy preservation parity checks.

### Manual Verification

- Run full unittest discovery.
- Run `git ls-files` audits.
- Run checkbot.

## Migration / Rollback

Move tests gradually. If a package test fails after migration, keep the legacy test and mark the package behavior gap instead of deleting coverage.

## Observability / Debugging

Test audit output lists package tests, legacy tests, smoke tests, negative tests, and any tests still importing scripts.

## Task Breakdown

T1: Add test audit command
- Change: Add or document audit for test-like files and script imports.
- Files likely affected: `scripts/dev/validate-release.sh`, tests.
- Verification: audit output in checkbot.

T2: Move legacy tests
- Change: Move script-importing tests to `tests/legacy/` or rename with legacy labels.
- Files likely affected: `tests/legacy/`, existing tests.
- Verification: unittest discovery.

T3: Add package parity tests
- Change: Add package tests for each migrated behavior before retiring legacy tests.
- Files likely affected: `tests/unit/`, `tests/integration/`, `tests/smoke/`.
- Verification: full suite.

T4: Add Public Seed negative tests
- Change: Ensure active root files fail only when tracked, not ignored.
- Files likely affected: `tests/negative/`, release doctor tests.
- Verification: negative test suite.

## Risks

- Moving tests changes discovery behavior.
- Legacy tests remain too influential and hide package gaps.
- Fixtures accidentally preserve private/local paths.

## Open Questions

None.
