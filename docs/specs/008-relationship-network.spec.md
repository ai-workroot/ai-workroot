# Spec 008 — Relationship Network

Status: accepted  
Target: 0.9.530

## Purpose

Replace Graph as business domain with Relationship Network.

## Entities

### RelationshipNode

Represents an object in the relationship network.

Node types:

```text
workroot
task
asset
agent_run
work_action
handoff
context_package
release_record
tombstone
external_reference
```

### RelationshipEdge

Canonical relationship.

Fields:

```text
edge_id
workroot_id
from_node_id
to_node_id
relationship_type
confidence
status
created_at
updated_at
created_by
```

### RelationshipType

Initial allowlist:

```text
uses
produces
updates
supersedes
supports
contradicts
references
belongs_to
related_to
derived_from
handoff_to
used_in_context
decomposes_to
covered_by_release
```

### RelationshipEvidence

Evidence for a relationship.

Fields:

```text
evidence_id
edge_id
evidence_type
source_ref
asset_id
task_id
context_trace_id
snippet_hash
note
created_at
```

## Canonical vs projection

RelationshipEdge is canonical.

Relationship traversal index is derived and belongs to Retrieval & Index Control.

## Naming

Docs and core code must use Relationship Network terms.

Allowed technical terms:

```text
graph traversal
graph projection
future graph database adapter
```

## Storage

Preferred 0.9.530 schema names:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

If migration risk is too large, compatibility views from old `graph_*` names may be kept temporarily, but docs must use Relationship Network.

## Acceptance

- Business docs do not call the domain Graph.
- RelationshipEdge persists canonical relationship.
- Relationship traversal projection is derived.
- Task decomposition uses Relationship Network.
- Release Control can cover RelationshipEdge without mutating edge truth.
