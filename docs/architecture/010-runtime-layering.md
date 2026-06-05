# Runtime Layering

## Purpose

AI Workroot 0.9.531 adds the Agent Protocol and Task Continuity foundation with lightweight physical layer directories. This document defines how to read the current source tree.

The source layout is a lightweight layered, capability-owned architecture:

```text
Entry / Client Layer
  entrypoints/
    cli/
    native_agent/
      templates/

Command / Use-case Adapter Layer
  commands/

Protocol Runtime Layer
  protocol/

Capability Layer
  capabilities/
    composition/
    work/
    handoff/
    context/
    retrieval/
    release/
    relationships/
    assets/
    system_health/

State / Infrastructure Layer
  state/

Shared Kernel
  shared/
```

The layout is intentionally not a DDD package tree. DDD remains useful for strategic language, but source code is organized around executable entrypoints, protocol runtime control, owning capabilities, managed state, and a tiny shared kernel.

## Layer Responsibilities

### Entry / Client Layer

`entrypoints/` exposes Workroot to users, agents, and future transport adapters.

Rules:

- Parse external inputs and route to command modules.
- Generate thin native agent entry files.
- Do not own protocol events, Task facts, TaskRun state, release policy, or retrieval logic.

### Command / Use-case Adapter Layer

`commands/` adapts CLI arguments, JSON files, stdin, and future transport inputs into internal requests.

Rules:

- Call the protocol runtime or the owning capability module.
- Keep stdout, JSON, and markdown formatting at the command boundary.
- Do not implement focus resolution, lease policy, idempotency, or Task projection logic.

### Protocol Runtime Layer

`protocol/` is the runtime implementation of Workroot Agent Protocol. It sits below command adapters and above capability modules.

It owns:

- `sync` and `commit` orchestration.
- Work-signal normalization and semantic focus resolution.
- Lease minting and validation.
- Commit idempotency and response replay.
- Recorded/projected/accepted result semantics.
- Non-blocking recovery responses.
- Projection routing into capability composition.
- Model-facing response construction.

It does not own:

- Task, TaskRun, Handoff, Asset, Relationship, Release, Retrieval, or Context facts.
- SQLite layout or migration policy.
- Full context recall strategy.
- Raw chat fragment persistence.

### Capability Layer

Capability modules own their own local models, operations, readers, policies, and tests.

Examples:

- `capabilities/composition/` owns cross-capability projection orchestration.
- `capabilities/work/` owns Task, TaskRun, TaskItem, work lifecycle, and time events.
- `capabilities/handoff/` owns handoff package creation and lookup.
- `capabilities/context/` owns context package building, budget handling, filtering, rendering, and diagnostics.
- `capabilities/retrieval/` owns candidate lookup, recall hints, FTS, and global read indexes.
- `capabilities/release/` owns tombstone, redaction, deletion, release filtering, and release target resolution.
- `capabilities/relationships/` owns Relationship Network truth.
- `capabilities/assets/` owns asset identity, metadata, lifecycle, and publication metadata.
- `capabilities/system_health/` owns doctor and release validation checks.

Capability modules must not depend on `protocol/`. The Agent Protocol is an application control layer above them.

`capabilities/composition/projections.py` is intentionally a single cross-capability projection file for now. If it becomes too large,
split by use-case semantics rather than adding mechanical `projections.py` files to every capability.

### State / Infrastructure Layer

`state/` owns managed state infrastructure:

- `AI_WORKROOT_HOME` layout.
- Workroot registry and environment config.
- SQLite schema initialization and migrations.
- Runtime view paths.
- Locks, JSONL helpers, and state-directory validation.

`state/` may define schema for protocol and capability tables, but it must not implement protocol policy or capability state machines.

### Shared Kernel

`shared/` is a tiny shared kernel for stable primitives and standard-library-only contracts.

Rules:

- Keep it small.
- Do not add capability models, protocol policy, runtime orchestration, or business services.
- Prefer the owning capability module when a helper has capability meaning.

## Protocol Spec Objects Versus Runtime Implementation

`protocol/` contains both protocol spec objects and runtime implementation because both are part of the Workroot Agent Protocol package.

Spec objects:

```text
protocol/model.py
protocol/events.py
```

These define request, response, and event shapes that should remain relatively stable.

Runtime implementation:

```text
protocol/controller.py
protocol/focus.py
protocol/lease.py
protocol/response.py
protocol/recovery.py
protocol/work_signal.py
protocol/projections.py
```

These implement the live sync/commit behavior and may evolve as the product matures.

Do not split `protocol_spec/` and `protocol_runtime/` into separate top-level packages in 0.9.531. The internal distinction is enough for this release line.

## Dependency Direction

Allowed primary direction:

```text
entrypoints -> commands
commands -> protocol
commands -> capability modules
commands -> state
protocol -> capabilities/composition
protocol -> state
capability modules -> state
shared/contracts -> standard library only
```

Forbidden direction:

```text
work -> protocol
handoff -> protocol
state -> protocol
release -> protocol
retrieval -> protocol
relationships -> protocol
assets -> protocol
shared -> protocol
shared -> capability modules
```

`context -> protocol` is not allowed. Protocol startup guidance is built above context and injected into context rendering.

## Current 0.9.531 Position

The 0.9.531 line is an Agent Protocol and Task Continuity foundation release. It establishes:

- Agent-facing sync/commit protocol flow.
- Task, TaskRun, TaskItem, handoff, asset, and decision projections through protocol events.
- Commit-batch idempotency.
- Non-blocking degraded behavior.
- Runtime views derived from SQLite facts.

It does not yet deliver the full layered L1/L2/L3 context recall strategy. That should be designed as a later context strategy upgrade, not folded into this layering cleanup.
