# Spec 005 - Capability Model

Status: accepted; source package names updated by the command-first architecture refactor
Target: 0.9.530

## Purpose

Define capability model files and lightweight implementation style.

## Capability files

```text
state/model.py
capabilities/work/model.py
capabilities/assets/model.py
capabilities/release/model.py
capabilities/handoff/model.py
capabilities/relationships/model.py
capabilities/retrieval/model.py
capabilities/context/model.py
capabilities/system_health/model.py
entrypoints/native_agent/model.py
shared/extensions.py
```

Do not create one file per entity unless a file grows too large.

## Common concepts

Capability-local model files should define small concepts close to their owner:

- relationship evidence refs belong in Relationship Network;
- time helpers/value objects belong with the capability that first needs them;
- external driver contracts belong in `shared/contracts/` only when they are standard-library-only and cross-capability.

`shared/` must not become a garbage bin or a new `core/`.

## Rich model rules

Capability objects must include behavior when local to the concept:

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

Capability modules may use shared contracts only when necessary.

Prefer:

- capability-local policies for pure rules;
- command entrypoints for workflows;
- shared contracts for abstract external capabilities;
- state/retrieval/native agent entrypoints for implementation ownership.

## Acceptance

- capability files contain domain behavior, not just dataclasses.
- capability modules do not import `cli` or old layer-first packages.
- shared contract imports are minimal and justified.
- retired terms are not present as active entity names.
