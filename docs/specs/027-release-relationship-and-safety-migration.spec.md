# Spec 027: Release, Relationship, and Safety Migration

## Status

Draft

## Priority

P0

## Background

Release Control and Relationship Network are central 0.9.530 concepts. Current package code already includes release target resolution and relationship signal filtering, but migration is incomplete while legacy graph/context behavior remains in scripts and tests.

## Goals

- Keep `ReleaseRecord.target_type/target_id` canonical.
- Keep `context_candidates.source_type/source_id` as candidate source metadata.
- Use a resolver for candidate, FTS, and relationship release targets.
- Ensure deleted/redacted content never appears in normal context.
- Ensure Relationship signals are backed by real relationship edges.
- Retire Graph as active business wording.

## Non-goals

- Do not add `release_target_type` or `release_target_id` to `context_candidates` in 0.9.530.
- Do not enforce SQLite foreign keys as a hard requirement.
- Do not remove tombstone markers from all context.

## Scope

### Included

- CandidateReleaseTargetResolver.
- Release evaluator priority.
- Relationship nodes/edges/evidence.
- Release-aware filtering for candidates, FTS, and relationship signals.
- Safety policy filtering.

### Excluded

- Remote policy services.
- Team permission systems.
- Full graph database.

## Dependencies

- Spec 007 Release Control.
- Spec 008 Relationship Network.
- Spec 026 Retrieval, Indexing, and Context Control Migration.

## Requirements

### Functional Requirements

FR-001: Resolver must map candidate sources to one or more canonical release target refs.

FR-002: Resolver must support `asset`, `task`, `work_action`, `agent_run`, `checkpoint`, `handoff`, `retrieval_card`, `indexed_chunk`, `fts_match`, `relationship_edge`, and nested `context_candidate` sources.

FR-003: Release evaluator must choose the most protective level in this order: `deleted > redacted > safety-sensitive > tombstone > archived > quiet > none`.

FR-004: Relationship signals rendered in context must be backed by actual relationship edges.

FR-005: Safety policies `never-auto`, `needs-confirmation`, and sensitive policies must be excluded from normal retrieval by default.

### Non-functional Requirements

NFR-001: Release and safety filtering must happen before rendering ordinary context.

NFR-002: Relationship truth must not be owned by indexing projections.

NFR-003: Debug trace must explain dropped release/safety items.

## Proposed Design

### Concepts

Release target: canonical object that Release Control can protect.

Candidate source: read-model source metadata that may resolve to one or more release targets.

Relationship signal: an explainable relation-backed edge relevant to selected candidates, active task, query, or candidate source IDs.

### Data Model

Canonical:

```text
release_records(target_type, target_id, release_level)
tombstones(target_type, target_id)
redactions(target_type, target_id)
deletion_records(target_type, target_id)
relationship_nodes
relationship_edges
relationship_evidence
```

Derived:

```text
context_candidates(source_type, source_id)
indexed_chunks(file_id, chunk_id, source_type, source_id)
```

### File Layout

```text
src/ai_workroot/release/model.py
src/ai_workroot/relationships/model.py
src/ai_workroot/retrieval/providers/release_provider.py
src/ai_workroot/retrieval/providers/relationship_provider.py
src/ai_workroot/context/builder.py
```

### CLI / API

Release and relationship authoring commands may be added later. This spec covers retrieval/context enforcement first.

### Runtime Behavior

Context Control asks the resolver/evaluator for each candidate, FTS hit, and relationship signal. Protected targets are dropped or tombstone-annotated before rendering.

### Error Handling

Unknown source types resolve to the source itself only if that is safe and traceable. Otherwise they are dropped with debug reason `unresolved-release-target`.

### Security / Privacy

Deleted and redacted content is never included in ordinary context. Tombstones may appear as symbolic release state without raw redacted/deleted content.

### Compatibility

Old `graph_nodes` / `graph_edges` fixtures can be migrated or mapped to relationship tables. Active docs and output should use Relationship Network wording.

## Acceptance Criteria

AC-001: Given an indexed chunk whose owning asset is redacted, when context is built, then the chunk text is absent.

AC-002: Given a relationship edge with deleted related target, when relationship signals are loaded, then protected content is absent and the drop reason is traced.

AC-003: Given a high-importance unrelated relationship node, when context is built, then it is not rendered as a signal.

AC-004: Given a tombstoned target, when context is built, then only symbolic tombstone state may appear.

AC-005: Given safety policy `never-auto`, when candidates are queried normally, then the candidate is excluded by default.

## Test Plan

### Unit Tests

- Resolver mappings for all required source types.
- Release priority ordering.
- Safety policy default filtering.
- Relationship signal relation-backed validation.

### Integration Tests

- Context with deleted/redacted/tombstone candidate targets.
- FTS chunk release filtering.
- Relationship edge release filtering.

### Manual Verification

- Run context debug with safety candidates, FTS match, relationship relation, weak unrelated node, and hard token trim.

## Migration / Rollback

Keep resolver centralized. If a migration step fails, disable the new source type mapping rather than bypassing release filters.

## Observability / Debugging

Debug trace must show release target refs, strongest release level, safety policy drops, relationship edge IDs, and reasons for omission.

## Task Breakdown

T1: Harden resolver coverage
- Change: Ensure all required source types resolve through `CandidateReleaseTargetResolver`.
- Files likely affected: `src/ai_workroot/retrieval/providers/release_provider.py`.
- Verification: resolver unit tests.

T2: Enforce safety defaults
- Change: Make candidate queries exclude blocked safety policies by default.
- Files likely affected: `src/ai_workroot/retrieval/providers/candidate_provider.py`.
- Verification: safety filtering tests.

T3: Relationship-only signals
- Change: Ensure rendered signals come from real edges and seed explanations render separately.
- Files likely affected: `src/ai_workroot/retrieval/providers/relationship_provider.py`, `src/ai_workroot/context/builder.py`.
- Verification: relationship signal tests.

T4: Replace graph wording
- Change: Update active docs/output/tests to Relationship Network where applicable.
- Files likely affected: docs and context rendering tests.
- Verification: terminology scan.

## Risks

- Source-to-target resolution misses one-to-many cases.
- Relationship projection rows are mistaken for canonical relationship truth.
- Tombstone handling becomes too aggressive and loses symbolic release state.

## Open Questions

None.
