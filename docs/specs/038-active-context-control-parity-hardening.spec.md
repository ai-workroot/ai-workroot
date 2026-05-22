# Spec: Active Context Control Parity Hardening

## Status

Draft

## Priority

P1

## Background

The active package Context Control path renders useful local context from ContextCandidates, FTS matches, relationship signals, and release decisions. The legacy Context Guide still contains richer continuity behavior, including current state, active task, checkpoints, handoffs, budget modes, and detailed traces. The active path must regain the minimum useful parity without recreating the old monolith.

## Goals

- Include compact Workroot, active task, checkpoint, and handoff context when present.
- Keep ContextRecallHint / Context Card selection active and release-aware.
- Make `fast`, `standard`, `quality`, and `deep` modes behaviorally distinct.
- Persist richer ContextTrace evidence.
- Preserve hard token limit behavior.

## Non-goals

- Do not copy the legacy Context Guide implementation wholesale.
- Do not introduce remote LLM, remote embedding, or vector retrieval.
- Do not expose archived/deep history unless explicitly requested and release policy allows it.
- Do not make this a broad CLI redesign.

## Scope

### Included

- Active `src/ai_workroot/runtime/context.py`.
- Active SQLite tables for tasks, checkpoints, handoffs, candidates, traces, and release filters.
- Context mode budget and selection behavior.
- Tests proving active path parity.

### Excluded

- Archived legacy Context Guide refactoring.
- MCP integration.
- Full cross-Workroot retrieval.

## Dependencies

- `032-part2-capability-parity-small-specs.spec.md`
- `037-release-derived-index-safety-hardening.spec.md`
- `src/ai_workroot/runtime/context.py`
- `src/ai_workroot/runtime/work.py`
- `src/ai_workroot/indexing/providers/context_recall_hint_provider.py`

## Requirements

### Functional Requirements

FR-001: Active Context Control must include a compact Workroot section.

FR-002: Active Context Control must include active task title/status/kind when an active task exists.

FR-003: Active Context Control must include the latest relevant checkpoint for the active task when present.

FR-004: Active Context Control must include the latest relevant handoff when present.

FR-005: `fast` mode must use a smaller candidate and FTS budget than `standard`.

FR-006: `quality` mode must consider more candidates or ContextRecallHints than `standard` and must trace the behavior.

FR-007: `deep` mode must remain explicit-only in CLI/runtime behavior.

FR-008: All modes must respect deleted/redacted/safety-sensitive release protection.

FR-009: ContextTrace must record request, effective mode, budget, selected candidates, selected hints, FTS matches, relationship signals, release drops, fallback behavior, trim decisions, confidence, and token usage.

### Non-functional Requirements

NFR-001: Context generation must remain local-first and explainable.

NFR-002: Hot path behavior must remain bounded by configured limits.

NFR-003: The rendered package must stay concise and token-budget aware.

## Proposed Design

### Concepts

Continuity summary:
Small structured context from active task, latest checkpoint, and latest handoff.

Mode plan:
The resolved local retrieval plan for the requested mode.

### Data Model

Use existing tables:

```text
tasks
work_checkpoints
handoffs
context_recall_hints
context_candidates
context_traces
budget_trim_decisions
```

No new table is required for this Spec.

### File Layout

Likely changed files:

```text
src/ai_workroot/runtime/context.py
tests/integration/test_indexing_context_control.py
tests/e2e/longrun.py
docs/specs/010-context-control.spec.md
```

### CLI / API

Use existing command:

```bash
workroot context --agent codex --cwd <dir> --mode fast|standard|quality|deep
```

If `deep` is requested through CLI, it is explicit by definition. Runtime trace records `deepExplicitlyRequested=true`.

### Runtime Behavior

1. Resolve mode plan.
2. Load continuity summary.
3. Materialize/query ContextRecallHints according to mode limits.
4. Query candidates/FTS/relationships according to mode limits.
5. Apply release filters.
6. Render compact package sections.
7. Persist trace details.

### Error Handling

- Missing continuity rows are omitted, not errors.
- Malformed optional continuity data becomes debug trace notes.
- Invalid token budgets remain CLI/runtime errors.

### Security / Privacy

- Continuity rows are subject to release evaluation when they map to canonical targets.
- Redacted/deleted content must not be rendered through continuity sections.

### Compatibility

- Legacy Context Guide remains callable as compatibility.
- Active context output keeps existing metadata lines.

## Acceptance Criteria

AC-001:
Given an active task, checkpoint, and handoff
When active Context Control runs
Then the rendered package includes compact current task and continuity sections.

AC-002:
Given enough candidates
When `fast` and `standard` run on the same Workroot
Then `fast` selects fewer or equal context items.

AC-003:
Given extra ContextRecallHints
When `quality` mode runs
Then it considers more local recall material than `standard` and traces that behavior.

AC-004:
Given `deep` mode is requested
When Context Control runs
Then trace records that deep mode was explicitly requested.

AC-005:
Given a redacted continuity target
When Context Control runs
Then protected text is not rendered.

## Test Plan

### Unit Tests

- Mode plan resolution.
- Continuity section rendering helpers.

### Integration Tests

- Active task/checkpoint/handoff inclusion.
- Fast vs standard vs quality selection behavior.
- Deep explicit trace.
- Release-aware continuity filtering.

### Manual Verification

- Run `workroot context --debug` against a temp Workroot with seeded tasks, hints, and handoffs.

## Migration / Rollback

No schema migration required. Rollback is a normal Git revert.

## Observability / Debugging

ContextTrace debug JSON includes mode plan, continuity source rows, selected/dropped context, release decisions, fallback behavior, and trim decisions.

## Task Breakdown

T1: Add active continuity inclusion tests
- Change: Seed active task/checkpoint/handoff and assert rendered active context includes compact sections.
- Files likely affected: `tests/integration/test_indexing_context_control.py`
- Verification: Test fails before implementation.

T2: Implement continuity loading and rendering
- Change: Add small helpers in `runtime/context.py`.
- Files likely affected: `src/ai_workroot/runtime/context.py`
- Verification: Continuity test passes.

T3: Add mode behavior tests
- Change: Test fast/standard/quality/deep active path behavior.
- Files likely affected: `tests/integration/test_indexing_context_control.py`
- Verification: Tests fail before implementation.

T4: Implement mode plans
- Change: Add bounded mode-specific candidate, FTS, hint, and relationship limits.
- Files likely affected: `src/ai_workroot/runtime/context.py`
- Verification: Mode tests pass.

T5: Enrich trace payload
- Change: Persist continuity, mode plan, fallback, and selected source metadata.
- Files likely affected: `src/ai_workroot/runtime/context.py`
- Verification: Trace assertions pass.

## Risks

- Adding too much continuity can bloat context packages.
- Mode behavior can become arbitrary if not kept simple.
- Deep mode must not become an accidental bypass for release protection.

## Open Questions

None.
