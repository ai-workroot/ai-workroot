# Spec: Time and Global Index Parity

## Status

Draft

## Priority

P1

## Background

Part 2 capability parity for 0.9.530 requires preserving useful legacy recall and navigation behavior while the active architecture moves into `src/ai_workroot/`. ContextRecallHint, Work, Asset, Release, and Relationship active paths now exist. The remaining gap is the supporting time dimension and Global Index projections for Task, Asset, and Time navigation.

This Spec completes the remaining lightweight parity layer without removing legacy compatibility.

## Goals

- Add a minimal `TimeEvent` active runtime path.
- Reserve lightweight `TimeRange` and `TemporalScope` value objects.
- Store time events in managed SQLite state.
- Add GlobalTaskIndex, GlobalAssetIndex, GlobalTimeIndex, and WorkrootTimeIndex projections.
- Keep Global Index as navigation metadata, not cross-Workroot knowledge or context recall.
- Add explicit migration priority to the scripts-to-source migration matrix.

## Non-goals

- Do not implement complex time-range Release Control.
- Do not write time-based asset surfaces into user directories by default.
- Do not remove or narrow legacy compatibility.
- Do not use Global Index as a default Context Control source.
- Do not introduce vector retrieval, remote embeddings, remote LLMs, or cloud dependencies.

## Scope

### Included

- `time_events` SQLite table, index, and migration marker.
- `runtime/time.py` minimal record/query API.
- `global-index/tasks.index.jsonl`.
- `global-index/assets.index.jsonl`.
- `global-index/time.index.jsonl`.
- Per-Workroot `global_index_entries` projections for task, asset, and time event entries.
- Migration matrix `Migration priority` column.

### Excluded

- Time-range redaction/deletion behavior.
- Calendar UI or time-based user-directory publishing.
- Cross-Workroot Context Control.
- Legacy script removal.

## Dependencies

- Spec 003 Workroot Environment Managed State.
- Spec 009 Retrieval & Index Control.
- Spec 013 Storage SQLite Schema.
- Spec 024 Work and Asset Runtime Migration.
- Spec 031 Compatibility-Preserving Script Migration.
- Spec 032 Part 2 Capability Parity Small Specs.

## Requirements

### Functional Requirements

FR-001: SQLite initialization must create `time_events`.

FR-002: SQLite initialization must create `idx_time_events_workroot_subject`.

FR-003: SQLite initialization must record `006-time-events`.

FR-004: `runtime/time.py` must provide `record_time_event`.

FR-005: `runtime/time.py` must provide `query_time_events`.

FR-006: Global Index must refresh and query Workroot task entries.

FR-007: Global Index must refresh and query Workroot asset entries.

FR-008: Global Index must refresh and query Workroot time event entries.

FR-009: Global Index refresh must not create ContextCandidates.

FR-010: The scripts-to-source migration matrix must include migration priority for every script row.

### Non-functional Requirements

NFR-001: All state must remain under AI Workroot system home or per-Workroot managed state.

NFR-002: The implementation must remain local-first and standard-library-only.

NFR-003: Index projections must be deterministic JSONL files.

NFR-004: The feature must be covered by discoverable `unittest` tests.

## Proposed Design

### Concepts

TimeEvent is a supporting projection event for recency, lifecycle, and navigation. It is not a standalone top-level domain and does not replace Work, Asset, Release, or Relationship records.

TimeRange and TemporalScope are lightweight value objects reserved for time-windowed retrieval and future release controls.

GlobalTaskIndex, GlobalAssetIndex, GlobalTimeIndex, and WorkrootTimeIndex are navigation projections. They do not store canonical knowledge bodies and are not used by Context Control for default cross-Workroot recall.

### Data Model

```sql
CREATE TABLE IF NOT EXISTS time_events (
  event_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  subject_type TEXT NOT NULL,
  subject_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  time_range_start TEXT,
  time_range_end TEXT,
  source_ref TEXT,
  created_at TEXT
);
```

### File Layout

```text
src/ai_workroot/runtime/time.py
src/ai_workroot/indexing/global_indexes.py
src/ai_workroot/storage/sqlite.py
tests/unit/test_runtime_time.py
tests/unit/test_global_indexes.py
tests/integration/test_environment_storage.py
```

Global JSONL projections:

```text
AI_WORKROOT_HOME/global-index/tasks.index.jsonl
AI_WORKROOT_HOME/global-index/assets.index.jsonl
AI_WORKROOT_HOME/global-index/time.index.jsonl
```

### CLI / API

No new CLI command is required. These APIs support runtime/indexing internals and future CLI surfaces.

### Runtime Behavior

`record_time_event` upserts a managed SQLite row. `query_time_events` filters by Workroot and optionally by subject type/id.

Global index refresh scans registered Workroots, opens each per-Workroot SQLite database, reads task/asset/time rows, writes per-Workroot `global_index_entries`, and writes global JSONL projection files.

### Error Handling

Missing registered Workroot SQLite databases are initialized before projection. Empty tables produce empty projection output. Invalid required runtime API arguments raise clear `ValueError`.

### Security / Privacy

Global Index entries are metadata projections only. They must not include asset body, context package text, redacted content, or deleted content body.

### Compatibility

Legacy scripts remain callable. This Spec only adds active package-owned projection paths.

## Acceptance Criteria

AC-001:
Given a fresh Workroot SQLite database
When schema initialization runs
Then `time_events`, `idx_time_events_workroot_subject`, and `006-time-events` exist.

AC-002:
Given a Workroot SQLite database
When `record_time_event` is called
Then `query_time_events` returns the event filtered by Workroot and subject.

AC-003:
Given registered Workroots with task, asset, and time event rows
When Global Index refresh runs
Then task, asset, and time JSONL projections are written under `AI_WORKROOT_HOME/global-index`.

AC-004:
Given Global Index refresh runs
When `context_candidates` is inspected
Then no candidates are created by Global Index.

AC-005:
Given the scripts-to-source migration matrix
When release surface tests inspect it
Then every script row has a P0/P1/P2/P3 migration priority.

## Test Plan

### Unit Tests

- `tests/unit/test_runtime_time.py`
- `tests/unit/test_global_indexes.py`

### Integration Tests

- `tests/integration/test_environment_storage.py`

### Manual Verification

- Inspect generated `global-index/*.index.jsonl` in a temporary `AI_WORKROOT_HOME`.

## Migration / Rollback

Migration adds `time_events`, `idx_time_events_workroot_subject`, and marker `006-time-events`. Rollback is a normal Git revert before release.

## Observability / Debugging

Global projection files are inspectable JSONL. Per-Workroot `global_index_entries` can be queried in SQLite for local debugging.

## Task Breakdown

T1: Add TimeEvent schema
- Change: Add `time_events`, index, and migration marker.
- Files likely affected: `src/ai_workroot/storage/sqlite.py`, `tests/integration/test_environment_storage.py`.
- Verification: targeted environment storage test.

T2: Add TimeEvent runtime
- Change: Add `record_time_event` and `query_time_events`.
- Files likely affected: `src/ai_workroot/runtime/time.py`, `tests/unit/test_runtime_time.py`.
- Verification: targeted runtime time tests.

T3: Add Global Task/Asset/Time Index projections
- Change: Add refresh/query helpers and JSONL outputs.
- Files likely affected: `src/ai_workroot/indexing/global_indexes.py`, `tests/unit/test_global_indexes.py`.
- Verification: targeted global index tests.

T4: Add migration priorities
- Change: Add `Migration priority` column to script migration matrix.
- Files likely affected: `docs/dev/0.9.530/scripts-to-src-migration.md`, `tests/test_public_seed_surface.py`.
- Verification: targeted public seed surface test.

T5: Full validation
- Change: Run full tests and release gates.
- Files likely affected: none unless failures reveal gaps.
- Verification: full validation suite.

## Risks

- Global indexes could accidentally become knowledge storage if body fields are added.
- TimeEvent could become a bloated domain if scope expands beyond projection metadata.
- Migration matrix priority may be misread as removal approval; compatibility removal remains out of scope.

## Open Questions

None.
