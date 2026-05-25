# Dependency Rules

## Layer overview

```text
cli -> commands

commands -> state
commands -> work/assets/relationships/retrieval/context/release/agent_entry/diagnostics
commands -> shared

capability modules -> shared
capability modules -> state when persistence is needed

state -> shared
shared/contracts -> standard library only
```

Old layer-first packages are not active source packages. Do not restore them as compatibility layers.

## CLI

`cli/` is the terminal adapter.

Rules:

1. CLI parses arguments.
2. CLI calls `commands`.
3. CLI formats terminal output and exit codes.
4. CLI must not import state, storage, retrieval, indexing, runtime internals, or capability implementation details directly.

## Commands

`commands/` owns application-level entrypoints.

Rules:

1. Commands coordinate capabilities.
2. Commands may call capability public modules.
3. Commands should not implement SQL, retrieval scoring, release policy internals, or context rendering internals.

## Capability Modules

Capability modules own local models and operations:

```text
state/
work/
assets/
relationships/
retrieval/
context/
release/
agent_entry/
diagnostics/
```

Rules:

1. Models stay local to the owning capability unless they are stable cross-capability primitives.
2. Retrieval consumes relationship signals but does not own relationship truth.
3. Context consumes retrieval output but does not own durable work facts.
4. Release filters and sanitizes protected content but does not own retrieval indexes.
5. Agent Entry generates entry files but is not an agent runtime.

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
- capability modules importing CLI.
- state importing commands or CLI.
