# Engineering Structure

## Design Decision

Use DDD only for strategic domain clarity. Source code is entrypoint-adapted, command-first, capability-owned, and shared-minimal.

Docs remain domain-language-first. Code should show the executable path first, then the capability that owns each behavior.

The active lightweight structure is:

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
    work/
    assets/
    relationships/
    retrieval/
    context/
    release/
    handoff/
    system_health/
  state/
  shared/
```

Old layer-first packages and old top-level capability packages are removed from the active source tree. Do not restore them as import compatibility layers.

## Migration Status

`src/ai_workroot/` is the active architecture target. New Clean Workroot behavior should land in `commands/`, `protocol/`, or the owning capability module.

`scripts/` is support-only and no longer carries active Clean Workroot product implementation:

```text
scripts/
  dev/                  developer, release, review, and smoke helpers
```

Runnable legacy Public Seed compatibility is removed from active paths. Old source remains inspectable only as non-runnable history under `docs/history/public-seed/code-archive/`.

## Module Responsibilities

### `entrypoints/`

External adapters only.

Rules:

- Parse terminal or transport-specific input.
- Render Native Agent Entry files.
- Call `commands/`.
- Format adapter-specific output and return exit codes.
- Do not call storage, retrieval, state, release, context, system health, or capability internals directly.

### `commands/`

Application-level command entrypoints.

Current command modules:

```text
commands/init_workroot.py
commands/list_workroots.py
commands/show_status.py
commands/build_context.py
commands/run_doctor.py
commands/bootstrap_dev.py
commands/agent_exchange.py
```

Rules:

- Coordinate protocol and capability modules.
- Express primary executable paths.
- Keep SQL, rendering algorithms, release policy, and template mechanics in lower owning modules.
- Be reusable from CLI, tests, future API/MCP/GUI adapters, and automation.

### `protocol/`

Agent-facing application control layer for Workroot Agent Protocol.

Owns:

- sync and commit orchestration.
- work-signal normalization and focus resolution.
- lease validation, commit idempotency, and response replay.
- model-facing response construction.
- projection routing into `capabilities/composition`.

Rules:

- May call `capabilities/composition` and managed state infrastructure.
- Must not own Task, Handoff, Context, Retrieval, Relationship, Release, or Asset truth.
- Must not expose state infrastructure details as ordinary model guidance.
- Capability modules must not import `protocol/`.

### `capabilities/composition/`

Cross-capability composition.

Owns:

- Protocol event projection into multiple capability facts.
- Transactionally consistent Task, TaskRun, TaskItem, Asset, Relationship, Retrieval, and Handoff projection effects.
- Durable facts derived from accepted protocol events and protocol commit batches.

Rules:

- Do not parse CLI input.
- Do not render protocol packets.
- Do not own lease or idempotency policy.
- Do not become a general workflow layer.
- Keep `projections.py` as one file until use-case complexity requires a semantic split.

### `state/`

Managed state support.

Owns:

- `AI_WORKROOT_HOME` resolution and directory validation.
- WorkrootEnvironment config.
- global registry and directory bindings.
- JSONL helpers.
- SQLite schema initialization and verification.
- state version helpers.
- migrations and file locks.

Rules:

- Do not own Context Control, Retrieval, Release Control, Handoff, or Work facts.
- Do not introduce ORM or one-repository-per-table structure.
- SQLite schema changes remain explicitly scoped and tested.

### `capabilities/work/`

Durable work facts and time events.

Owns Task, TaskRun, TaskItem, AgentRun, WorkAction, WorkCheckpoint, InvalidationRecord, and TimeEvent runtime operations.

### `capabilities/handoff/`

Derived transfer packages for the next agent, tool, session, human, or future self.

### `capabilities/assets/`

Asset metadata, lifecycle, publication, and asset runtime operations.

### `capabilities/relationships/`

Canonical Relationship Network truth and relationship runtime operations.

Retrieval may consume relationship signals, but relationship truth is owned here.

### `capabilities/retrieval/`

Indexing, FTS, candidate providers, recall hints, and global index read models.

Retrieval finds candidates. It does not decide final context package structure, release filtering, or relationship truth.

### `capabilities/context/`

Context package building, selection, budget handling, rendering, debug trace, and diagnostic logging.

Context consumes retrieval output and release filters. It does not own durable work truth. Context does not import `protocol/`; protocol startup guidance is built above context and injected into rendering.

### `capabilities/release/`

Release Control models and authoring operations.

Owns release, quiet/archive semantics where present, tombstone, redaction, deletion overlays, release target resolution, release filtering, and strict release-derived index sanitization.

### `capabilities/system_health/`

Doctor, release surface validation, health models, and actionable diagnostic reporting.

### `shared/`

Small shared primitives and standard-library-only contracts.

Allowed:

```text
shared/extensions.py
shared/contracts/
```

Rules:

- Shared code must be stable, minimal, and cross-capability.
- Do not move capability-specific policy, models, or operations here.
- `shared/contracts/` must not import project modules.

## Dependency Rules

```text
entrypoints
  -> commands

commands
  -> state
  -> protocol
  -> capabilities
  -> shared

protocol
  -> state
  -> capabilities/composition

capabilities/composition
  -> capability packages
  -> state
  -> shared

capability packages
  -> shared
  -> state when persistence is needed
  -> other capabilities only when consuming their public capability output

state
  -> shared

shared/contracts
  -> standard library only
```

Forbidden:

```text
entrypoints -> implementation internals below commands/
shared -> capability modules
state -> commands or entrypoints
capabilities -> protocol
retrieval owns canonical relationship truth
```
