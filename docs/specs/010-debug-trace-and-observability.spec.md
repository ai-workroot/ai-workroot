# Spec: Debug Trace and Observability

## Status

Draft

## Priority

P0

## Background

Context generation and retrieval must be explainable. AI Workroot 0.9.529 needs debug traces that show how Context Guide resolved the Workroot, which mode and budget were used, which retrieval channels ran, what matched, what was selected, what was dropped, why confidence was assigned, whether mode escalation happened, and how long each step took.

## Goals

- Provide explainable Context Guide and retrieval traces.
- Store debug traces in managed state only.
- Keep recent traces bounded.
- Include timing, selected candidates, dropped candidates, scores, and reasons.
- Include Context Guide mode, confidence, token budget, mode switch reason, and fallback details.
- Support developer inspection without exposing excessive private content.

## Non-goals

- Debug trace is not a telemetry upload system.
- Debug trace does not call remote services.
- Debug trace does not replace doctor.
- Debug trace does not store full file contents by default.

## Scope

### Included

- Context debug trace schema.
- Retrieval trace requirements.
- Mode, confidence, and budget trace requirements.
- Doctor output relationship.
- Timing and candidate selection observability.
- Trace retention.
- Developer inspection commands or files.

### Excluded

- Context Guide scoring details, covered by `007-context-guide-builder.spec.md`.
- FTS indexing behavior, covered by `009-fts-indexing-and-retrieval.spec.md`.
- Release gates, covered by `014-release-and-test-gates.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `006-doctor-command.spec.md`
- `007-context-guide-builder.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: `workroot context --debug` must write a JSON debug trace.

FR-002: Debug trace must include Workroot resolution details.

FR-003: Debug trace must include active task and current state identifiers when available.

FR-004: Debug trace must list challengers executed and skipped.

FR-005: Debug trace must include candidate counts per challenger.

FR-006: Debug trace must include selected candidates and selection reasons.

FR-007: Debug trace must include dropped candidates and drop reasons.

FR-008: Debug trace must include FTS matches and scores when FTS runs.

FR-009: Debug trace must include graph edges used when graph signals run.

FR-010: Debug trace must include token budget usage.

FR-011: Debug trace must include latency breakdown.

FR-012: Debug trace retention must keep a bounded recent history, defaulting to the last 50 records.

FR-013: Debug trace must include requested mode, effective mode, and mode switch reason when applicable.

FR-014: Debug trace must include context confidence and confidence reasons.

FR-015: Debug trace must include target tokens, hard token limit, used token estimate, and budget source.

FR-016: Debug trace must include Quality soft-limit status when Quality Mode is used or attempted.

FR-017: Debug trace must indicate whether Deep Mode was explicitly requested.

FR-018: Debug trace must include fallback reasons for malformed runtime hints, missing indexes, missing candidate tables, sparse FTS, stale candidates, or trace write limitations.

### Non-functional Requirements

NFR-001: Debug trace creation must not push Context Guide over the P95 hot path target on healthy small Workroots.

NFR-002: Trace content must be bounded and avoid full source file bodies by default.

NFR-003: Trace files must remain local managed state.

NFR-004: Trace JSON must be stable enough for tests and developer tooling.

NFR-005: Observability must remain useful when a retrieval channel fails.

## Proposed Design

### Concepts

- Trace: JSON record for one context generation or retrieval run.
- Challenger event: Execution record for one retrieval channel.
- Candidate decision: Selected or dropped candidate with reason.
- Timing span: Named duration in milliseconds.

### Data Model

Debug trace:

```json
{
  "traceId": "trace_20260519_000001",
  "workrootId": "wr_example",
  "agent": "codex",
  "cwd": "/path/to/user/directory",
  "startedAt": "2026-05-19T00:00:00Z",
  "completedAt": "2026-05-19T00:00:00Z",
  "latencyMs": 128,
  "requestedMode": "standard",
  "contextMode": "standard",
  "modeSwitchReason": null,
  "confidence": "high",
  "confidenceReasons": [
    "active task resolved",
    "high-confidence required candidates available"
  ],
  "resolution": {
    "strategy": "nearest-registered-workroot",
    "matchedDirectory": "/path/to/user/directory"
  },
  "timing": {
    "resolveWorkroot": 8,
    "loadState": 11,
    "queryCandidates": 34,
    "fts": 20,
    "graphExpansion": 17,
    "scoring": 6,
    "packageBuild": 12
  },
  "challengers": [],
  "selectedCandidates": [],
  "droppedCandidates": [],
  "tokenBudget": {
    "target": 4000,
    "hard": 6000,
    "estimatedUsed": 2180,
    "source": "agent:codex"
  },
  "qualitySoftLimitMs": null,
  "deepExplicitlyRequested": false,
  "fallbacks": []
}
```

Dropped candidate:

```json
{
  "candidateId": "cand_old",
  "sourceType": "decision",
  "reason": "superseded",
  "scoreBeforeDrop": 0.72
}
```

### File Layout

Trace storage:

```text
<stateDirectory>/context/debug/
  latest.json
  history/
    trace_<timestamp>.json
```

Doctor output is not stored by default unless a future explicit report option is added.

### CLI / API

Required CLI:

```bash
workroot context --agent codex --cwd . --debug
```

P1 inspection command:

```bash
workroot trace latest
```

The P1 command is optional for first implementation if trace files are documented and doctor can point to them.

### Runtime Behavior

Trace flow:

1. Create trace builder at Context Guide start.
2. Record resolution.
3. Record each challenger start, result, skip, or failure.
4. Record candidate filtering and scoring.
5. Record confidence calculation and reasons.
6. Record token budgeting and budget source.
7. Record mode switch and Quality soft-limit status when applicable.
8. Record package write result.
9. Write `latest.json`.
10. Append/copy to `history/`.
11. Prune history beyond retention.

### Error Handling

- If trace write fails, Context Guide should still return context and warn.
- If a challenger fails, trace the failure and continue when safe.
- If trace pruning fails, warn but do not fail Context Guide.
- If trace JSON serialization fails, write a minimal failure trace.
- If a mode escalation attempt exceeds the soft limit, trace the partial result and fallback confidence.

### Security / Privacy

Trace snippets must be short and bounded. Trace must not include full file bodies, secrets, environment variables, credentials, or hidden system paths beyond local diagnostic paths. Trace stays under managed state and is never uploaded.

### Compatibility

Trace schema should include a `schemaVersion` field in implementation. Future trace schema changes must use migrations or versioned readers.

## Acceptance Criteria

AC-001:
Given `workroot context --debug`
When Context Guide runs
Then `context/debug/latest.json` is written under managed state.

AC-002:
Given FTS retrieval runs
When debug trace is inspected
Then query, matches, scores, and timing are present.

AC-003:
Given candidates are dropped
When debug trace is inspected
Then each dropped candidate includes a reason.

AC-004:
Given more than 50 traces exist
When a new trace is written
Then old history records are pruned according to retention policy.

AC-005:
Given a trace write failure
When Context Guide runs
Then context generation does not fail solely because the trace could not be stored.

AC-006:
Given Context Guide escalates from Standard to Quality
When debug trace is inspected
Then effective mode, mode switch reason, soft-limit status, and confidence reasons are present.

AC-007:
Given a Context Package is generated for Codex
When debug trace is inspected
Then token budget source, target, hard limit, and used token estimate are present.

AC-008:
Given Deep Mode is not requested
When debug trace is inspected
Then `deepExplicitlyRequested` is false and effective mode is not `deep`.

## Test Plan

### Unit Tests

- Test trace schema serialization.
- Test challenger event recording.
- Test selected and dropped candidate recording.
- Test retention pruning.
- Test trace write failure handling.
- Test mode and confidence trace fields.
- Test token budget source trace fields.

### Integration Tests

- Run Context Guide with debug and validate JSON trace.
- Run FTS challenger and validate FTS trace fields.
- Run graph challenger and validate graph edge trace fields.
- Simulate challenger failure and validate fallback trace.
- Run Quality Mode fixture and validate mode switch fields.
- Run Deep Mode request and validate explicit request field.

### Manual Verification

- Inspect `latest.json` after context generation.
- Confirm trace content is useful and bounded.
- Confirm user directory remains unchanged.

## Migration / Rollback

Initial migration creates debug directories under managed state. Rollback may delete generated trace history because it is diagnostic state, not canonical truth. Rollback must not delete context packages unless explicitly requested.

## Observability / Debugging

This Spec defines observability for context generation. Doctor should validate trace directory writability and may show the latest trace path when Context Guide fails.

Context debug trace should include:

- package mode and requested mode;
- mode switch reason;
- confidence and confidence reasons;
- target, hard, and used token budget;
- agent budget source;
- Quality soft-limit status;
- Deep explicit-request status;
- fallback reasons.

## Task Breakdown

T1: Add trace schema and writer
- Change: Implement trace builder and JSON writer with mode, confidence, budget, and fallback fields.
- Files likely affected: debug module, context module.
- Verification: Unit tests validate schema.

T2: Instrument Context Guide
- Change: Record resolution, challengers, selection, drops, token usage, confidence, mode switches, and timing.
- Files likely affected: context module.
- Verification: Integration test validates trace after context generation.

T3: Instrument retrieval channels
- Change: Record FTS and graph channel details.
- Files likely affected: retrieval module, graph module.
- Verification: Trace tests include retrieval details.

T4: Add retention pruning
- Change: Keep latest plus bounded history.
- Files likely affected: debug module.
- Verification: Unit test prunes beyond 50.

T5: Add doctor trace check
- Change: Verify trace directory health.
- Files likely affected: doctor module.
- Verification: Doctor fixture detects unwritable debug directory.

## Risks

- Trace files can grow too large if snippets are not bounded.
- Debug output can leak sensitive summaries if safety policy is not applied.
- Excessive instrumentation can slow Context Guide.

## Open Questions

None.
