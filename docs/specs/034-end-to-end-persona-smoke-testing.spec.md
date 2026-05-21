# Spec: End-to-End Persona Smoke Testing

## Status

Draft

## Priority

P1

## Background

AI Workroot needs repeatable end-to-end validation that exercises Clean Workroot behavior across realistic personal roles. Unit and integration tests catch module regressions, but they do not prove that multiple Workroots, user assets, managed state, Context Control, Relationship Network, Release Control, and Native Agent Entry work together under CLI usage.

## Goals

- Provide reusable Level 2, Level 3, and Level 4 E2E harnesses.
- Validate five personal Workroot personas with different user directory contents.
- Verify Clean Mode does not write managed state into user directories.
- Stress context assembly, debug traces, hard token trimming, and release protection.
- Preserve report artifacts for client-side review.

## Non-goals

- Do not call remote LLMs, remote embeddings, or vector databases.
- Do not replace unit, integration, smoke, or negative tests.
- Do not simulate every possible human workflow in one test.
- Do not create durable state in the real user environment.

## Scope

### Included

- Level 2 five-persona smoke.
- Level 3 five-persona longrun with 30 tasks by default.
- Level 4 five-persona longrun with 40 tasks by default.
- Context audit reports, transcripts, command logs, and failure JSON.
- Safety checks for redacted/deleted content leakage and tombstone symbolic visibility.
- Hard-token debug trace preservation checks.

### Excluded

- Browser automation.
- Real Codex UI automation.
- Cloud-backed retrieval.
- Performance benchmarks beyond basic token/context counters.

## Dependencies

- `src/ai_workroot/cli/main.py`
- `src/ai_workroot/runtime/context.py`
- `src/ai_workroot/runtime/init.py`
- `src/ai_workroot/runtime/release.py`
- `src/ai_workroot/runtime/relationships.py`
- `src/ai_workroot/indexing/providers/`

## Requirements

### Functional Requirements

FR-001: The harness must create Workroots through the package CLI using temporary `AI_WORKROOT_HOME`.

FR-002: The harness must create five personas: software engineer, founder/operator, researcher, writer/creator, and nontechnical learner.

FR-003: Level 3 must run at least 30 tasks by default.

FR-004: Level 4 must run at least 40 tasks by default.

FR-005: The harness must write `summary.md`, `failures.json`, `context-audit.json`, `longrun-matrix.json`, `commands.json`, and transcripts.

FR-006: The harness must fail if redacted/deleted protected markers appear in ordinary context.

FR-007: The harness must allow tombstone symbolic markers when they are annotated rather than treated as current source truth.

FR-008: The harness must fail if debug context output loses candidate sources, filters, scoring, timing, token usage, or trim steps.

### Non-functional Requirements

NFR-001: Runs must be local-first and deterministic enough for regression use.

NFR-002: Runs must not mutate the real user environment.

NFR-003: The run root must reject unsafe paths such as the repository root, repository parent, current directory, or `/`.

NFR-004: Reports should be readable without inspecting SQLite directly.

## Proposed Design

### Concepts

- Persona: a representative personal Workroot user profile for testing.
- Scenario: a reusable task type that seeds Work, Asset, Release Control, Relationship Network, FTS, and Context Recall Hint data.
- Level 2: short smoke across personas.
- Level 3: 30-task longrun.
- Level 4: 40-task longrun with broader context pressure.

### Data Model

The harness seeds:

- `tasks`
- `agent_runs`
- `work_actions`
- `work_checkpoints`
- `handoffs`
- `assets`
- `context_recall_hints`
- `indexed_chunks`
- `relationship_nodes`
- `relationship_edges`
- `release_records`
- `redactions`
- `deletion_records`
- `tombstones`

### File Layout

Test harness files live under `tests/e2e/`.

Run artifacts live under caller-provided run roots outside the repository:

```text
<run-root>/
  ai-workroot-home/
  user-dirs/
  transcripts/
  reports/
```

The selected user directories may contain user assets and optional Native Agent Entry files only. Managed state must remain under `ai-workroot-home`.

### CLI / API

Programmatic API:

- `run_persona_smoke(run_root=...)`
- `run_longrun(run_root=..., level=3|4, tasks_per_persona=...)`

CLI:

```bash
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite persona-smoke
AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite longrun
```

E2E suites are opt-in only. Default unit, integration, smoke, and release validation commands must not run E2E, longrun, or live-agent tests.

### Runtime Behavior

The harness initializes Workroots, seeds SQLite with realistic records, runs status/context/debug/doctor/list commands, writes transcripts, and renders a client report to stdout.

### Error Handling

Unsafe run roots raise `ValueError`. CLI command failures are recorded in `failures.json` and make the run fail.

### Security / Privacy

The harness uses synthetic data only. Redacted/deleted marker strings must not appear in ordinary context output.

### Compatibility

The harness uses Python unittest and package CLI commands. No additional dependency is required.

## Acceptance Criteria

AC-001:
Given a temporary run root
When Level 2 persona smoke runs
Then five Workroots are initialized and no managed state is written into user directories.

AC-002:
Given Level 3 longrun
When the harness completes
Then it reports 30 tasks, nonzero token usage, debug trace coverage, and no protected leaks.

AC-003:
Given Level 4 longrun
When hard token trimming occurs
Then debug trace fields remain visible.

AC-004:
Given a run root equal to the repository root
When the harness starts
Then it refuses to run.

## Test Plan

### Unit Tests

- Run-root safety helper coverage through E2E tests.

### Integration Tests

- `tests/e2e/persona_smoke_cases.py`
- `tests/e2e/longrun_cases.py`
- `tests/e2e/runner.py`

### Manual Verification

- Inspect `reports/summary.md`.
- Inspect `reports/context-audit.json`.
- Inspect transcripts for representative context packages.

## Migration / Rollback

Not applicable.

## Observability / Debugging

Each run writes command logs, context audit JSON, transcript markdown, and a client-facing summary.

## Task Breakdown

T1: Add reusable personas
- Change: Define five personas and user files.
- Files likely affected: `tests/e2e/personas.py`
- Verification: Persona smoke test.

T2: Add reusable scenarios
- Change: Define task scenarios for planning, debugging, decision, release control, large context, and weak query.
- Files likely affected: `tests/e2e/scenarios.py`
- Verification: Longrun tests.

T3: Add shared harness
- Change: Add CLI runner, env builder, user directory validation.
- Files likely affected: `tests/e2e/harness.py`
- Verification: Persona smoke test.

T4: Add Level 2 smoke
- Change: Implement five-persona smoke and report.
- Files likely affected: `tests/e2e/persona_smoke.py`, `tests/e2e/persona_smoke_cases.py`, `tests/e2e/runner.py`
- Verification: `AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite persona-smoke`

T5: Add Level 3/4 longrun
- Change: Implement longrun seeding, probes, audits, and CLI.
- Files likely affected: `tests/e2e/longrun.py`, `tests/e2e/longrun_cases.py`, `tests/e2e/runner.py`
- Verification: `AI_WORKROOT_RUN_E2E=1 python3 -m tests.e2e.runner --suite longrun`

## Risks

- Harness data may become too synthetic and miss real workflow gaps.
- Longrun runtime may grow as scenarios expand.
- Overly broad leak detection may confuse tombstone symbolic visibility with strict protected content.

## Open Questions

None.
