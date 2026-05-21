# Spec 005 — Core Model

Status: accepted
Target: 0.9.530

## Purpose

Define core model files and lightweight implementation style.

## Core files

```text
core/common.py
core/environment.py
core/work.py
core/assets.py
core/release.py
core/relationships.py
core/retrieval.py
core/context.py
core/agent.py
core/health.py
core/extensions.py
```

Do not create one file per entity unless a file grows too large.

## Common concepts

`common.py` should define small shared concepts only:

- typed IDs or ID helpers
- `ActorRef`
- `SourceRef`
- `EvidenceRef`
- `PolicyRef`
- `DomainEvent`
- time helpers/value objects where needed

It must not become a garbage bin.

## Rich model rules

Core objects must include behavior when local to the concept:

Examples:

- `Task.can_transition_to()`
- `Task.close()`
- `Asset.publish()`
- `Asset.mark_missing()`
- `Tombstone.allows_explicit_review()`
- `RelationshipEdge.attach_evidence()`
- `IndexManifest.is_stale()`
- `ContextBudget.requires_trim()`

## Avoid over-ceremony

Do not require:

- repository for every entity;
- service for every entity;
- handler for every use case;
- class for every enum;
- one file per enum.

## External capabilities

Core may use contracts only when necessary.

Prefer:

- core policies for pure rules;
- runtime orchestration for workflows;
- contracts for abstract external capabilities;
- storage/indexing/agent for implementations.

## Acceptance

- core files contain domain behavior, not just dataclasses.
- core does not import storage/indexing/agent/cli/runtime.
- contracts imports are minimal and justified.
- retired terms are not present as active entity names.
