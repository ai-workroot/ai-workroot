# Spec: SQLite Cache and Provenance Graph

## Status

Draft

## Priority

P0

## Background

AI Workroot 0.9.529 uses SQLite as the local acceleration and graph/query layer. SQLite stores per-Workroot query acceleration, FTS, graph storage/query, Materialized Context Candidates, and global index cache. For most Workroot facts, source files remain the source of truth. For graph data, SQLite is the primary graph store in 0.9.529, with export, backup, and rebuild support.

## Goals

- Initialize global and per-Workroot SQLite databases.
- Enable WAL mode for read/write concurrency.
- Create graph tables, candidate tables, and FTS tables through migrations.
- Keep SQLite local and rebuildable where applicable.
- Support graph export, backup, and rebuild.

## Non-goals

- This Spec does not require a vector database.
- This Spec does not use SQLite as the only source of truth for all Workroot facts.
- This Spec does not implement cloud database sync.
- This Spec does not implement deep graph traversal in Context Guide hot path.

## Scope

### Included

- Per-Workroot SQLite database layout.
- Global SQLite database layout.
- Graph table schema.
- WAL mode.
- Export, backup, and rebuild requirements.
- Relationship to FTS and context candidates.

### Excluded

- Candidate lifecycle details, covered by `008-materialized-context-candidates.spec.md`.
- FTS indexing behavior, covered by `009-fts-indexing-and-retrieval.spec.md`.
- Context Guide selection behavior, covered by `007-context-guide-builder.spec.md`.
- Concurrency merge semantics beyond SQLite WAL and transactions.

## Dependencies

- Core project decisions: Clean Mode; managed state outside the user directory; controlled bootstrap; high-quality Context Guide; Materialized Context Candidates; local-first explainable retrieval without a P0 vector dependency; debug traces; branch-and-review Git workflow; English-first docs and comments.
- `003-managed-state-layout.spec.md`
- `005-migrations.spec.md`
- `008-materialized-context-candidates.spec.md`
- `009-fts-indexing-and-retrieval.spec.md`

## Requirements

### Functional Requirements

FR-001: Per-Workroot SQLite must live at `<stateDirectory>/cache/workroot.sqlite`.

FR-002: Global SQLite must live at `<AI_WORKROOT_HOME>/global-cache/global.sqlite`.

FR-003: SQLite connections must enable WAL mode where supported.

FR-004: Per-Workroot SQLite must include graph node, graph edge, and graph edge evidence tables.

FR-005: Per-Workroot SQLite must include context candidate tables.

FR-006: Per-Workroot SQLite must include FTS indexing tables.

FR-007: Global SQLite must store registered Workroots, global index cards, cross-Workroot navigation cards, and global FTS.

FR-008: Graph export must produce a portable file under managed state.

FR-009: Graph backup must produce a backup under managed state.

FR-010: Graph rebuild must be able to rebuild from exported graph data and source records where available.

FR-011: Doctor must verify required SQLite tables.

### Non-functional Requirements

NFR-001: SQLite use must be local-first and offline.

NFR-002: SQLite reads must support Context Guide hot path latency goals.

NFR-003: SQLite writes must use transactions.

NFR-004: SQLite schema must be migrated through ordered migrations.

NFR-005: SQLite caches must not be committed by default.

## Proposed Design

### Concepts

- Global SQLite: User-level cache for navigation and global index cards.
- Per-Workroot SQLite: Local query, FTS, candidate, and graph store for one Workroot.
- Provenance graph: Relationship model connecting tasks, assets, knowledge, decisions, rules, domains, handoffs, time events, agent runs, and context packages.
- Rebuildable cache: SQLite data that can be regenerated from source records.

### Data Model

Graph tables:

```sql
CREATE TABLE graph_nodes (
  node_id TEXT PRIMARY KEY,
  node_type TEXT NOT NULL,
  kind TEXT,
  title TEXT,
  summary TEXT,
  status TEXT,
  importance TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE graph_edges (
  edge_id TEXT PRIMARY KEY,
  from_node_id TEXT NOT NULL,
  to_node_id TEXT NOT NULL,
  relation TEXT NOT NULL,
  strength REAL,
  confidence REAL,
  status TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE graph_edge_evidence (
  edge_id TEXT,
  evidence_type TEXT,
  relative_path TEXT,
  heading TEXT,
  snippet TEXT,
  source_id TEXT
);
```

Indexes:

```sql
CREATE INDEX idx_graph_edges_from ON graph_edges(from_node_id);
CREATE INDEX idx_graph_edges_to ON graph_edges(to_node_id);
CREATE INDEX idx_graph_edges_relation ON graph_edges(relation);
CREATE INDEX idx_graph_nodes_type ON graph_nodes(node_type);
```

Allowed graph node types:

```text
task
asset
knowledge
decision
rule
concept
domain
handoff
time-event
agent-run
context-package
```

Allowed relation types include:

```text
derived_from
extracted_from
summarized_from
documented_in
implemented_in
published_as
belongs_to_task
produced_by_task
belongs_to_domain
supports
contradicts
updates
supersedes
depends_on
confirmed_by_user
used_in_context
created_during
```

### File Layout

```text
<AI_WORKROOT_HOME>/
  global-cache/
    global.sqlite
  workroots/
    <workrootId>/
      graph/
        exports/
        backups/
      cache/
        workroot.sqlite
```

No SQLite database is written inside the user directory in Clean Mode.

### CLI / API

P0 internal APIs:

```text
open_global_sqlite()
open_workroot_sqlite(workroot_id)
initialize_sqlite_schema(scope)
verify_sqlite_schema(scope)
```

P1 CLI:

```bash
workroot graph export
workroot graph backup
workroot graph rebuild
workroot cache rebuild
```

P0 may include internal graph export/backup functions used by doctor or tests.

### Runtime Behavior

SQLite init flow:

1. Resolve managed state directory.
2. Open SQLite database.
3. Enable WAL mode.
4. Apply schema migrations.
5. Verify required tables and indexes.

Graph usage:

- Context Guide may query one-hop graph edges.
- Graph-derived context payload must remain small.
- Graph signals default max is 3 to 5.
- Deep graph traversal is not used in P0 hot path.

### Error Handling

- If SQLite cannot open, report path and OS error.
- If WAL mode fails, warn or fail depending on platform support and write requirement.
- If schema is missing, report migration required.
- If graph export fails, leave existing backups untouched.
- If rebuild fails, preserve prior database or backup when possible.

### Security / Privacy

SQLite may contain summaries, snippets, relationship metadata, and indexed text. It must remain local under managed state. SQLite files must not be committed by default or written into the user directory in Clean Mode.

### Compatibility

SQLite is part of P0. Vector database is not. Future graph or vector drivers may be extensions, but P0 must remain usable with SQLite only.

## Acceptance Criteria

AC-001:
Given a new Clean Mode Workroot
When managed state initializes
Then `<stateDirectory>/cache/workroot.sqlite` exists.

AC-002:
Given SQLite initializes
When PRAGMA journal mode is checked
Then WAL mode is enabled where supported.

AC-003:
Given a migrated Workroot
When schema is inspected
Then graph tables, context candidate tables, and FTS tables exist.

AC-004:
Given a graph edge is inserted
When graph one-hop query runs
Then related node and edge metadata are returned.

AC-005:
Given Clean Mode
When SQLite initializes
Then no SQLite file is created inside the user directory.

## Test Plan

### Unit Tests

- Test SQLite path resolution.
- Test schema creation SQL.
- Test graph node and edge insertion.
- Test one-hop graph query.
- Test export data formatting.

### Integration Tests

- Initialize global and per-Workroot SQLite databases.
- Run migrations and verify required tables.
- Run doctor against healthy and missing-table fixtures.
- Run graph export and backup into managed state.

### Manual Verification

- Inspect SQLite tables with SQLite CLI.
- Confirm WAL files remain under managed cache.
- Confirm no SQLite files appear in user directory.

## Migration / Rollback

SQLite schema changes must be applied by `005-migrations.spec.md`. Cache tables may be dropped and rebuilt. Graph tables are primary in 0.9.529, so migrations affecting graph tables must create backups before changing schema and support export before destructive changes.

## Observability / Debugging

Doctor must report:

- database path;
- open status;
- WAL status;
- required table status;
- graph table status;
- candidate and FTS table status.

Context debug trace must include graph edges used and SQLite query timing.

## Task Breakdown

T1: Add SQLite opener
- Change: Open global and per-Workroot SQLite with WAL mode.
- Files likely affected: SQLite module.
- Verification: Unit test checks PRAGMA journal mode.

T2: Add schema migrations
- Change: Create graph, candidate, FTS, and global cache tables.
- Files likely affected: migration definitions.
- Verification: Integration test inspects schema.

T3: Add graph repository
- Change: Insert and query graph nodes, edges, and evidence.
- Files likely affected: graph module.
- Verification: Unit tests for graph operations.

T4: Add export and backup
- Change: Export graph and backup SQLite under managed state.
- Files likely affected: graph module, CLI P1 if included.
- Verification: Integration test creates export and backup files.

T5: Add doctor SQLite checks
- Change: Verify DB open, WAL, and tables.
- Files likely affected: doctor module.
- Verification: Doctor tests detect missing table.

## Risks

- Treating graph SQLite as primary requires careful backup before schema changes.
- WAL behavior differs on network filesystems.
- SQLite cache can grow large without pruning policies.
- Graph relationship semantics can become too broad if not constrained.

## Open Questions

None.
