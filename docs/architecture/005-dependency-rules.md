# Dependency Rules

## Layer overview

```text
cli -> runtime
runtime -> core + contracts
core -> contracts only when necessary
storage -> contracts
indexing -> contracts (+ core for interpretation where unavoidable)
agent -> contracts + resources (+ runtime for workflows)
contracts -> standard library only
```

## Contracts

`contracts/` is the protocol layer.

Rules:

1. `contracts` must not import `core`.
2. `contracts` must not import `runtime`.
3. `contracts` must not import `storage`, `indexing`, `agent`, or `cli`.
4. `contracts` may use dataclasses, typing, protocols, enums, and standard library only.
5. Port DTOs may duplicate some fields from core entities to preserve independence.

## Core

`core/` owns domain language and core behavior.

Rules:

1. Core entities are not property bags.
2. Core should contain behavior, invariants, lifecycle transitions, and policies.
3. Core must not import storage/indexing/agent/cli/runtime.
4. Core may import contracts only when a core service needs an abstract capability.
5. Entities should usually not hold contract implementations as long-lived fields.
6. For external capabilities, prefer core services or runtime orchestration.

## Runtime

`runtime/` orchestrates workflows.

Rules:

1. Runtime loads data, invokes core behavior, calls contracts, coordinates transactions, and persists results.
2. Runtime must not contain low-level storage implementation.
3. Runtime must not hide domain rules that belong in core.

## Storage

`storage/` implements persistence contracts.

Rules:

1. Storage does not decide domain policy.
2. Storage does not publish assets.
3. Storage does not decide context selection.
4. Storage may map port DTOs to SQLite/JSONL rows.

## Indexing

`indexing/` implements index/retrieval contracts and projection pipelines.

Rules:

1. Indexing owns derived read models and provider implementations.
2. Indexing does not own canonical Relationship truth.
3. Indexing must observe Release Control redaction/deletion rules.
4. Vector/search adapters are reserved only in 0.9.530; no actual dependency.

## Agent

`agent/` implements Agent Interface capabilities.

Rules:

1. Agent may generate Native Agent Entry from templates.
2. Agent does not own Context Control decisions.
3. Agent must not expose state paths or private IDs in user entry files.

## CLI

`cli/` is thin.

Rules:

1. CLI parses commands.
2. CLI calls runtime.
3. CLI formats output.
4. CLI does not implement core logic.

## Import check

Codex must add a lightweight import-boundary check or test that prevents the most dangerous violations:

- contracts importing core/runtime/storage/indexing/agent/cli
- core importing storage/indexing/agent/cli
- cli importing storage directly
