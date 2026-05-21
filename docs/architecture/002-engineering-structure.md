# Engineering Structure

## Design decision

Use DDD only for strategic domain clarity. Do not implement a heavyweight DDD directory tree.

Use this lightweight structure:

```text
src/ai_workroot/
  core/
  contracts/
  runtime/
  storage/
  indexing/
  agent/
  cli/
  resources/
```

## Module responsibilities

## Migration status

`src/ai_workroot/` is the active architecture target for 0.9.530. New Clean Workroot behavior should land here unless a change is explicitly preserving legacy compatibility.

`scripts/` is support-only and no longer carries active Clean Workroot product implementation:

```text
scripts/
  dev/                  developer, release, review, and smoke helpers
  compat/               short wrappers that delegate to src/ai_workroot
  legacy/public_seed/   quarantined Public Seed compatibility entry points
```

Old Public Seed capabilities remain callable where compatibility tests require
them, but new Clean Workroot domain logic must land under `src/ai_workroot/`.

When touching a capability that exists in both places:

- prefer the `src/ai_workroot/` package for new Clean Workroot runtime behavior;
- keep `scripts/` changes limited to developer helpers, compatibility wrappers, and legacy quarantine;
- add tests that make the intended active path explicit;
- do not hard-delete legacy behavior unless the matching capability is covered in `src/ai_workroot/` and Compatibility Removal has been approved.

### `core/`

Core concepts, behavior, value objects, policies, lightweight events.

MVP layout:

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

Rules:

- Keep files by domain area, not one class per file.
- Core may use contracts only when necessary.
- Core must not import storage/indexing/agent/cli/runtime.
- Core entities are not property bags. They must hold local behavior and invariants.

### `contracts/`

Protocol layer. This is the ports layer of the architecture, but the project uses the friendlier name `contracts`.

MVP files:

```text
contracts/storage.py
contracts/retrieval.py
contracts/filesystem.py
contracts/git.py
contracts/templates.py
contracts/events.py
contracts/clock.py
```

Rules:

- Contracts must not import core.
- Contracts must not import runtime/storage/indexing/agent/cli.
- Contracts should define protocol DTOs using standard library types.
- Storage/indexing/agent adapters implement contracts.

### `runtime/`

Application runtime and orchestration.

MVP files:

```text
runtime/container.py
runtime/unit_of_work.py
runtime/environment.py
runtime/bootstrap.py
runtime/workroot.py
runtime/context.py
runtime/assets.py
runtime/release.py
runtime/relationships.py
runtime/indexing.py
runtime/doctor.py
runtime/migrations.py
```

Rules:

- Runtime wires core + contracts + adapters.
- Runtime owns transaction boundaries and workflow orchestration.
- Runtime is not the retired `.workroot/runtime` directory.

### `storage/`

Persistence implementations.

```text
storage/sqlite/
storage/jsonl/
storage/filesystem/
```

Rules:

- Storage implements contracts.
- Storage must not contain business decisions.
- Storage may map between DTOs and persisted rows.

### `indexing/`

Indexing/projection/retrieval provider implementations.

```text
indexing/catalog.py
indexing/pipeline.py
indexing/refresh.py
indexing/invalidation.py
indexing/health.py
indexing/global_indexes.py
indexing/candidates.py
indexing/fts.py
indexing/relationship_projection.py
indexing/providers/
```

Rules:

- Indexing implements retrieval/index contracts.
- Indexing maintains derived read models and projections.
- Relationship truth is not owned by indexing.
- Vector/search adapters are reserved interfaces only in 0.9.530.

### `agent/`

Agent interface implementation.

```text
agent/native_entry.py
agent/managed_block.py
agent/templates.py
agent/startup.py
agent/permissions.py
agent/adapters/
```

Rules:

- Native Agent Entry generation is here.
- Agent adapter protocol logic is here.
- Agent does not own Context Control decisions.

### `cli/`

Command interface.

```text
cli/main.py
cli/commands/init.py
cli/commands/list.py
cli/commands/status.py
cli/commands/context.py
cli/commands/doctor.py
cli/commands/bootstrap_dev.py
```

Rules:

- CLI is thin.
- CLI calls runtime.
- CLI does not contain business logic.

## Dependency rules

```text
cli -> runtime
runtime -> core
runtime -> contracts
storage -> contracts
indexing -> contracts
agent -> contracts
agent -> runtime where needed
core -> contracts only when necessary
contracts -> standard library only
```

Forbidden:

```text
contracts -> core
contracts -> runtime
contracts -> storage
contracts -> indexing
contracts -> agent
core -> storage
core -> indexing
core -> agent
core -> cli
cli -> storage directly
cli -> indexing directly
```

## Why not pure DDD directories

Pure DDD directories are heavier and less obvious for open-source contributors. The project uses DDD strategically, but implementation is capability-based:

- Core concepts in `core`.
- Protocols in `contracts`.
- Orchestration in `runtime`.
- Persistence in `storage`.
- Indexing/projections in `indexing`.
- Agent protocols in `agent`.
- Commands in `cli`.

This keeps the project simple without losing architectural rigor.
