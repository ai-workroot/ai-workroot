# Spec: Materialized Context Candidates

## Status

Draft

## Priority

P0

## Background

Context Guide must generate a relevant context package in under 1 second. It cannot rediscover all relevant context on every run. Materialized Context Candidates provide a small, rebuildable SQLite read model of items that may enter context.

Candidates are not facts, not user assets, and not a large JSONL context-card store. They are local acceleration records derived from Workroot state.

## Goals

- Maintain a rebuildable candidate table/cache for fast context selection.
- Store candidate lifecycle, policy, scoring metadata, and token estimates.
- Support invalidation and refresh when source state changes.
- Keep source-of-truth facts outside the candidate table.
- Feed Context Guide without requiring remote services.

## Non-goals

- Candidates are not canonical knowledge.
- Candidates are not a vector database.
- Candidates are not a replacement for FTS.
- Candidates are not automatically summarized by remote LLM calls.

## Scope

### Included

- Candidate table schema.
- Candidate lifecycle.
- Update and invalidation strategy.
- Scoring metadata.
- Relationship to Context Guide.
- Rebuild behavior.

### Excluded

- Context Guide final selection, covered by `007-context-guide-builder.spec.md`.
- FTS file chunk indexing, covered by `009-fts-indexing-and-retrieval.spec.md`.
- SQLite database initialization, covered by `013-sqlite-cache-and-provenance-graph.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `005-migrations.spec.md`
- `007-context-guide-builder.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`

## Requirements

### Functional Requirements

FR-001: Per-Workroot SQLite must include `context_candidates`.

FR-002: Per-Workroot SQLite must include `context_candidates_fts`.

FR-003: Candidate records must include source type, source ID, title, summary, domains, related tasks, related assets, importance, confidence, status, context policy, safety policy, token estimate, updated time, and last used time.

FR-004: Candidate lifecycle must support `active`, `stale`, `archived`, `superseded`, and `gravestone`.

FR-005: Candidate context policy must support `always`, `task-related`, `summary-first`, `on-demand`, and `never-auto`.

FR-006: Only active candidates should normally enter Context Guide selection.

FR-007: Candidate rebuild must be possible from source managed state and user asset metadata.

FR-008: Candidate updates must not call remote services automatically.

FR-009: Candidate invalidation must occur when source records are deleted, released, superseded, or materially changed.

FR-010: Context Guide must record candidate `last_used_at` when selected.

### Non-functional Requirements

NFR-001: Candidate queries must support the Context Guide hot path target.

NFR-002: Candidate records must be small enough for fast scoring.

NFR-003: Candidate generation must be deterministic from the same source state.

NFR-004: Candidate table must remain local-first and explainable.

NFR-005: Candidate cache must tolerate rebuild without data loss because it is not canonical truth.

## Proposed Design

### Concepts

- Candidate: Rebuildable read model row for possible context.
- Source record: Canonical or semi-canonical item from tasks, decisions, knowledge, handoffs, asset registry, or graph.
- Candidate policy: Rule controlling automatic context eligibility.
- Lifecycle status: Whether the candidate is active, stale, archived, superseded, or a gravestone.

### Data Model

SQLite schema:

```sql
CREATE TABLE context_candidates (
  candidate_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  source_type TEXT NOT NULL,
  source_id TEXT NOT NULL,
  title TEXT,
  summary TEXT,
  domains TEXT,
  related_tasks TEXT,
  related_assets TEXT,
  importance TEXT,
  confidence REAL,
  status TEXT,
  context_policy TEXT,
  safety_policy TEXT,
  token_estimate INTEGER,
  updated_at TEXT,
  last_used_at TEXT
);

CREATE VIRTUAL TABLE context_candidates_fts USING fts5(
  candidate_id,
  title,
  summary
);
```

Indexes:

```sql
CREATE INDEX idx_context_candidates_workroot ON context_candidates(workroot_id);
CREATE INDEX idx_context_candidates_status ON context_candidates(status);
CREATE INDEX idx_context_candidates_policy ON context_candidates(context_policy);
CREATE INDEX idx_context_candidates_importance ON context_candidates(importance);
```

### File Layout

Candidates live only in:

```text
<stateDirectory>/cache/workroot.sqlite
```

Optional rebuild reports live under:

```text
<stateDirectory>/maintenance/history.jsonl
```

No candidate JSONL file is created inside the user directory.

### CLI / API

P0 internal APIs:

```text
upsert_context_candidate(candidate)
mark_candidate_stale(source_type, source_id)
rebuild_context_candidates(workroot_id)
query_context_candidates(filters)
```

P1 CLI:

```bash
workroot refresh
workroot cache rebuild
```

Context Guide uses candidate query APIs in P0.

### Runtime Behavior

Candidate lifecycle:

1. Source state changes.
2. Opportunistic maintenance marks related candidates stale or updates them.
3. Rebuild or refresh job upserts candidate rows.
4. Context Guide queries active candidates.
5. Selected candidates get `last_used_at`.
6. Released, superseded, or gravestone sources mark candidates non-active.

`workroot context` hot path may not perform full candidate rebuild. It may use existing candidates and trace stale-cache fallback.

### Error Handling

- If candidate table is missing, report migration required.
- If candidate FTS table is missing, Context Guide may fall back to non-FTS candidate query and trace the fallback.
- If candidate rebuild fails, keep existing candidates and mark maintenance failure.
- If source record cannot be found, mark candidate stale.

### Security / Privacy

Candidates may contain summaries of user assets and knowledge. They must remain local under managed state. Safety policy must prevent sensitive candidates from entering context automatically.

### Compatibility

Candidate table is new in 0.9.529. Legacy Workroots require migration or bootstrap before Context Guide can use candidate selection.

## Acceptance Criteria

AC-001:
Given a migrated Workroot
When SQLite schema is inspected
Then `context_candidates` and `context_candidates_fts` exist.

AC-002:
Given a source decision record
When candidate refresh runs
Then an active decision candidate is created or updated.

AC-003:
Given a source record is superseded
When invalidation runs
Then its candidate status becomes `superseded`.

AC-004:
Given Context Guide selects a candidate
When selection completes
Then `last_used_at` is updated in managed state.

AC-005:
Given a candidate has `never-auto`
When Context Guide runs
Then it is not selected automatically.

## Test Plan

### Unit Tests

- Test candidate serialization.
- Test lifecycle transitions.
- Test policy filtering.
- Test source invalidation mapping.
- Test token estimate bounds.

### Integration Tests

- Run migration and verify table schema.
- Rebuild candidates from fixture task, decision, handoff, and asset registry data.
- Run Context Guide and verify selected candidate usage updates.

### Manual Verification

- Inspect candidate rows with SQLite CLI.
- Run context before and after a candidate refresh.
- Confirm no candidate files appear in user directory.

## Migration / Rollback

Migration creates candidate tables and indexes. Rollback may drop these tables because candidates are rebuildable. Dropping candidate tables must not delete canonical facts, user assets, graph backups, or registry records.

## Observability / Debugging

Candidate refresh should report:

- sources scanned;
- candidates inserted, updated, marked stale, archived, superseded, or gravestone;
- elapsed time;
- failures.

Context debug trace should include candidate counts and filter reasons.

## Task Breakdown

T1: Add candidate schema migration
- Change: Create `context_candidates` and FTS table.
- Files likely affected: migration definitions, SQLite module.
- Verification: Migration test inspects schema.

T2: Add candidate model and repository
- Change: Add upsert, query, lifecycle update, and last-used update APIs.
- Files likely affected: candidate module.
- Verification: Unit tests for CRUD and status transitions.

T3: Add candidate refresh from source state
- Change: Build candidates from tasks, decisions, handoffs, knowledge, assets, domains, and graph signals.
- Files likely affected: candidate refresh module.
- Verification: Integration fixture produces expected candidates.

T4: Connect Context Guide
- Change: Query active candidates and update usage.
- Files likely affected: context module.
- Verification: Context integration test selects candidates.

## Risks

- Candidate summaries can drift from source state if invalidation is incomplete.
- Candidate table can become too large without lifecycle pruning.
- Safety policy mistakes can put sensitive summaries into context.

## Open Questions

None.
