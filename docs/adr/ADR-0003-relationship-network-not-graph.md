# ADR-0003 — Relationship Network, not Graph

Status: accepted

## Decision

The business domain is named Relationship Network. Graph remains only a technical/implementation term.

## Rationale

AI Workroot maintains relationships among tasks, assets, releases, context packages, and agents. Calling the domain Graph overemphasizes a data structure or graph database implementation.

## Consequences

- Use RelationshipNode/RelationshipEdge/RelationshipEvidence in core language.
- Graph traversal/projection may still appear in indexing/technical docs.
