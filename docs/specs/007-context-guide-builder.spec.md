# Spec: Context Guide Builder

## Status

Draft

## Priority

P0

## Background

Context Guide is the central runtime feature of AI Workroot 0.9.529. It must generate a small, relevant, safe, explainable Context Package for an agent in under 1 second on the hot path without remote calls, full user directory scans, full index rebuilds, deep graph traversal, or vector database dependency.

## Goals

- Generate an agent-ready Context Package from local managed state.
- Meet the hot path performance target.
- Use Materialized Context Candidates, FTS, graph one-hop signals, current state, and active task state.
- Produce explainable selection through debug trace.
- Keep user directory writes out of context generation.

## Non-goals

- Context Guide does not call remote LLMs or embedding APIs in P0.
- Context Guide does not require vector search in P0.
- Context Guide does not perform heavy maintenance on the hot path.
- Context Guide does not replace source-of-truth files.

## Scope

### Included

- Context Package generation.
- Inputs, challengers, scoring, filtering, token budget, and output structure.
- Relationship to Materialized Context Candidates, FTS, graph signals, and debug traces.
- Agent-specific output support.

### Excluded

- Candidate lifecycle details, covered by `008-materialized-context-candidates.spec.md`.
- FTS indexing details, covered by `009-fts-indexing-and-retrieval.spec.md`.
- Debug trace schema details, covered by `010-debug-trace-and-observability.spec.md`.
- SQLite and graph storage details, covered by `013-sqlite-cache-and-provenance-graph.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `006-doctor-command.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`

## Requirements

### Functional Requirements

FR-001: `workroot context --agent <agent> --cwd <path>` must resolve the current Workroot.

FR-002: Context Guide must load current state and active task when available.

FR-003: Context Guide must query active Materialized Context Candidates.

FR-004: Context Guide must query local FTS when a query or current task text is available.

FR-005: Context Guide must use graph one-hop signals only by default.

FR-006: Context Guide must filter unsafe, stale, superseded, archived, and gravestone candidates.

FR-007: Context Guide must score and rank candidates with explainable reasons.

FR-008: Context Guide must apply a default target token budget of 4000 tokens and a hard budget of 6000 tokens.

FR-009: Context Guide must produce a Markdown Context Package.

FR-010: Context Guide must write Context Package and debug trace to managed state only.

FR-011: Context Guide must support `--debug`.

FR-012: Context Guide must not call remote services on the hot path.

### Non-functional Requirements

NFR-001: Hot path P50 latency target is under 300 ms on a healthy small Workroot.

NFR-002: Hot path P95 latency target is under 1000 ms on a healthy small Workroot.

NFR-003: Context generation must work offline.

NFR-004: Context generation must avoid full user directory scans.

NFR-005: Context output must be deterministic enough for testing with stable fixtures.

## Proposed Design

### Concepts

- Context Package: Markdown payload returned to an agent.
- Challenger: A retrieval channel that proposes candidates.
- Candidate: A small rebuildable record that may enter context.
- Graph signal: A compact relationship summary derived from one-hop graph edges.
- Token budget: Approximate budget that bounds output.

### Data Model

Context generation request:

```json
{
  "agent": "codex",
  "cwd": "/path/to/user/directory",
  "query": null,
  "debug": false,
  "targetTokenBudget": 4000,
  "hardTokenBudget": 6000
}
```

Context selection item:

```json
{
  "candidateId": "cand_decision_clean_mode",
  "sourceType": "decision",
  "title": "Clean Mode keeps managed state outside user directory",
  "score": 0.94,
  "reasons": ["required-rule", "active-task-domain"],
  "tokenEstimate": 120
}
```

### File Layout

Managed output:

```text
<stateDirectory>/context/
  guide.md
  packages/
    latest.md
    history/
  debug/
    latest.json
    history/
```

No Context Guide output is written to the user directory by default.

### CLI / API

Required CLI:

```bash
workroot context --agent codex --cwd .
workroot context --agent claude --cwd .
workroot context --agent codex --cwd . --debug
```

Output defaults to Markdown Context Package on stdout. With `--debug`, stdout may include package plus trace path or support `--format json` in a later implementation.

### Runtime Behavior

Selection flow:

1. Resolve Workroot.
2. Load runtime hints and token budgets.
3. Load current state.
4. Load active task.
5. Query context candidates.
6. Query FTS.
7. Query graph one-hop signals.
8. Merge and deduplicate candidates.
9. Filter candidates by lifecycle and safety policy.
10. Score candidates.
11. Apply token budget by priority.
12. Build Markdown Context Package.
13. Write package and debug trace to managed state.

Priority order:

```text
current state
active task
required rules
relevant decisions
relevant knowledge
asset summaries
graph signals
```

### Error Handling

- If Workroot cannot be resolved, return an actionable init/bootstrap message.
- If managed state is missing, ask user to run doctor.
- If SQLite is unavailable, fall back to minimal file-based state only when safe and trace the fallback.
- If Context Package exceeds hard budget, drop lower-priority candidates and trace the drops.
- If debug trace cannot be written, return the package and warn.

### Security / Privacy

Context Guide uses local managed state only. It must not include secrets, logs, or private debug snippets unless they are explicitly marked safe for context. It must respect `never-auto`, gravestone, released, and safety policies.

### Compatibility

If 0.9.529 state is missing candidate tables, Context Guide should fail with migration guidance rather than performing a full rebuild on the hot path.

## Acceptance Criteria

AC-001:
Given a healthy Workroot
When `workroot context --agent codex --cwd .` runs
Then it returns a Markdown Context Package.

AC-002:
Given active context candidates and FTS matches
When Context Guide runs
Then selected items appear in priority order within the token budget.

AC-003:
Given stale or superseded candidates
When Context Guide runs
Then those candidates are filtered and recorded in the debug trace.

AC-004:
Given no network access
When Context Guide runs
Then it completes without remote calls.

AC-005:
Given debug mode
When Context Guide runs
Then a debug trace records challengers, counts, selected candidates, dropped candidates, reasons, and timings.

## Test Plan

### Unit Tests

- Test candidate merge and deduplication.
- Test lifecycle and safety filters.
- Test scoring reasons.
- Test token budget trimming.
- Test Markdown package rendering.

### Integration Tests

- Generate context from a fixture Workroot with candidates, FTS, and graph signals.
- Run with SQLite unavailable and assert safe fallback or actionable failure.
- Run `--debug` and validate trace fields.
- Measure fixture hot path latency budget in a non-flaky way.

### Manual Verification

- Run context command from a registered user directory.
- Review output for agent usefulness and absence of internal noise.
- Confirm no files were written to the user directory.

## Migration / Rollback

Context Guide relies on migrations for required tables and layout. Rollback of generated context packages means deleting managed `context/packages/latest.md` and regenerating. Source state is not changed by Context Guide.

## Observability / Debugging

Debug trace must include:

- Workroot resolution;
- active task;
- challengers executed;
- candidate counts;
- selected candidates;
- filtered candidates and reasons;
- score details;
- FTS matches;
- graph edges used;
- token budget usage;
- latency breakdown;
- fallbacks.

## Task Breakdown

T1: Add context request and package models
- Change: Define request, candidate selection, and package structures.
- Files likely affected: context module, tests.
- Verification: Unit tests for serialization and rendering.

T2: Add Workroot resolution and state loading
- Change: Resolve current Workroot and load current state and active task.
- Files likely affected: context module, state module.
- Verification: Integration test resolves from cwd.

T3: Add challengers
- Change: Implement state, task, rule, decision, asset, domain, FTS, graph, time, and safety challengers.
- Files likely affected: context module, retrieval module.
- Verification: Unit tests for each challenger with fixtures.

T4: Add scoring and budgeting
- Change: Merge, filter, score, and trim candidates.
- Files likely affected: context module.
- Verification: Unit tests for deterministic selected output.

T5: Add CLI command
- Change: Wire `workroot context` and `--debug`.
- Files likely affected: CLI module.
- Verification: CLI integration test returns package and trace.

## Risks

- Context generation can become slow if it performs maintenance or scans.
- Token estimates can be imprecise.
- Debug traces can leak too much source content if not bounded.
- Scoring can become hard to explain if too many signals are added early.

## Open Questions

None.
