# Spec 009 — Retrieval & Index Control

Status: accepted
Target: 0.9.530

## Purpose

Define retrieval and indexing as a core system capability serving context recall and local management queries.

## Entities and objects

### Index

Domain index, not database index.

Fields:

```text
index_id
workroot_id_or_environment_id
scope
tier
kind
source_domain
status
last_built_at
last_refreshed_at
row_count
staleness
rebuild_policy
retention_policy
```

### IndexScope

```text
environment
workroot
task
asset
extension
system
```

### IndexTier

```text
startup
active
registry
evidence
asset_recall
relationship
deep
accelerator
```

### IndexKind

```text
navigation
registry
metadata
text
fts
candidate
relationship_projection
vector
search
time
capability
```

### IndexManifest

Describes purpose, sources, provider, refresh strategy, release handling, and rebuild policy.

### IndexEntry

Generic read model row. Specific projections may implement structured entries:

- `GlobalWorkrootIndexEntry`
- `GlobalTaskIndexEntry`
- `GlobalAssetIndexEntry`
- `TextChunkEntry`
- `ContextCandidateEntry`
- `RelationshipTraversalEntry`

### RetrievalRequest / RetrievalResult / RetrievalPlan

Request/response/plan objects for retrieval.

## Provider / Contract / Adapter

Contracts define protocols:

```text
RetrievalProvider
IndexRepository
IndexRefreshGateway
```

Adapters implement protocols:

```text
SQLiteFtsProvider
CandidateProvider
RelationshipTraversalProvider
MetadataProvider
VectorProvider (reserved)
SearchProvider (reserved)
```

No actual vector DB, remote embedding, or remote LLM dependency in 0.9.530.

## Uses

### Context recall

Context Control uses Retrieval & Index Control for:

- candidates;
- FTS matches;
- metadata;
- relationship traversal projection;
- future provider fusion.

### Management queries

CLI/UI/System Health use Retrieval & Index Control for:

- list Workroots;
- list Tasks;
- list Assets;
- list Releases/Tombstones;
- index status;
- stale/corrupt index reporting.

## Release handling

Indexes must recognize:

- quiet;
- archived;
- tombstone;
- redacted;
- deleted;
- safety-sensitive.

0.9.530 behavior:

- tombstone/quiet/archive: annotate and trace.
- redacted/deleted/safety-sensitive: strictly protect.

## Acceptance

- Global indexes are environment-scoped.
- Workroot indexes are Workroot-scoped.
- ContextCandidate is read model, not Asset.
- FTS rows are read models, not Assets.
- Relationship traversal indexes are derived.
- Redacted/deleted entries cannot leak through FTS/candidates.
