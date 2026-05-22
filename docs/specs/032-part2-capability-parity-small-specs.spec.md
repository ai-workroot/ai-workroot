# Spec: Part 2 Capability Parity Small Specs

## Status

Accepted for 0.9.530; compatibility notes superseded by `041-runnable-legacy-compat-removal.spec.md`

## Priority

P0

## Background

The 0.9.530 Clean Workroot domain reset moves the active architecture toward `src/ai_workroot/` while preserving existing user value from the Public Seed era. This Spec defines Part 2 capability parity for that migration. It defines small, reversible implementation slices that restore capability parity through active package modules before any compatibility layer is removed.

Each slice is a small Spec iteration with acceptance criteria, targeted tests, and a rollback path.

## Goals

- Preserve Context Card capability through the active ContextRecallHint model.
- Keep `context_candidates` as a materialized read model, not the canonical Context Card store.
- Add active package-owned runtime paths for Work, Asset, Release, and Relationship behavior.
- Add minimal Global Workroot Index visibility without turning global indexes into cross-Workroot knowledge.
- Preserve legacy capability through active package modules and historical archive review; callable compatibility removal is governed by Spec 041.
- Validate every small Spec iteration with targeted tests plus full release gates at checkpoints.

## Non-goals

- Do not remove capability parity. Runnable compatibility removal is handled separately by Spec 041.
- Do not tag, release, or merge from this Spec.
- Do not introduce a vector database, remote embedding service, remote LLM dependency, or cloud service.
- Do not reintroduce Public Seed as the active Clean Workroot architecture.
- Do not add heavy DDD directory structures; DDD remains strategic modeling guidance.
- Do not treat `context_candidates` as canonical knowledge or as the canonical release target.

## Scope

### Included

- ContextRecallHint schema, FTS table, repository, and materialization.
- Release-aware ContextRecallHint target resolution.
- Context Control integration so Context Cards influence selected context.
- Debug trace evidence for hint-derived selected and filtered candidates.
- Minimal active Work runtime.
- Minimal active Asset runtime.
- Minimal active Release authoring runtime.
- Minimal active Relationship authoring runtime.
- Minimal Global Workroot Index visibility.
- Script migration parity audit and wrapper hardening.
- Final capability parity validation.

### Excluded

- Compatibility removal.
- Full replacement of every mature legacy CLI command.
- GUI or C-end first-run installer behavior.
- Cross-Workroot retrieval or knowledge sharing.
- Vector/embedding-backed retrieval.
- Large architectural refactors unrelated to capability parity.

## Dependencies

- Spec 007 Release Control.
- Spec 008 Relationship Network.
- Spec 009 Retrieval & Index Control.
- Spec 010 Context Control.
- Spec 013 Storage SQLite Schema.
- Spec 023 Active Package CLI and Legacy Isolation.
- Spec 024 Work and Asset Runtime Migration.
- Spec 026 Retrieval, Indexing, and Context Control Migration.
- Spec 027 Release, Relationship, and Safety Migration.
- Spec 031 Compatibility-Preserving Script Migration.
- `docs/dev/0.9.530/matrix/legacy-capability-preservation-matrix.md`.
- `docs/dev/0.9.530/scripts-to-src-migration.md`.

## Requirements

### Functional Requirements

FR-001: The active schema must include `context_recall_hints` and `context_recall_hints_fts`.

FR-002: ContextRecallHint repository functions must support insert/update, query, and materialization into ContextCandidate read models.

FR-003: Context generation must materialize relevant ContextRecallHints before querying and selecting candidates.

FR-004: ContextRecallHint-derived candidates must participate in scoring and selection, not only display output.

FR-005: Release evaluation must resolve ContextRecallHint-derived candidates to canonical release targets before filtering or annotation.

FR-006: Deleted and redacted ContextRecallHint targets must be excluded from normal context.

FR-007: Tombstone ContextRecallHint targets must remain annotated, not hard-excluded by default in 0.9.530.

FR-008: Debug traces must record ContextRecallHint source evidence, scoring, selection, and release-filter outcomes.

FR-009: Active Work runtime functions must create and query tasks, agent runs, work actions, checkpoints, handoffs, and invalidations through package-owned code.

FR-010: Active Asset runtime functions must create and query internal/result/decision/knowledge assets without writing user directory files by default.

FR-011: Active Release runtime functions must author release records, tombstones, redactions, deletion records, and target release-state lookups.

FR-012: Active Relationship runtime functions must create and query relationship nodes, edges, and evidence.

FR-013: Global Workroot Index must expose Workroot-level navigation metadata only; it must not own knowledge or create context candidates.

FR-014: Legacy scripts must remain callable while implementation ownership moves into package modules.

FR-015: The parity matrix and migration docs must explicitly mark active, compatibility-scoped, and deferred capabilities.

### Non-functional Requirements

NFR-001: Clean Mode must not write managed state into the user-selected directory by default.

NFR-002: Every small Spec iteration must be reversible through a normal Git revert.

NFR-003: Implementation must remain local-first and standard-library-first.

NFR-004: SQLite changes must be idempotent and migration-recorded.

NFR-005: New modules must stay focused and readable; avoid broad rewrites of unrelated runtime code.

NFR-006: Full validation must pass before checkpoint commit or handoff.

NFR-007: Capability parity tests must be discoverable through `python3 -m unittest discover -s tests -v`.

## Proposed Design

### Concepts

Context Card: product-facing recall anchor that tells Context Control what should be remembered or surfaced.

ContextRecallHint: active code and schema name for Context Card. It points to canonical targets such as Asset, Task, WorkAction, AgentRun, Checkpoint, Handoff, RelationshipEdge, indexed chunks, or legacy RetrievalCard.

ContextCandidate: materialized read model used for retrieval and selection. It is not canonical knowledge and is not the canonical release target.

Global Workroot Index: global navigation metadata under AI Workroot system home. It can list Workroots and metadata but does not own Workroot knowledge.

Small Spec iteration: a scoped implementation slice that changes one capability boundary and proves it with tests.

### Data Model

Add a ContextRecallHint table:

```sql
CREATE TABLE IF NOT EXISTS context_recall_hints (
  hint_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  target_type TEXT NOT NULL,
  target_id TEXT NOT NULL,
  scope_type TEXT,
  scope_id TEXT,
  kind TEXT,
  title TEXT,
  summary TEXT,
  priority TEXT,
  recall_rule TEXT,
  lifecycle_status TEXT,
  origin TEXT,
  source_ref TEXT,
  created_at TEXT,
  updated_at TEXT
);
```

Add FTS and index support:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS context_recall_hints_fts
USING fts5(hint_id, title, summary);

CREATE INDEX IF NOT EXISTS idx_context_recall_hints_workroot_target
ON context_recall_hints(workroot_id, target_type, target_id);
```

Record migration marker:

```sql
INSERT OR IGNORE INTO schema_migrations (migration_id, applied_at)
VALUES ('003-context-recall-hints', datetime('now'));
```

Materialized candidates use:

```text
source_type=context_recall_hint
source_id=<hint_id>
context_policy=<hint.recall_rule>
importance=<hint.priority>
```

### File Layout

Active package additions:

```text
src/ai_workroot/indexing/providers/context_recall_hint_provider.py
src/ai_workroot/indexing/global_indexes.py
src/ai_workroot/runtime/work.py
src/ai_workroot/runtime/assets.py
src/ai_workroot/runtime/release.py
src/ai_workroot/runtime/relationships.py
```

Changed active package files:

```text
src/ai_workroot/storage/sqlite.py
src/ai_workroot/runtime/context.py
src/ai_workroot/indexing/providers/release_provider.py
src/ai_workroot/indexing/providers/relationship_provider.py
```

Tests:

```text
tests/unit/test_context_recall_hints.py
tests/unit/test_release_target_resolver.py
tests/unit/test_runtime_work.py
tests/unit/test_runtime_assets.py
tests/unit/test_runtime_release.py
tests/unit/test_runtime_relationships.py
tests/unit/test_global_indexes.py
tests/integration/test_environment_storage.py
split Context Control integration tests under tests/integration/
```

No file in this Spec may create managed state inside the user-selected Workroot directory by default.

### CLI / API

No new primary CLI command is required by this Spec. Context behavior remains available through:

```text
python -m ai_workroot context
python -m ai_workroot context --debug
```

Legacy scripts remain compatibility entry points. They are not promoted as active Clean Workroot architecture.

### Runtime Behavior

Context Control materializes relevant ContextRecallHints before candidate query and selection. Hint-derived candidates then flow through the same dedupe, scoring, safety, release, and token-budget logic as other candidates.

Release evaluation resolves hint-derived candidates through the CandidateReleaseTargetResolver. The evaluator checks all resolved target refs and applies the most protective release state:

```text
deleted > redacted > safety-sensitive > tombstone > archived > quiet > none
```

Global indexes refresh Workroot-level metadata under AI Workroot system home. They must not materialize ContextCandidates or store per-Workroot knowledge bodies.

### Error Handling

Schema initialization must be idempotent. Missing FTS support or operational query errors must degrade gracefully where existing retrieval behavior already supports fallback, while debug traces record fallback evidence.

Runtime helper functions must return deterministic records or raise clear `ValueError`/`RuntimeError` messages for invalid required fields.

### Security / Privacy

All new behavior is local-first. No remote calls are allowed. Deleted and redacted content must not enter normal context packages. Tombstones remain visible only as state annotations unless later architecture explicitly changes the default behavior.

### Compatibility

Legacy script compatibility remains intact. Public Seed behavior may be compatibility-scoped, but it must not be documented as the active Clean Workroot architecture. Compatibility removal requires a later explicit approval step.

## Acceptance Criteria

AC-001:
Given a fresh Workroot SQLite database
When schema initialization runs
Then `context_recall_hints`, `context_recall_hints_fts`, and `003-context-recall-hints` exist.

AC-002:
Given an active ContextRecallHint matching a context query
When Context Control builds a package
Then the hint-derived candidate can be selected and appears in debug trace evidence.

AC-003:
Given a ContextRecallHint targeting a redacted or deleted target
When Context Control builds normal context
Then the candidate is dropped and the trace records the release reason.

AC-004:
Given a ContextRecallHint targeting a tombstoned target
When Context Control builds normal context
Then the candidate may appear with tombstone annotation instead of being hard-excluded.

AC-005:
Given Work, Asset, Release, and Relationship runtime helpers
When unit tests call the active package APIs
Then records are written to and read from SQLite without relying on legacy script internals.

AC-006:
Given a refreshed Global Workroot Index
When the index is inspected
Then it contains Workroot navigation metadata only and no knowledge body or ContextCandidate data.

AC-007:
Given the branch test suite
When `python3 -m unittest discover -s tests -v` runs
Then all unit, integration, smoke, and negative tests are discovered and pass.

## Test Plan

### Unit Tests

- ContextRecallHint insert/update/query/materialization tests.
- CandidateReleaseTargetResolver tests for ContextRecallHint and canonical target expansion.
- Runtime Work helper tests.
- Runtime Asset helper tests.
- Runtime Release helper tests.
- Runtime Relationship helper tests.
- Global Workroot Index helper tests.

### Integration Tests

- SQLite schema initialization includes ContextRecallHint tables, FTS table, indexes, and migration marker.
- Context Control selects hint-derived candidates.
- Context Control drops redacted/deleted hint targets.
- Context Control annotates tombstoned hint targets.
- Context trace records hint-derived selected and dropped candidates.

### Manual Verification

- Run `python -m ai_workroot context --debug` against a temporary Workroot with a ContextRecallHint.
- Confirm no managed state is written into the user-selected directory.
- Confirm legacy script entry points remain callable if touched by wrapper migration.

## Migration / Rollback

Migration adds idempotent SQLite schema creation plus a `003-context-recall-hints` migration marker. Rollback is a normal Git revert before release. Existing databases that already contain the table must remain valid.

## Observability / Debugging

Context debug traces must show:

- ContextRecallHint candidate source.
- Selected and filtered candidate IDs.
- Release target refs used for filtering.
- Drop reasons for deleted/redacted targets.
- Tombstone annotation evidence.
- Timing and token-budget metadata already required by Context Control.

## Task Breakdown

T1: Capability parity gates and baseline
- Change: Add this Spec and keep parity matrix/migration docs aligned.
- Files likely affected: `docs/specs/032-part2-capability-parity-small-specs.spec.md`, `docs/dev/0.9.530/matrix/legacy-capability-preservation-matrix.md`, `docs/dev/0.9.530/scripts-to-src-migration.md`.
- Verification: `rg -n "Context Card|ContextRecallHint|Work runtime|Asset runtime|Release Control|Relationship Network" docs/architecture docs/dev docs/specs`.

T2: ContextRecallHint schema and provider
- Change: Add SQLite tables, FTS, index, migration marker, and provider functions.
- Files likely affected: `src/ai_workroot/storage/sqlite.py`, `src/ai_workroot/indexing/providers/context_recall_hint_provider.py`, `tests/integration/test_environment_storage.py`, `tests/unit/test_context_recall_hints.py`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.integration.test_environment_storage tests.unit.test_context_recall_hints -v`.

T3: ContextRecallHint materialization in Context Control
- Change: Materialize relevant hints before candidate query/selection.
- Files likely affected: `src/ai_workroot/runtime/context.py`, split Context Control integration tests under `tests/integration/`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.integration.test_context_retrieval_selection.ContextRetrievalSelectionTest.test_context_recall_hint_affects_active_context_selection -v`.

T4: Release-aware ContextRecallHint resolution
- Change: Resolve hint candidates to hint and canonical targets; apply protective release state.
- Files likely affected: `src/ai_workroot/indexing/providers/release_provider.py`, `tests/unit/test_release_target_resolver.py`, split Context Control integration tests under `tests/integration/`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_release_target_resolver tests.integration.test_context_retrieval_selection tests.integration.test_context_budget_trace tests.integration.test_context_release_filtering -v`.

T5: Context trace parity for hint-derived candidates
- Change: Record selected and dropped hint-derived candidate evidence.
- Files likely affected: `src/ai_workroot/runtime/context.py`, split Context Control integration tests under `tests/integration/`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.integration.test_context_retrieval_selection tests.integration.test_context_budget_trace tests.integration.test_context_release_filtering -v`.

T6: Minimal active Work runtime
- Change: Add package-owned helpers for tasks, agent runs, work actions, checkpoints, handoffs, and invalidations.
- Files likely affected: `src/ai_workroot/runtime/work.py`, `tests/unit/test_runtime_work.py`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_runtime_work -v`.

T7: Minimal active Asset runtime
- Change: Add package-owned helpers for internal/result/decision/knowledge assets.
- Files likely affected: `src/ai_workroot/runtime/assets.py`, `tests/unit/test_runtime_assets.py`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_runtime_assets -v`.

T8: Minimal active Release authoring runtime
- Change: Add package-owned helpers for release records, tombstones, redactions, deletion records, and release-state lookup.
- Files likely affected: `src/ai_workroot/runtime/release.py`, `tests/unit/test_runtime_release.py`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_runtime_release -v`.

T9: Minimal active Relationship authoring runtime
- Change: Add package-owned helpers for relationship nodes, edges, evidence, and query.
- Files likely affected: `src/ai_workroot/runtime/relationships.py`, `tests/unit/test_runtime_relationships.py`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_runtime_relationships -v`.

T10: Minimal Global Workroot Index visibility
- Change: Add package-owned global index refresh/query helpers.
- Files likely affected: `src/ai_workroot/indexing/global_indexes.py`, `tests/unit/test_global_indexes.py`.
- Verification: `PYTHONPATH=src python3 -m unittest tests.unit.test_global_indexes -v`.

T11: Script migration parity audit and wrapper hardening
- Change: Prove remaining script-owned behavior is package-owned, compatibility-wrapped, or explicitly deferred.
- Files likely affected: `docs/dev/0.9.530/scripts-to-src-migration.md`, wrapper scripts only if a tested compatibility gap is found.
- Verification: targeted wrapper tests plus `scripts/dev/validate-release.sh`.

T12: Final capability parity validation
- Change: Run full tests and docs sweep; fix only verified gaps.
- Files likely affected: docs/tests only as needed.
- Verification: full validation commands in this Spec all pass.

## Risks

- Context Cards may regress if only materialized candidates are implemented but release resolution is skipped.
- Legacy script compatibility may appear preserved while package-owned tests remain incomplete.
- Global indexes may accidentally grow into cross-Workroot knowledge storage if boundaries are not enforced.
- Tombstone semantics may be over-tightened and hide useful context contrary to 0.9.530 decisions.
- Test discovery may miss nested tests without package markers.

## Open Questions

None for the current small Spec iterations. Compatibility removal remains a future decision and is intentionally out of scope.
