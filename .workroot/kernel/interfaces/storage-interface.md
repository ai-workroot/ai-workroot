# Storage Interface

Storage drivers accelerate lookup or computation.

They must define:

- source files
- generated store paths
- rebuild command
- incremental update behavior
- deletion propagation
- redaction propagation
- release and tombstone filtering
- backup and export behavior
- failure recovery

SQLite and DuckDB are driver choices, not kernel identity.

Generated stores are optional, local-first, rebuildable, and excluded from public release by default.
