# Engineering Structure

## Design decision

Use DDD only for strategic domain clarity. Source code is command-first, capability-owned, and shared-minimal.

Docs remain domain-language-first. Code should show the executable path first, then the capability that owns each behavior.

The active lightweight structure is:

```text
src/ai_workroot/
  cli/
  commands/
  state/
  work/
  assets/
  relationships/
  retrieval/
  context/
  release/
  agent_entry/
  diagnostics/
  shared/
  templates/
```

Old layer-first packages are removed from the active source tree. Do not restore them as import compatibility layers.

## Migration status

`src/ai_workroot/` is the active architecture target. New Clean Workroot behavior should land in `commands/` or the owning capability module.

`scripts/` is support-only and no longer carries active Clean Workroot product implementation:

```text
scripts/
  dev/                  developer, release, review, and smoke helpers
```

Runnable legacy Public Seed compatibility is removed from active paths. Old source remains inspectable only as non-runnable history under `docs/history/public-seed/code-archive/`.

## Module responsibilities

### `cli/`

Terminal adapter only.

Rules:

- Parse terminal input.
- Call `commands/`.
- Format terminal output and return exit codes.
- Do not call storage, retrieval, state, release, context, or diagnostics internals directly.

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
```

Rules:

- Coordinate capability modules.
- Express primary executable paths.
- Keep SQL, rendering algorithms, release policy, and template mechanics in capability modules.
- Be reusable from CLI, tests, future API/MCP/GUI adapters, and automation.

### `state/`

Managed state support.

Owns:

- `AI_WORKROOT_HOME` resolution and directory validation.
- WorkrootEnvironment config.
- global registry and directory bindings.
- JSONL helpers.
- SQLite schema initialization and verification.
- migrations and file locks.

Rules:

- Do not own Context Control, Retrieval, Release Control, Handoff, or Work facts.
- Do not introduce ORM or one-repository-per-table structure.
- SQLite schema changes remain explicitly scoped and tested.

### `work/`

Durable work facts and time events.

Owns:

- Task.
- AgentRun.
- WorkAction.
- WorkCheckpoint.
- InvalidationRecord.
- Handoff records as durable work facts.
- TimeEvent runtime operations.

### `assets/`

Asset metadata, lifecycle, publication, and asset runtime operations.

### `relationships/`

Canonical Relationship Network truth and relationship runtime operations.

Retrieval may consume relationship signals, but relationship truth is owned here.

### `retrieval/`

Indexing, FTS, candidate providers, recall hints, release-aware retrieval filters, and global index read models.

Retrieval finds candidates. It does not decide final context package structure and does not own relationship truth.

### `context/`

Context package building, selection, budget handling, rendering, debug trace, and diagnostic logging.

Context consumes retrieval output and release filters. It does not own durable work truth.

### `release/`

Release Control models and authoring operations.

Owns release, quiet/archive semantics where present, tombstone, redaction, deletion overlays, and strict release-derived index sanitization.

### `agent_entry/`

Native Agent Entry templates, managed blocks, validation, and permission hints.

AI Workroot is not an agent runtime; this package only owns the entry files that let agents enter a Workroot safely.

### `diagnostics/`

Doctor, release surface validation, health models, and actionable diagnostic reporting.

### `shared/`

Small shared primitives and standard-library-only contracts.

Allowed:

```text
shared/model.py
shared/extensions.py
shared/contracts/
```

Rules:

- Shared code must be stable and cross-capability.
- Do not move capability-specific policy, models, or operations here.
- `shared/contracts/` must not import project modules.

### `templates/`

Packaged templates used by runtime capabilities such as Native Agent Entry.

## Dependency rules

```text
cli
  -> commands

commands
  -> state
  -> work
  -> assets
  -> relationships
  -> retrieval
  -> context
  -> release
  -> agent_entry
  -> diagnostics
  -> shared

capability modules
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
cli -> command implementation internals below commands/
shared -> capability modules
state -> commands or cli
retrieval owns canonical relationship truth
context owns durable work facts
release owns retrieval indexes
agent_entry owns durable Workroot truth
```

## Why not pure DDD directories

Pure DDD directories are heavier and less obvious for open-source contributors and AI coding agents. The project uses DDD strategically for language and constraints, while implementation is organized by executable commands and owning capabilities.
