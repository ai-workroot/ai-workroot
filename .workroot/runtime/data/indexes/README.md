# Local Indexes

Optional local indexes can live here.

Examples:

- SQLite task and mind index
- DuckDB analytical/process index when a Workroot needs local analysis
- full-text search index

These must be rebuildable from files.

They are allowed to become more sophisticated over time, including incremental updates, vector indexes, and graph indexes. Full rebuild from file sources must remain available.

## SQLite

SQLite is the recommended first local index database for v0.9.527 practice.

Use it for:

- task registry queries
- task run records
- artifact lookup
- decision lookup
- Mind entry lookup
- relationship lookup
- lightweight full-text search experiments

Do not use SQLite as the only source of truth. Every durable record must still exist as a readable file in the Workroot.

Temporal columns use ISO-8601 `TEXT` by design. See `.workroot/kernel/config/time.md`.

Recommended path:

```text
.workroot/runtime/data/indexes/workroot.sqlite
```

Recommended schema:

```text
.workroot/runtime/data/indexes/schema.sql
```

The database can be deleted and rebuilt from files.

## DuckDB

DuckDB can be used when the Workroot needs local analytical queries rather than point lookup.

Use it for:

- tabular data analysis
- joining multiple local files
- profiling process datasets
- repeated task or role analysis
- analytical reports that should be reproducible

Recommended path when used:

```text
.workroot/runtime/data/indexes/workroot.duckdb
```

DuckDB must also be rebuildable from files and documented by a manifest.

Do not use DuckDB as the only place where durable knowledge or decisions live.

## Manifests

Every non-trivial local index should have a small manifest describing:

- purpose
- source files
- rebuild command
- update strategy
- privacy/deletion considerations

Indexes must not become hidden archives of released, tombstoned, redacted, or deleted material.
