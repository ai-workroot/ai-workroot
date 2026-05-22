# Spec: Release Derived Index Safety Hardening

## Status

Draft

## Priority

P0

## Background

Release Control protects ordinary Context Control output by filtering candidates, FTS matches, and relationship signals at render time. That is necessary but not sufficient. Redacted and deleted targets can still leave sensitive derived text in `context_candidates`, candidate FTS, indexed chunks, chunk FTS, and ContextRecallHint materializations. Raw fallback user-asset candidates can also bypass release filtering when all selected candidates were removed.

This Spec closes the P0 safety gap without redesigning Release Control or changing Tombstone semantics.

## Goals

- Prevent raw fallback candidates from reintroducing protected file names after release filtering.
- Sanitize or remove derived index rows for redacted and deleted targets.
- Keep Tombstone, quiet, and archived targets visible or traceable according to current policy.
- Record release propagation and context fallback behavior in inspectable state.
- Add Doctor coverage for release-derived index leakage.

## Non-goals

- Do not add `release_target_type` or `release_target_id` columns to `context_candidates`.
- Do not implement remote deletion workflows.
- Do not introduce a vector database, remote embedding, or remote LLM dependency.
- Do not make Tombstone hard-excluded by default.
- Do not remove legacy compatibility paths.

## Scope

### Included

- Active `src/ai_workroot/` Release Control and Context Control paths.
- Fallback candidate behavior in `runtime/context.py`.
- Derived index sanitation for key SQLite tables.
- Release propagation event and index invalidation records.
- Doctor checks for key release-derived leakage.
- Regression tests in active package tests.

### Excluded

- Legacy Public Seed context implementation except where existing tests must remain green.
- GUI or MCP behavior.
- Full database foreign-key migration.
- Large schema redesign.

## Dependencies

- `007-release-control.spec.md`
- `009-retrieval-index-control.spec.md`
- `010-context-control.spec.md`
- `013-storage-sqlite-schema.spec.md`
- `032-part2-capability-parity-small-specs.spec.md`
- `src/ai_workroot/runtime/context.py`
- `src/ai_workroot/runtime/release.py`
- `src/ai_workroot/indexing/providers/release_provider.py`
- `src/ai_workroot/storage/sqlite.py`

## Requirements

### Functional Requirements

FR-001: Context Control must detect when any candidate, FTS match, or relationship signal was dropped because of `deleted`, `redacted`, or `safety-sensitive`.

FR-002: If a protected drop occurred, raw user-directory fallback candidates must not run.

FR-003: ContextTrace debug JSON must record whether fallback was attempted and the reason when disabled.

FR-004: Creating or updating a `redacted` ReleaseRecord must sanitize derived title, summary, and body text for the target.

FR-005: Creating or updating a `deleted` ReleaseRecord or DeletionRecord must remove or replace ordinary derived rows for the target.

FR-006: Creating redactions and deletion records must write a `release_propagation_events` row.

FR-007: Creating redactions and deletion records must write one or more `index_invalidations` rows for affected derived indexes.

FR-008: ContextRecallHint materialization must not materialize full hint title or summary when its target is redacted or deleted.

FR-009: Doctor must detect leaked derived text for redacted/deleted targets in key active SQLite tables.

FR-010: Tombstone targets must remain annotated, not hard-excluded, and must not trigger strict derived deletion.

### Non-functional Requirements

NFR-001: The implementation must remain local-first and use only the Python standard library.

NFR-002: Sanitation must be idempotent.

NFR-003: The release target resolver remains the only mapping layer from candidates/matches/signals to canonical release targets.

NFR-004: Tests must prove both ordinary output safety and stored derived data safety.

## Proposed Design

### Concepts

Protected drop:
A candidate, FTS match, or relationship signal removed because release evaluation found `deleted`, `redacted`, or `safety-sensitive`.

Derived index:
A table or FTS table that caches text for lookup or scoring and is not canonical source content.

Release propagation:
The synchronous MVP operation that records a release event, invalidates affected indexes, and sanitizes key derived rows in the same SQLite database.

### Data Model

Use existing tables:

```text
release_propagation_events(event_id, release_id, event_type)
index_invalidations(invalidation_id, index_id, reason)
context_candidates
context_candidates_fts
indexed_files
indexed_chunks
indexed_chunks_fts
context_recall_hints
context_recall_hints_fts
```

MVP event IDs may be deterministic enough for idempotency:

```text
relprop:<release-id>:derived-safety
idxinv:<release-id>:context-candidates
idxinv:<release-id>:indexed-chunks
idxinv:<release-id>:context-recall-hints
```

### File Layout

Likely changed files:

```text
src/ai_workroot/runtime/context.py
src/ai_workroot/runtime/release.py
src/ai_workroot/indexing/providers/context_recall_hint_provider.py
src/ai_workroot/indexing/providers/release_provider.py
src/ai_workroot/storage/sqlite.py
src/ai_workroot/runtime/doctor.py
tests/negative/test_release_protection_context.py, tests/negative/test_release_protection_targets.py, tests/negative/test_release_protection_relationships.py
split Context Control integration tests under tests/integration/
tests/unit/test_runtime_release.py
tests/unit/test_context_recall_hints.py
```

### CLI / API

No new user-facing CLI is required for this Spec.

Runtime API changes:

```python
sanitize_release_derived_indexes(conn, *, workroot_id: str, release_id: str, target: ReleaseTargetRef, level: str) -> None
verify_release_derived_index_safety(path: Path) -> list[str]
```

### Runtime Behavior

Context generation:

1. Load/materialize hints.
2. Query candidates.
3. Apply release filters.
4. Apply FTS and relationship release filters.
5. Compute `protected_drop_occurred`.
6. If no selected candidates and no protected drop occurred, run fallback.
7. If protected drop occurred, skip fallback and persist trace metadata.

Release creation:

1. Persist release/redaction/deletion row.
2. If level is strict, sanitize derived stores.
3. Record propagation event.
4. Record invalidations.

### Error Handling

- Missing optional derived tables should not crash release authoring; they should produce no-op sanitation.
- SQL operational errors in Doctor should become findings, not tracebacks.
- Unknown target types should not be assumed safe by context filtering.

### Security / Privacy

- Redacted and deleted source content must not be stored in ordinary derived indexes after sanitation.
- Sanitized placeholders must not include original text.
- Fallback must fail closed after strict release filtering.

### Compatibility

- Existing databases are upgraded through idempotent table and index creation.
- Legacy context behavior remains unchanged in this Spec.

## Acceptance Criteria

AC-001:
Given all normal candidates are dropped because an asset is deleted
When Context Control would otherwise fall back to user-directory files
Then fallback is disabled and the protected file name does not appear in ordinary context.

AC-002:
Given a redacted asset has context candidate title and summary text
When the redaction is created
Then `context_candidates` and `context_candidates_fts` no longer contain the original protected text.

AC-003:
Given a deleted asset has indexed chunks
When the deletion record is created
Then `indexed_chunks` and `indexed_chunks_fts` no longer contain the original protected text.

AC-004:
Given a ContextRecallHint points to a redacted target
When hints are materialized
Then the full hint title and summary are not materialized into `context_candidates`.

AC-005:
Given a deliberately leaked candidate row for a redacted target
When Doctor runs
Then Doctor reports a release-derived index safety failure.

AC-006:
Given a tombstone target has a candidate
When Context Control runs
Then the target remains visible with a tombstone annotation.

## Test Plan

### Unit Tests

- `test_create_redaction_sanitizes_candidate_and_hint_derived_indexes`
- `test_create_deletion_record_removes_indexed_chunk_derived_text`
- `test_context_recall_hint_redacted_target_materializes_placeholder`

### Integration Tests

- `test_fallback_is_disabled_after_protected_release_drop`
- `test_context_trace_records_fallback_disabled_reason`

### Manual Verification

- Run `workroot context --debug` in a temp Workroot with a deleted candidate and confirm fallback status appears in debug output.

## Migration / Rollback

Existing rows are sanitized only when strict release records are created or when Doctor detects leakage. Rollback is a normal Git revert for code. Sanitized derived rows are rebuildable from canonical non-redacted sources only when policy allows.

## Observability / Debugging

- ContextTrace debug JSON records fallback attempted/disabled state.
- Debug markdown includes fallback behavior when `--debug` is used.
- `release_propagation_events` records strict release propagation.
- `index_invalidations` records affected derived indexes.
- Doctor reports release-derived index safety findings.

## Task Breakdown

T1: Add fallback disabled regression test
- Change: Add a negative/integration test that creates a deleted candidate and a same-named user file, then verifies fallback does not expose it.
- Files likely affected: split Context Control integration tests under `tests/integration/`
- Verification: Targeted unittest fails before implementation.

T2: Implement protected-drop fallback gating
- Change: Compute protected drop state and pass fallback behavior into trace/render.
- Files likely affected: `src/ai_workroot/runtime/context.py`
- Verification: Targeted context fallback test passes.

T3: Add derived sanitation tests
- Change: Add tests for redaction/deletion sanitation of candidates, FTS, chunks, and hints.
- Files likely affected: `tests/unit/test_runtime_release.py`, `tests/unit/test_context_recall_hints.py`
- Verification: Tests fail before implementation.

T4: Implement release sanitation and propagation records
- Change: Add sanitation helper and call it from strict release APIs.
- Files likely affected: `src/ai_workroot/runtime/release.py`
- Verification: Unit tests pass.

T5: Add Doctor release-derived leakage check
- Change: Add `verify_release_derived_index_safety` and include it in active Doctor.
- Files likely affected: `src/ai_workroot/storage/sqlite.py`, `src/ai_workroot/runtime/doctor.py`, tests.
- Verification: Doctor leakage test passes.

T6: Run release safety validation
- Change: No code change.
- Files likely affected: None.
- Verification: Targeted tests, full unittest discover, release doctor.

## Risks

- Over-aggressive sanitation could remove Tombstone visibility.
- File-name fallback suppression can reduce context when a Workroot has only user files and a protected drop occurred.
- FTS virtual table deletion must be tested because SQLite FTS behavior differs from normal tables.

## Open Questions

None.
