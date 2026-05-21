# Spec 013 — Storage and SQLite Schema

Status: accepted
Target: 0.9.530

## Purpose

Define storage schema direction for new core model.

## Storage principles

- SQLite can hold canonical state and derived read models.
- Do not call all SQLite data cache.
- Relationship Network canonical tables are not cache.
- FTS/candidates/projections are derived.
- Environment registry may remain JSONL in 0.9.530 but has domain model.

## Required schema areas

### migrations

```text
schema_migrations
```

### workroot management

```text
workroots
directory_bindings
workroot_aliases
workroot_relationships
```

Environment-level records may be JSONL initially, but schema must be documented.

### assets

```text
assets
asset_surfaces
asset_publications
asset_path_history
asset_provenance
```

Remove top-level `knowledge_items` as active model. If old table remains for compatibility, it must map to `assets(asset_type='knowledge')`.

### release control

```text
release_records
tombstones
redactions
deletion_records
release_propagation_events
```

### work

```text
tasks
agent_runs
work_actions
work_checkpoints
retrieval_cards
invalidation_records
handoffs
work_events
operation_transactions
```

### relationships

Preferred:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

Compatibility views for `graph_*` may exist if needed.

### retrieval/index

```text
indexes
index_manifests
index_builds
index_invalidations
indexed_files
indexed_chunks
indexed_chunks_fts
context_candidates
context_candidates_fts
global_index_entries
```

### context

```text
context_packages
context_traces
candidate_selections
budget_trim_decisions
```

### system health

```text
doctor_runs
diagnostic_findings
maintenance_actions
```

## Redaction/deletion requirements

Derived tables must not keep redacted/deleted details.

Doctor must be able to check derived stores for violations.

## Acceptance

- schema migration path documented.
- old `knowledge_items` not treated as top-level domain.
- relationship tables exist.
- release tables exist.
- index manifest/build/invalidation tables exist.
- redacted/deleted negative tests pass.
