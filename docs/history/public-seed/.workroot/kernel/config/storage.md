# Storage

Files are the source of truth.

Optional local databases and indexes may accelerate retrieval, but must be disposable and rebuildable from files.

Long-term Workroots should separate source files, summaries, manifests, generated indexes, and large raw data. The core repository should remain readable and portable even after years of use.

## Database Selection

Use the database that matches the work.

### SQLite

Use SQLite for local OLTP-style and index-oriented needs:

- task registry lookup
- run records
- artifact lookup
- decision lookup
- Mind entry lookup
- relationship lookup
- lightweight local state
- small full-text search experiments

SQLite is a good default because it is local, simple, cross-platform, and easy to rebuild from files.

### DuckDB

Use DuckDB for local OLAP-style and analysis-oriented needs:

- analyzing tabular files
- joining larger local datasets
- repeated analytical queries
- profiling and summarizing process data
- role or task-specific analytical workspaces

DuckDB is appropriate when the Workroot needs analytical capability, not just point lookup.

### Shared Rules

All local databases must be:

- optional accelerators
- local-first
- rebuildable from file sources
- documented by manifests
- excluded from public commits by default unless intentionally publishing sample data
- cleared or rebuilt when source material is released, tombstoned, redacted, or deleted

Do not store durable knowledge only in a database. Durable knowledge belongs in readable Workroot files.

Installation and usage may differ between macOS and Windows. Agents should choose setup steps according to the user's operating system and the concrete task context.

## Temporal Fields

Temporal fields use ISO-8601 `TEXT`, not database-specific datetime types.

This is intentional because CSV and Markdown files are the source of truth, SQLite has no dedicated datetime storage class, and ISO-8601 text stays readable, portable, and sortable.

See `.workroot/kernel/config/time.md`.

## Scale Rules

- Keep startup context small.
- Keep generated databases and caches out of Git by default.
- Partition high-volume directories by date, topic, or project.
- Store summaries and manifests in Git; store large raw data only when intentionally needed.
- Treat SQLite, DuckDB, vector indexes, and graph indexes as rebuildable acceleration layers.

## Cache Freshness

Analytical and operational Workroots often need local caches.

When a cache matters, distinguish:

- observation date: the business or life date being analyzed
- extraction date: when source data was pulled
- generation date: when the cache or output file was created
- freshness rule: when the cache is still acceptable
- refresh rule: when the cache must be rebuilt

Use manifests or clear filenames when this distinction affects correctness.

Do not silently treat an old cache as fresh. If freshness matters, say which date the result depends on.
