# Spec 026: Retrieval, Indexing, and Context Control Migration

## Status

Draft

## Priority

P0

## Background

The mature 0.9.529 Context Guide and indexing behavior still exists largely in `scripts/workroot_context.py`, `scripts/workroot_indexing.py`, and `scripts/workroot_candidates.py`. Clean Workroot 0.9.530 must move this behavior into package Retrieval & Index Control and Context Control.

## Goals

- Make package indexing providers own FTS, chunks, candidate read models, and retrieval inputs.
- Make package Context Control own context package generation and trace persistence.
- Preserve explainable local-first retrieval.
- Ensure FTS/query/relationship signals affect selection.
- Keep vector retrieval optional and absent in 0.9.530.

## Non-goals

- Do not add vector database dependency.
- Do not call remote embedding or remote LLM services.
- Do not move deleted/redacted content into normal context packages.

## Scope

### Included

- File indexing and chunking.
- FTS search and fallback traces.
- Materialized Context Candidates.
- Candidate pool building and selection.
- Context package rendering, token budgets, debug trace, persistence.

### Excluded

- Full semantic/vector retrieval.
- Cloud sync.
- UI context browser.

## Dependencies

- Spec 009 Retrieval Index Control.
- Spec 010 Context Control.
- Spec 013 Storage SQLite Schema.
- Spec 027 Release, Relationship, and Safety Migration.

## Requirements

### Functional Requirements

FR-001: Package indexing must index supported text files into SQLite FTS.

FR-002: Package candidate provider must upsert/query context candidates with source flags and safety policies.

FR-003: Context Control must build candidate pools from required rules, explicit/query matches, FTS, relationship signals, and recent/high-importance candidates.

FR-004: FTS and relationship hits must affect candidate score or selection.

FR-005: Context output must include mode, confidence, latency, and token usage metadata.

FR-006: Debug output must include sources, filters, scores, drops, timing, token budget source, and hard-limit trim steps.

FR-007: FTS OperationalError must degrade gracefully and record debug fallback evidence.

### Non-functional Requirements

NFR-001: Token estimation must conservatively handle English, CJK, and code.

NFR-002: Context rendering must enforce hard token limit with final fallback.

NFR-003: Context Control must be local-first and deterministic.

## Proposed Design

### Concepts

Retrieval & Index Control builds explainable local signals. Context Control selects, filters, trims, renders, and persists a Context Package.

### Data Model

Derived tables:

```text
indexed_files
indexed_chunks
indexed_chunks_fts
context_candidates
context_candidates_fts
context_packages
context_traces
candidate_selections
budget_trim_decisions
```

### File Layout

```text
src/ai_workroot/indexing/fts.py
src/ai_workroot/indexing/candidates.py
src/ai_workroot/indexing/pipeline.py
src/ai_workroot/indexing/providers/sqlite_fts.py
src/ai_workroot/indexing/providers/candidate_provider.py
src/ai_workroot/runtime/context.py
src/ai_workroot/core/context.py
```

### CLI / API

Existing command remains:

```text
workroot context --agent codex --cwd <dir> --query <text> --mode standard --target-tokens 1200 --hard-token-limit 2400 --debug
```

### Runtime Behavior

Context runtime resolves Workroot, loads retrieval signals, applies safety/release filters, ranks candidates, renders package, enforces budget, persists trace, and returns Markdown.

### Error Handling

FTS errors degrade to candidate-only retrieval and appear in debug trace. Missing DB falls back to user asset discovery without writing into the user directory.

### Security / Privacy

Redacted/deleted content is removed before rendering. Safety-sensitive content requires explicit allowed paths or admin/debug/audit mode.

### Compatibility

Old script context tests are ported to package context tests. Legacy tests remain only for historical compatibility.

## Acceptance Criteria

AC-001: Given many always candidates and explicit/FTS/relationship matches, when context is built, then explicit/FTS/relationship candidates cannot be starved.

AC-002: Given an FTS match for a query, when context is built, then selected candidates or score reasons show FTS influence.

AC-003: Given a relationship edge related to selected sources, when context is built, then Relationship signals are relation-backed and affect selection.

AC-004: Given CJK and code-heavy content, when token budget is enforced, then token usage is nonzero and hard limit is respected.

AC-005: Given SQLite FTS raises OperationalError, when debug context is requested, then output records the FTS fallback error.

## Test Plan

### Unit Tests

- Token estimator for English, CJK, code, and mixed text.
- Candidate pool starvation prevention.
- Score reason merging.
- Hard-limit final fallback.

### Integration Tests

- Index file, query FTS, build context.
- Query candidate FTS, build context.
- Debug trace persistence.
- Package context output after bootstrap-dev.

### Manual Verification

- Run `workroot context` and `workroot context --debug` with temporary state.
- Inspect persisted context trace rows.

## Migration / Rollback

Port functions in small groups: indexing, candidate provider, budget/token, pool/scoring, rendering/trace. Keep old script context until parity tests pass. Rollback by routing package runtime back to prior provider implementation.

## Observability / Debugging

Debug trace must expose candidate sources, filtered reasons, scoring, FTS fallback errors, relationship signals, timing, token usage, and trim decisions.

## Task Breakdown

T1: Migrate indexing chunking
- Change: Move supported-file detection, hashing, chunking, and FTS insert behavior into package indexing modules.
- Files likely affected: `src/ai_workroot/indexing/fts.py`, `src/ai_workroot/indexing/pipeline.py`.
- Verification: package indexing tests.

T2: Migrate candidate provider parity
- Change: Port candidate FTS, safety filtering, source flags, and use-count updates.
- Files likely affected: `src/ai_workroot/indexing/candidates.py`, `src/ai_workroot/indexing/providers/candidate_provider.py`.
- Verification: candidate provider tests.

T3: Migrate context budget/render helpers
- Change: Move token estimator, budget config merge, render trim, confidence, and trace helpers into package modules.
- Files likely affected: `src/ai_workroot/runtime/context.py`, `src/ai_workroot/core/context.py`.
- Verification: token and context trace tests.

T4: Add package context parity tests
- Change: Port legacy context behavior tests to package imports.
- Files likely affected: `tests/integration/`, `tests/unit/`, `tests/negative/`.
- Verification: full unittest suite.

## Risks

- Large context logic becomes hard to review if moved all at once.
- Legacy tests may keep passing while package context regresses.
- Token budget changes may alter output snapshots.

## Open Questions

None.
