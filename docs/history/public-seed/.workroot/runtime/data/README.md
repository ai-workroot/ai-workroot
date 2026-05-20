# Data

Optional local process data can live here.

Data stores are accelerators, not the source of truth.

They should be local-first, disposable, rebuildable, and documented by manifests.

## Database Choices

- SQLite: use for local indexes, point lookup, lightweight state, and small full-text search.
- DuckDB: use for local analytical work, tabular data exploration, larger joins, profiling, and repeatable OLAP-style queries.
- Vector and graph stores: future retrieval accelerators; use only when a concrete Workroot needs them.

Every database should have a manifest explaining what it contains and how it can be rebuilt.

Generated databases, caches, and local indexes should not be committed by default. They must not be the only copy of durable knowledge.
