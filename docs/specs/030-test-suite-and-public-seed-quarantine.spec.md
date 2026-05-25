# Spec 030: Test Suite and Public Seed Quarantine

## Status

Accepted for 0.9.530; legacy-test notes superseded by `041-runnable-legacy-compat-removal.spec.md`

## Priority

P0

## Background

The repository previously had tests that imported legacy scripts directly and historical materials that must not be confused with active Clean Workroot architecture. After Spec 041, default tests prove package behavior and archive boundaries without executing runnable legacy compatibility.

## Goals

- Split tests by purpose.
- Make package tests authoritative for active Clean Workroot behavior.
- Preserve legacy tests only as non-runnable historical archive material unless a package parity test replaces them.
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

FR-003: Active tests must not import `scripts.*` legacy compatibility paths. Historical tests are archived as non-runnable `.txt` material.

FR-004: Negative tests must fail if root tracked `space/`, `.workroot/`, `AGENTS.md`, `CLAUDE.md`, or `.idea/` returns as active architecture.

FR-005: Docs/spec checks must ensure 0.9.530 specs remain accepted/draft with consistent reading order.

### Non-functional Requirements

NFR-001: Default test suite must run through `python3 -m unittest discover -s tests -v` without running E2E, longrun, or live-agent tests.

NFR-002: E2E suites must be opt-in only through `AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite <suite>`.

NFR-003: Smoke tests must use temporary `AI_WORKROOT_HOME`.

NFR-004: Tests must not depend on the developer's real GitHub, SSH, or global environment.

## Proposed Design

### Concepts

Active test: validates current Clean Workroot package behavior.

Legacy test: historical test material from the Public Seed era. It is non-runnable after Spec 041 unless rewritten as an active package parity test.

Negative test: prevents forbidden architecture regression.

### File Layout

```text
tests/unit/
tests/integration/
tests/smoke/
tests/negative/
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

Legacy tests are archived after package parity is proven or intentionally retired. Active default discovery must not execute legacy script tests.

## Acceptance Criteria

AC-001: Given `git ls-files`, when scanned for test-like files outside `tests/`, then none are found except explicitly documented helper scripts.

AC-002: Given package tests, when run, then active Clean Workroot behavior is covered through `ai_workroot.*` imports.

AC-003: Given historical legacy tests, when archived, then they are non-runnable `.txt` files under `docs/history/public-seed/code-archive/`.

AC-004: Given root tracked Public Seed files, when release validation tests run, then they fail.

AC-005: Given ignored local `AGENTS.md`, `CLAUDE.md`, or `.idea/`, when validation runs, then it does not fail release surface checks.

## Test Plan

### Unit Tests

- Import-boundary checks.
- Docs/spec reading order checks.
- Release surface path classifier.

### Integration Tests

- Package state/context flows.
- Historical archive boundary checks.

### Manual Verification

- Run full unittest discovery.
- Run `git ls-files` audits.
- Run checkbot.

## Migration / Rollback

Move tests gradually. If a package test fails after migration, keep historical evidence in the archive and mark the package behavior gap instead of restoring runnable compatibility.

## Observability / Debugging

Test audit output lists package tests, smoke tests, negative tests, archived legacy tests, and any active tests still importing scripts.

## Task Breakdown

T1: Add test audit command
- Change: Add or document audit for test-like files and script imports.
- Files likely affected: `scripts/dev/validate-release.sh`, tests.
- Verification: audit output in checkbot.

T2: Archive legacy tests
- Change: Move retired script-importing tests to non-runnable history or replace them with package parity tests.
- Files likely affected: `docs/history/public-seed/code-archive/tests/`, existing tests.
- Verification: unittest discovery and archive boundary tests.

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
