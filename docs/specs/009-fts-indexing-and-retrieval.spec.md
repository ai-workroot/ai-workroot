# Spec: FTS Indexing and Retrieval

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 must provide local-first, explainable retrieval without requiring a vector database or embedding provider. SQLite FTS, file metadata, recent activity, explicit project files, and git state provide the first retrieval foundation.

## Goals

- Index user assets and managed summaries through local SQLite FTS.
- Support chunked text retrieval with explainable matches and ranking.
- Feed Context Guide and search commands.
- Avoid vector database dependency in P0.
- Avoid remote calls.

## Non-goals

- This Spec does not implement semantic vector retrieval.
- This Spec does not require embedding generation.
- This Spec does not index every binary file body.
- This Spec does not perform full directory scans during Context Guide hot path.

## Scope

### Included

- FTS table and metadata model.
- File indexing strategy.
- Chunking strategy.
- Ranking and search behavior.
- Debug trace integration.
- Relationship to Context Guide and Materialized Context Candidates.

### Excluded

- Context Guide final selection, covered by `007-context-guide-builder.spec.md`.
- Candidate lifecycle, covered by `008-materialized-context-candidates.spec.md`.
- SQLite database initialization, covered by `013-sqlite-cache-and-provenance-graph.spec.md`.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `007-context-guide-builder.spec.md`
- `008-materialized-context-candidates.spec.md`
- `010-debug-trace-and-observability.spec.md`
- `013-sqlite-cache-and-provenance-graph.spec.md`

## Requirements

### Functional Requirements

FR-001: Per-Workroot SQLite must include local FTS tables for indexed text chunks.

FR-002: Indexed records must include source path, source type, chunk ID, title, text, hash, modified time, and indexing time.

FR-003: Indexing must support Markdown, plain text, JSON, JSONL, CSV, and source code text files in P0.

FR-004: Indexing must skip binary files by default.

FR-005: Indexing must skip ignored managed state inside user directories because Clean Mode should not create it.

FR-006: Retrieval must support keyword query with ranking.

FR-007: Retrieval must return matched file/chunk metadata and snippets.

FR-008: Retrieval must record scores and match reasons in debug trace when used by Context Guide.

FR-009: Retrieval must not require vector database or embeddings.

FR-010: Incremental indexing must use file metadata and hashes to avoid unnecessary re-indexing.

### Non-functional Requirements

NFR-001: Retrieval must work offline.

NFR-002: Query results must be explainable.

NFR-003: Indexing must avoid unbounded memory usage.

NFR-004: Context Guide hot path must not perform full index rebuild.

NFR-005: Index data must remain local managed state.

## Proposed Design

### Concepts

- Indexed source: A user asset or managed summary allowed for retrieval.
- Chunk: A bounded text unit stored in FTS.
- Incremental index: Refresh based on path, mtime, size, and hash.
- Retrieval channel: FTS challenger used by Context Guide.

### Data Model

Suggested SQLite schema:

```sql
CREATE TABLE indexed_files (
  file_id TEXT PRIMARY KEY,
  workroot_id TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  source_type TEXT NOT NULL,
  title TEXT,
  size_bytes INTEGER,
  modified_at TEXT,
  content_hash TEXT,
  indexed_at TEXT,
  status TEXT
);

CREATE TABLE indexed_chunks (
  chunk_id TEXT PRIMARY KEY,
  file_id TEXT NOT NULL,
  workroot_id TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  heading TEXT,
  ordinal INTEGER,
  token_estimate INTEGER,
  content_hash TEXT,
  indexed_at TEXT
);

CREATE VIRTUAL TABLE indexed_chunks_fts USING fts5(
  chunk_id,
  title,
  heading,
  body
);
```

### File Layout

FTS data lives under:

```text
<stateDirectory>/cache/workroot.sqlite
```

Index refresh history lives under:

```text
<stateDirectory>/maintenance/history.jsonl
```

No FTS index files are written into the user directory.

### CLI / API

P0 internal APIs:

```text
refresh_fts_index(workroot_id, paths=None)
search_fts(workroot_id, query, limit)
```

P1 CLI:

```bash
workroot search "clean mode"
workroot refresh
```

Context Guide uses `search_fts` in P0.

### Runtime Behavior

Indexing flow:

1. Determine allowed indexed sources from asset registry, explicit project files, managed summaries, and recent activity.
2. Read supported text files with size limits.
3. Chunk by headings or bounded text size.
4. Store file metadata and chunk metadata.
5. Upsert FTS rows.
6. Mark removed files as deleted or stale.

Retrieval flow:

1. Receive query from current task, explicit query, or Context Guide.
2. Query FTS table.
3. Rank by FTS score, recency, source importance, and explicit asset metadata.
4. Return bounded matches with metadata and snippets.
5. Record trace when debug is enabled.

### Error Handling

- If a file cannot be read, mark it skipped with reason.
- If a file exceeds size limits, index metadata and mark body skipped.
- If FTS table is missing, report migration required.
- If query is empty, Context Guide may skip FTS challenger and trace skip reason.

### Security / Privacy

FTS may contain excerpts of user files. It must live only in managed state and must not be synced or sent remotely. Sensitive file patterns should be skipped by default when known, and future configuration may add exclude patterns.

### Compatibility

FTS is required for P0 retrieval but vector search is not. Future semantic retrieval should use a separate optional interface and must not break FTS behavior.

## Acceptance Criteria

AC-001:
Given a text file in a user directory
When indexing runs
Then FTS contains searchable chunks for that file.

AC-002:
Given a binary file in a user directory
When indexing runs
Then the binary body is skipped and the skip reason is recorded.

AC-003:
Given a keyword query
When FTS retrieval runs
Then matched chunks include path, heading, snippet, score, and reason.

AC-004:
Given Context Guide debug mode
When FTS challenger runs
Then FTS matches and scores appear in the debug trace.

AC-005:
Given no vector database
When retrieval runs
Then keyword FTS still works.

## Test Plan

### Unit Tests

- Test supported file type detection.
- Test binary detection.
- Test chunking by heading and size.
- Test ranking composition.
- Test skip reason recording.

### Integration Tests

- Build FTS index from a fixture user directory.
- Search for known terms and assert expected chunks.
- Modify a file and verify incremental re-indexing.
- Delete a file and verify stale/deleted status.
- Run Context Guide with FTS debug trace.

### Manual Verification

- Run refresh on a sample project.
- Run search for known phrases.
- Inspect that no index files appear in the user directory.

## Migration / Rollback

Migration creates FTS tables. Rollback may drop FTS tables because they are rebuildable. Dropping FTS must not remove asset registry records or user files.

## Observability / Debugging

Index refresh should report:

- files scanned;
- files indexed;
- files skipped with reasons;
- chunks inserted or updated;
- elapsed time.

Retrieval trace should report:

- query;
- FTS SQL channel;
- matched chunks;
- scores;
- snippets;
- ranking reasons;
- timing.

## Task Breakdown

T1: Add FTS schema migration
- Change: Create indexed files, chunks, and FTS tables.
- Files likely affected: migration definitions, SQLite module.
- Verification: Migration test inspects tables.

T2: Add chunker
- Change: Parse supported text and create bounded chunks.
- Files likely affected: indexing module.
- Verification: Unit tests for Markdown, text, JSONL, CSV, and source files.

T3: Add incremental indexer
- Change: Use metadata and hash to upsert changed files only.
- Files likely affected: indexing module.
- Verification: Integration test modifies one file and indexes only changed content.

T4: Add FTS search
- Change: Query FTS and return ranked results with metadata.
- Files likely affected: retrieval module.
- Verification: Search integration tests.

T5: Connect Context Guide debug trace
- Change: Include FTS matches and timing in trace.
- Files likely affected: context module, debug module.
- Verification: Trace validation test.

## Risks

- Large files can slow indexing without strict limits.
- FTS ranking may overvalue term frequency without domain and recency weighting.
- Sensitive files may be indexed if exclusion rules are too weak.

## Open Questions

None.
