# Dependency Rules

## Layer overview

```text
entrypoints -> commands

commands -> state
commands -> protocol
commands -> capabilities
commands -> shared

protocol -> state
protocol -> capabilities/composition

capability modules -> shared
capability modules -> state when persistence is needed

state -> shared
shared/contracts -> standard library only
```

Old layer-first packages are not active source packages. Do not restore them as compatibility layers.

## Entry Points

`entrypoints/` contains external adapters such as CLI and Native Agent Entry.

Rules:

1. Entry points parse external input or render native Agent entry files.
2. Entry points call `commands`.
3. Entry points format adapter-specific output and exit codes.
4. Entry points must not import state, storage, retrieval, indexing, runtime internals, or capability implementation details directly.

## Commands

`commands/` owns application-level entrypoints.

Rules:

1. Commands coordinate the Agent Protocol runtime and capabilities.
2. Commands may call capability public modules.
3. Commands should not implement SQL, focus resolution, lease policy, retrieval scoring, release policy internals, or context rendering internals.

## Protocol

`protocol/` is the Agent Protocol runtime control layer.

Rules:

1. Protocol implements sync, commit, focus resolution, lease validation, idempotency, response guidance, recovery, and projection routing.
2. Protocol may call `capabilities/composition` and `state/`.
3. Protocol must not import `cli/`.
4. Protocol does not own Task, Handoff, Asset, Relationship, Release, Retrieval, or Context facts.

## Capability Modules

Capability modules own local models and operations:

```text
capabilities/composition/
capabilities/work/
capabilities/assets/
capabilities/relationships/
capabilities/retrieval/
capabilities/context/
capabilities/release/
capabilities/handoff/
capabilities/system_health/
```

Rules:

1. Models stay local to the owning capability unless they are stable cross-capability primitives.
2. Retrieval consumes relationship signals but does not own relationship truth.
3. Context consumes retrieval output but does not own durable work facts.
4. Release filters and sanitizes protected content but does not own retrieval indexes.
5. Handoff owns derived transfer packages, not durable Work truth.
6. System Health owns doctor and release validation checks.
7. Capability modules must not import `protocol/`.

## State

`state/` owns managed state infrastructure.

Rules:

1. State may define SQLite schema and runtime paths.
2. State must not implement Agent Protocol policy.
3. State must not import `protocol/`, `commands/`, or `entrypoints/`.

## Shared

`shared/` owns only small stable primitives and standard-library-only contracts.

Rules:

1. `shared/contracts/` must not import project modules.
2. `shared/` must not become a new `core/`.
3. Capability-specific policy and behavior should stay with the owning capability.

## Import check

Tests must prevent the most dangerous violations:

- CLI bypassing `commands`.
- `shared/contracts` importing project modules.
- old layer-first package directories reappearing.
- capability modules importing `protocol/` or CLI.
- state importing protocol, commands, or CLI.
