# Source Layering and Capability Composition Design

## Purpose

This design upgrades the AI Workroot source layout so the package tree matches the current architecture language:
entrypoints adapt external tools, commands adapt use cases, protocol controls Agent exchange, capabilities own Workroot behavior,
composition coordinates cross-capability projections, state owns managed infrastructure, and shared remains a tiny kernel.

This is a structural cleanup, not a product feature expansion. It must keep behavior stable, avoid compatibility wrappers, and keep
the system easier to evolve toward richer Agent protocol and layered context recall work.

## Current Problem

The current source tree is still physically flat:

```text
ai_workroot/
  cli/
  agent_entry/
  templates/
  commands/
  protocol/
  work/
  assets/
  relationships/
  retrieval/
  context/
  release/
  handoff/
  diagnostics/
  state/
  shared/
```

This creates three architectural mismatches:

1. `cli`, `agent_entry`, and `templates` are all entrypoint concerns, but they are separate top-level peers.
2. Capability packages are top-level peers, even though the docs already describe a capability layer.
3. `protocol/projections.py` owns a large cross-capability projection implementation, so protocol has too much capability fact knowledge.

The `diagnostics` name is also too implementation-oriented. The package actually owns System Health checks, not arbitrary diagnostic output.

## Target Source Layout

```text
src/ai_workroot/
  entrypoints/
    cli/
    native_agent/
      templates/

  commands/

  protocol/

  capabilities/
    composition/
      projections.py

    work/
      model.py
      operations.py
      time.py

    assets/
      model.py
      operations.py

    handoff/
      model.py
      operations.py

    relationships/
      model.py
      operations.py

    retrieval/
      model.py
      global_indexes.py
      providers/

    context/
      model.py
      control.py
      builder.py

    release/
      model.py
      operations.py
      evaluation.py
      filter.py

    system_health/
      model.py
      doctor.py
      release_validation.py

  state/
  shared/
```

Future external adapters, such as MCP, belong under `entrypoints/`.

## Layer Responsibilities

### Entry Points

`entrypoints/` exposes Workroot to external tools and Agent-native files.

Responsibilities:

- Parse external process inputs.
- Render or update native Agent entry files.
- Delegate into `commands/`.

Non-responsibilities:

- Protocol state.
- Task facts.
- Cross-capability projections.
- SQLite business writes.

### Commands

`commands/` is the use-case adapter layer.

Responsibilities:

- Convert entrypoint input into internal request objects.
- Call `protocol`, `capabilities`, or `state`.
- Format command-facing output.

Non-responsibilities:

- Protocol lease or idempotency policy.
- Task continuity state machines.
- Context recall strategy.
- Cross-capability projection logic.

### Protocol

`protocol/` controls the Workroot Agent Protocol.

Responsibilities:

- `sync` and `commit` orchestration.
- Lease minting and validation.
- Commit idempotency.
- Work signal normalization.
- Focus resolution.
- Model-facing response and private packet rendering.
- Non-blocking degraded and recovery behavior.

Protocol should call `capabilities.composition.projections.apply_projection()` for durable event projection. It must not own the
SQL details for Task, Asset, Handoff, Relationship, Retrieval, or other capability facts.

### Capabilities

`capabilities/` contains Workroot behavior modules.

Each capability owns its local language, models, operations, policies, and tests. The default file split is intentionally light:

- `model.py`: pure concepts, dataclasses, status constants, and local state transitions.
- `operations.py`: runtime operations with side effects such as SQLite writes, file writes, and index invalidation.

Do not add heavy DDD folders such as `domain/`, `entities/`, `repositories/`, or `services/`.

### Capability Composition

`capabilities/composition/` is the top of the capability layer.

It exists because some use cases are inherently cross-capability. Protocol event projection is the first such use case: one commit may
create or update Task, TaskRun, TaskItem, Handoff, Asset, Relationship, Retrieval candidate, and runtime-view-invalidating facts together.

For this release, keep composition simple:

```text
capabilities/composition/projections.py
```

Do not add one `projections.py` file inside every capability package in this pass. That would create many same-named files and increase
navigation cost before the complexity requires it.

Composition responsibilities:

- Apply protocol event projections into capability facts.
- Keep cross-capability writes transactionally consistent.
- Return projection effects back to protocol.

Composition non-responsibilities:

- CLI parsing.
- Protocol packet rendering.
- Lease or idempotency policy.
- Schema migration.
- Layered context recall strategy.
- New domain entities.

If `composition/projections.py` becomes too large later, split by use-case semantics, not by mechanical capability folders, for example:
`task_continuity.py`, `asset_capture.py`, `decision_capture.py`, or `handoff_capture.py`.

### State

`state/` owns managed infrastructure:

- Workroot registry.
- Environment config.
- SQLite schema and migrations.
- Runtime view paths.
- Locks and JSONL helpers.

State may define schema, but it must not implement protocol policy or capability state machines.

### Shared

`shared/` remains a tiny kernel. It may contain stable, standard-library-only contracts and primitives. It must not become a new `core/`
package.

## Dependency Rules

Allowed primary direction:

```text
entrypoints -> commands
commands -> protocol / capabilities / state
protocol -> capabilities.composition / state
capabilities.composition -> capabilities.* / state / shared
capabilities.* -> state / shared
state -> shared
shared -> standard library only
```

Forbidden direction:

```text
capabilities -> protocol
state -> protocol
protocol -> entrypoints
commands -> entrypoints
shared -> capabilities
```

The current `context/builder.py -> protocol` dependency must be removed during this migration. Context should accept protocol guidance as
input from the command/protocol layer instead of importing protocol directly.

## Naming Decisions

`diagnostics` becomes `capabilities/system_health`.

Reason:

- `diagnostics` names a technical output style.
- `system_health` names the capability.
- The code already describes this behavior as System Health doctor runtime flow.

This keeps capability names at the same abstraction level as `work`, `assets`, `retrieval`, `context`, `release`, `handoff`, and
`relationships`.

## Compatibility Policy

No compatibility wrapper packages will be kept.

Old layer-first import paths should be updated directly to `ai_workroot.entrypoints.*` or `ai_workroot.capabilities.*`
paths. Tests and docs must follow the new structure.

## Documentation and Test Contract Updates

Update public and contract-facing docs so they describe the new source layout:

- `README.md`
- `docs/architecture.md`
- `docs/workroot-system-design.md`
- `docs/kernel-implementation-specification.md`
- `docs/architecture/010-runtime-layering.md`
- `docs/architecture/002-engineering-structure.md`
- `docs/architecture/005-dependency-rules.md`
- `docs/validation/acceptance-checklist.md`
- `docs/releases/0.9.531.md`

Update source layout, import boundary, release surface, and current-docs contract tests to enforce the new structure.

## Validation

The migration is successful when:

- `python3 -m unittest tests.unit.test_import_boundaries -v` passes.
- `python3 -m unittest tests.unit.test_source_layout_imports -v` passes.
- `python3 -m unittest tests.contracts.test_current_docs_contract -v` passes.
- `python3 -m unittest tests.contracts.test_release_surface_contract -v` passes.
- `scripts/dev/validate-release.sh` passes.
- Full unittest discovery passes.

No remote push is part of this design.
