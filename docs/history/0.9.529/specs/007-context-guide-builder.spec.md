# Spec: Context Guide Builder

## Status

Draft

## Priority

P0

## Background

Context Guide is the central runtime feature of AI Workroot 0.9.529. It must generate a small, relevant, safe, explainable Context Package for an agent while treating 1 second as the normal hot-path target, not an absolute correctness limit. Accuracy has priority over strict latency: Standard Mode is fast by default, Quality Mode may use a bounded local 2-3 second soft limit when confidence is insufficient, and Deep Mode requires an explicit request.

## Goals

- Generate an agent-ready Context Package from local managed state.
- Meet the configured hot-path performance target without sacrificing critical context accuracy.
- Use Materialized Context Candidates, FTS, graph one-hop signals, current state, and active task state.
- Produce explainable selection through debug trace.
- Keep user directory writes out of context generation.
- Include mode, confidence, latency, token usage, and fallback metadata in every Context Package.

## Non-goals

- Context Guide does not call remote LLMs or embedding APIs in P0.
- Context Guide does not require vector search in P0.
- Context Guide does not perform heavy maintenance on the hot path.
- Context Guide does not replace source-of-truth files.
- Context Guide does not silently enter Deep Mode.
- Context Guide does not treat a low-confidence sub-second package as better than a bounded, more accurate local Quality package.

## Scope

### Included

- Context Package generation.
- Inputs, challengers, scoring, filtering, token budget, and output structure.
- Relationship to Materialized Context Candidates, FTS, graph signals, and debug traces.
- Agent-specific output support.
- Integration with mode-aware configuration, confidence, and token budgets.

### Excluded

- Candidate lifecycle details, covered by `008-materialized-context-candidates.spec.md`.
- FTS indexing details, covered by `009-fts-indexing-and-retrieval.spec.md`.
- Debug trace schema details, covered by `010-debug-trace-and-observability.spec.md`.
- SQLite and graph storage details, covered by `013-sqlite-cache-and-provenance-graph.spec.md`.
- Mode, budget, and confidence policy details, covered by `015-context-guide-modes-budgets-and-confidence.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `006-doctor-command.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`
- `015-context-guide-modes-budgets-and-confidence.spec.md`

## Requirements

### Functional Requirements

FR-001: `workroot context --agent <agent> --cwd <path>` must resolve the current Workroot.

FR-002: Context Guide must load current state and active task when available.

FR-003: Context Guide must query active Materialized Context Candidates.

FR-004: Context Guide must query local FTS when a query or current task text is available.

FR-005: Context Guide must use graph one-hop signals only by default.

FR-006: Context Guide must filter unsafe, stale, superseded, archived, and gravestone candidates.

FR-007: Context Guide must score and rank candidates with explainable reasons.

FR-008: Context Guide must resolve target and hard token budgets from runtime hints or built-in defaults, with a conservative Codex default target around 4000 tokens and hard limit no greater than 6000 tokens.

FR-009: Context Guide must produce a Markdown Context Package.

FR-010: Context Guide must write Context Package and debug trace to managed state only.

FR-011: Context Guide must support `--debug`.

FR-012: Context Guide must not call remote services on the hot path.

FR-013: Context Guide must support `fast`, `standard`, `quality`, and explicit `deep` mode semantics from `015-context-guide-modes-budgets-and-confidence.spec.md`.

FR-014: Context Guide must include a Context Metadata section with mode, confidence, latency, token usage, fallback status, and low-confidence reasons when applicable.

FR-015: Context Guide must compute package confidence as `high`, `medium`, or `low`.

FR-016: Context Guide may escalate from Standard Mode to Quality Mode only for local confidence reasons and within the configured Quality soft latency budget.

FR-017: Context Guide must not use Deep Mode unless `--deep` is explicitly requested.

### Non-functional Requirements

NFR-001: Hot path P50 latency target is under 300 ms on a healthy small Workroot.

NFR-002: Standard Mode hot path P95 latency target is under 1000 ms on a healthy small Workroot, with a configurable soft limit up to 2000 ms when needed for local accuracy.

NFR-003: Context generation must work offline.

NFR-004: Context generation must avoid full user directory scans.

NFR-005: Context output must be deterministic enough for testing with stable fixtures.

NFR-006: Quality Mode should use a 2-3 second configurable soft limit and return the best current package if the soft limit is exceeded.

## Proposed Design

### Concepts

- Context Package: Markdown payload returned to an agent.
- Challenger: A retrieval channel that proposes candidates.
- Candidate: A small rebuildable record that may enter context.
- Graph signal: A compact relationship summary derived from one-hop graph edges.
- Token budget: Approximate budget that bounds output.
- Context mode: `fast`, `standard`, `quality`, or explicit `deep` profile controlling retrieval depth and budget.
- Context confidence: Package-level `high`, `medium`, or `low` signal explaining whether the current context is sufficient for major changes.

### Data Model

Context generation request:

```json
{
  "agent": "codex",
  "cwd": "/path/to/user/directory",
  "query": null,
  "debug": false,
  "mode": "standard",
  "deep": false,
  "targetTokenBudget": 4000,
  "hardTokenBudget": 6000,
  "maxLatencyMs": 2000
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

Context package metadata:

```json
{
  "mode": "standard",
  "confidence": "medium",
  "latencyMs": 842,
  "targetTokens": 4000,
  "hardTokenLimit": 6000,
  "usedTokens": 3820,
  "fallbackUsed": false,
  "confidenceReasons": [
    "active task resolved",
    "some related asset summaries are stale"
  ]
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
<stateDirectory>/state/
  runtime-hints.json
```

No Context Guide output is written to the user directory by default.

### CLI / API

Required CLI:

```bash
workroot context --agent codex --cwd .
workroot context --agent claude --cwd .
workroot context --agent codex --cwd . --debug
workroot context --agent codex --cwd . --mode fast
workroot context --agent codex --cwd . --mode standard
workroot context --agent codex --cwd . --mode quality
workroot context --agent codex --cwd . --deep
workroot context --agent codex --cwd . --target-tokens 4000
workroot context --agent codex --cwd . --max-latency-ms 3000
```

Output defaults to Markdown Context Package on stdout. With `--debug`, stdout may include package plus trace path or support `--format json` in a later implementation.

### Runtime Behavior

Selection flow:

1. Resolve Workroot.
2. Load runtime hints, requested mode, agent budget, and latency policy.
3. Load current state.
4. Load active task.
5. Query context candidates.
6. Query FTS.
7. Query graph one-hop signals.
8. Merge and deduplicate candidates.
9. Filter candidates by lifecycle and safety policy.
10. Score candidates.
11. Compute confidence.
12. If Standard Mode confidence is insufficient, optionally run bounded local Quality expansion.
13. Apply token budget by priority.
14. Build Markdown Context Package with metadata.
15. Write package and debug trace to managed state.

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

Quality escalation reasons:

```text
active task unclear
candidate count too low
candidate confidence low
important source summaries stale
FTS results sparse or noisy
graph indicates superseded or conflicting knowledge
architecture-heavy or review-heavy task
question asks why, source, relationship, architecture, or tradeoff
```

### Error Handling

- If Workroot cannot be resolved, return an actionable init/bootstrap message.
- If managed state is missing, ask user to run doctor.
- If SQLite is unavailable, fall back to minimal file-based state only when safe and trace the fallback.
- If Context Package exceeds hard budget, drop lower-priority candidates and trace the drops.
- If debug trace cannot be written, return the package and warn.
- If runtime hints are malformed, use built-in defaults and trace the configuration fallback.
- If Quality Mode exceeds the soft latency limit, return the best current package, mark confidence `medium` or `low`, and suggest explicit Deep Mode.
- If Deep Mode is requested but not fully implemented, report explicit reserved-mode behavior rather than silently substituting Standard Mode.

### Security / Privacy

Context Guide uses local managed state only. It must not include secrets, logs, or private debug snippets unless they are explicitly marked safe for context. It must respect `never-auto`, gravestone, released, and safety policies.

### Compatibility

If 0.9.529 state is missing candidate tables, Context Guide should fail with migration guidance rather than performing a full rebuild on the hot path.

## Acceptance Criteria

AC-001:
Given a healthy Workroot
When `workroot context --agent codex --cwd .` runs
Then it returns a Markdown Context Package with Context Metadata.

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

AC-006:
Given a Standard Mode context run
When runtime hints are available
Then Context Guide uses configured latency and token budgets rather than scattered hardcoded limits.

AC-007:
Given low-confidence Standard Mode results
When Quality escalation runs within the configured soft limit
Then the package and trace show Quality Mode and the mode switch reason.

AC-008:
Given no explicit `--deep`
When Context Guide runs during normal agent startup
Then Deep Mode is not used.

## Test Plan

### Unit Tests

- Test candidate merge and deduplication.
- Test lifecycle and safety filters.
- Test scoring reasons.
- Test token budget trimming.
- Test Markdown package rendering.
- Test context metadata rendering.
- Test confidence calculation.
- Test mode and budget resolution.

### Integration Tests

- Generate context from a fixture Workroot with candidates, FTS, and graph signals.
- Run with SQLite unavailable and assert safe fallback or actionable failure.
- Run `--debug` and validate trace fields.
- Measure fixture hot path latency budget in a non-flaky way.
- Run `--mode quality` and verify mode metadata.
- Run `--deep` and verify explicit Deep handling.

### Manual Verification

- Run context command from a registered user directory.
- Review output for agent usefulness and absence of internal noise.
- Confirm no files were written to the user directory.
- Confirm package confidence guidance is understandable for agents.

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
- context mode and mode switch reason;
- confidence and confidence reasons;
- fallbacks.

## Task Breakdown

T1: Add context request and package models
- Change: Define request, mode, budget, confidence, candidate selection, and package structures.
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
- Change: Merge, filter, score, compute confidence, resolve mode budgets, and trim candidates.
- Files likely affected: context module.
- Verification: Unit tests for deterministic selected output.

T5: Add CLI command
- Change: Wire `workroot context`, `--debug`, `--mode`, `--deep`, `--target-tokens`, and `--max-latency-ms`.
- Files likely affected: CLI module.
- Verification: CLI integration test returns package and trace.

T6: Add Quality escalation guardrails
- Change: Add bounded local Quality escalation and explicit Deep-mode handling.
- Files likely affected: context arbiter, debug trace module.
- Verification: Integration tests for low-confidence escalation and no silent Deep Mode.

## Risks

- Context generation can become slow if it performs maintenance or scans.
- Token estimates can be imprecise.
- Debug traces can leak too much source content if not bounded.
- Scoring can become hard to explain if too many signals are added early.

## Open Questions

None.
