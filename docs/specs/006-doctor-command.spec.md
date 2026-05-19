# Spec: Doctor Command

## Status

Draft

## Priority

P0

## Background

AI Workroot needs an actionable verification command for Clean Mode, managed state, bootstrap state, migrations, SQLite, indexes, context candidates, and Context Guide output. Doctor is the main safety check before runtime use and release.

## Goals

- Verify Clean Mode boundaries.
- Verify managed state layout and schema versions.
- Verify bootstrap and migration readiness.
- Verify index, SQLite, Context Guide, and debug-trace health.
- Verify Context Guide runtime hints, mode defaults, and budget configuration.
- Provide actionable diagnostics without requiring ordinary users to inspect internals.

## Non-goals

- Doctor does not perform heavy maintenance by default.
- Doctor does not silently repair files unless an explicit repair option is added.
- Doctor does not call remote services.
- Doctor does not prove semantic correctness of all knowledge.

## Scope

### Included

- `workroot doctor` command behavior.
- Validation categories and output severity.
- Clean Mode, managed state, bootstrap, migration, SQLite, Context Guide, and index checks.
- Developer diagnostics for debug traces.

### Excluded

- Release policy, covered by `014-release-and-test-gates.spec.md`.
- Migration application logic, covered by `005-migrations.spec.md`.
- Context selection logic, covered by `007-context-guide-builder.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `002-clean-mode-installation.spec.md`
- `003-managed-state-layout.spec.md`
- `004-bootstrap-process.spec.md`
- `005-migrations.spec.md`
- `007-context-guide-builder.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: `workroot doctor` must detect whether the current directory resolves to a registered Workroot.

FR-002: Doctor must verify that Clean Mode managed state is outside the user directory.

FR-003: Doctor must detect forbidden managed-state folders or files inside the user directory.

FR-004: Doctor must verify global config and registry files.

FR-005: Doctor must verify per-Workroot `workroot.json`.

FR-006: Doctor must verify migration status.

FR-007: Doctor must verify SQLite database existence and required tables.

FR-008: Doctor must verify graph tables.

FR-009: Doctor must verify `context_candidates` and FTS tables.

FR-010: Doctor must verify Context Guide can generate a minimal package without remote calls.

FR-011: Doctor must verify debug trace storage and retention configuration.

FR-012: Doctor must emit actionable diagnostics with severity levels.

FR-013: Doctor must verify Context Guide runtime hints are readable when present and compatible with built-in defaults when absent.

FR-014: Doctor must verify Standard Mode remains the default unless explicitly configured otherwise.

FR-015: Doctor must verify Deep Mode requires explicit request.

FR-016: Doctor must verify agent-specific budgets exist for Codex, Claude, and default agents when runtime hints are present.

### Non-functional Requirements

NFR-001: Doctor must work offline.

NFR-002: Default doctor must be non-mutating.

NFR-003: Doctor output must be understandable in text and machine-readable JSON.

NFR-004: Doctor must complete quickly on healthy small Workroots.

NFR-005: Doctor must avoid reading full user directory contents unless a specific check requires limited inspection.

## Proposed Design

### Concepts

- Check: One validation rule with ID, status, severity, message, and suggested action.
- Severity: `info`, `warning`, `error`.
- Category: `resolution`, `clean-mode`, `managed-state`, `bootstrap`, `migration`, `sqlite`, `context`, `debug`, `native-agent-entry`.
- Non-mutating default: Doctor reports issues but does not repair them.

### Data Model

Doctor result:

```json
{
  "status": "pass",
  "workrootId": "wr_example",
  "checks": [
    {
      "id": "clean-mode-state-outside-user-dir",
      "category": "clean-mode",
      "severity": "error",
      "status": "pass",
      "message": "Managed state is outside the user directory.",
      "suggestedAction": null
    }
  ],
  "startedAt": "2026-05-19T00:00:00Z",
  "completedAt": "2026-05-19T00:00:01Z"
}
```

### File Layout

Doctor reads:

```text
<AI_WORKROOT_HOME>/config.json
<AI_WORKROOT_HOME>/registry/
<AI_WORKROOT_HOME>/workroots/<workrootId>/workroot.json
<AI_WORKROOT_HOME>/workroots/<workrootId>/cache/workroot.sqlite
<AI_WORKROOT_HOME>/workroots/<workrootId>/context/
```

Doctor must not create files in the user directory.

### CLI / API

Required CLI:

```bash
workroot doctor
workroot doctor --format json
workroot doctor --workroot <workrootId>
```

Potential future repair:

```bash
workroot doctor --fix
```

`--fix` is out of scope for P0 unless explicitly approved during implementation.

### Runtime Behavior

Doctor flow:

1. Resolve AI Workroot home.
2. Resolve current Workroot from cwd or explicit ID.
3. Run checks by category.
4. Summarize pass/warn/fail.
5. Return non-zero exit code if error checks fail.
6. Print suggested actions for each failed check.

### Error Handling

- If no Workroot resolves, report init or bootstrap instructions.
- If managed state is missing, report the expected path.
- If SQLite is malformed, report cache rebuild or migration instructions.
- If migration status is failed, report migration ID and recovery action.
- If Context Guide generation fails, report the stage and debug trace path when available.
- If runtime hints are malformed, report the managed-state path and suggest removing or repairing the file.

### Security / Privacy

Doctor must not print file contents by default. JSON output may include local paths because it is a local developer diagnostic command. It must not print secrets or full debug snippets unless a future explicit verbose flag is approved.

### Compatibility

Doctor should distinguish current 0.9.529 Clean Mode Workroots from legacy public-seed Workroots and explain required migration or bootstrap steps.

## Acceptance Criteria

AC-001:
Given a healthy Clean Mode Workroot
When `workroot doctor` runs
Then it exits successfully and reports Clean Mode, state, SQLite, and Context Guide checks as passing.

AC-002:
Given managed state inside the user directory
When doctor runs
Then it reports a Clean Mode error and exits non-zero.

AC-003:
Given missing graph tables
When doctor runs
Then it reports a SQLite schema error with a migration or rebuild suggestion.

AC-004:
Given pending required migrations
When doctor runs
Then it reports migration status and the command needed to apply migrations.

AC-005:
Given `--format json`
When doctor runs
Then it emits valid JSON with check IDs, categories, severities, statuses, and suggested actions.

AC-006:
Given malformed `runtime-hints.json`
When doctor runs
Then it reports a Context Guide configuration error with an actionable repair suggestion.

AC-007:
Given no `runtime-hints.json`
When doctor runs
Then it reports that built-in defaults will be used rather than failing.

## Test Plan

### Unit Tests

- Test check result data model.
- Test severity summary and exit code rules.
- Test Clean Mode boundary check.
- Test missing SQLite table check.
- Test JSON output formatting.
- Test runtime hints validation.

### Integration Tests

- Run doctor after `workroot init`.
- Run doctor after `workroot bootstrap-dev`.
- Corrupt or remove required state in a fixture and assert diagnostics.
- Run doctor on a legacy public-seed layout and assert migration guidance.
- Run doctor with missing and malformed runtime hints.

### Manual Verification

- Run doctor in a healthy local Workroot.
- Run doctor from a non-Workroot directory.
- Review text output for ordinary-user clarity.

## Migration / Rollback

Doctor itself does not migrate or rollback state in P0. It reports migration and rollback instructions from `005-migrations.spec.md`.

## Observability / Debugging

Doctor output is part of observability. It should include:

- check timings;
- category summaries;
- failed check details;
- suggested actions;
- optional JSON output for developer tooling.
- runtime hints readability and context mode defaults.

## Task Breakdown

T1: Add doctor result model
- Change: Define check IDs, severities, categories, and output serialization.
- Files likely affected: doctor module, tests.
- Verification: Unit tests validate result JSON.

T2: Add resolution and Clean Mode checks
- Change: Verify Workroot binding and state boundary.
- Files likely affected: doctor module.
- Verification: Integration test catches state inside user directory.

T3: Add state and migration checks
- Change: Validate config, workroot metadata, and migration status.
- Files likely affected: doctor module, migration module.
- Verification: Fixture tests for missing and failed migrations.

T4: Add SQLite and context checks
- Change: Validate required SQLite tables, runtime hints, mode defaults, and minimal Context Guide generation.
- Files likely affected: doctor module, SQLite module, context module.
- Verification: Integration test checks healthy initialized Workroot.

T5: Add output formats
- Change: Support text and JSON output.
- Files likely affected: CLI module.
- Verification: CLI tests for both formats.

## Risks

- Doctor can become slow if it performs deep scans.
- Too much diagnostic detail can expose private path or content data.
- Repair behavior may be tempting but should remain explicit.

## Open Questions

None.
