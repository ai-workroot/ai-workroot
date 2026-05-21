# 0.9.530 Scripts-to-Source Migration Detailed Design

## Status

Draft checkpoint for the next implementation stage on `feat/0.9.530-clean-workroot-domain-reset`.

Compatibility correction: the current implementation stage is package ownership. This phase finishes package ownership while preserving existing script and legacy CLI compatibility. The Compatibility Removal phase removes or narrows compatibility later, with a separate branch/version and separate approval.

## Design Principle

Migrate by behavior and contracts, not by mechanically moving files.

The large scripts contain useful behavior, test history, and edge-case handling. The package already contains Clean Workroot foundations. The migration must combine them without turning `src/ai_workroot/` into a copy of the old Public Seed shape.

## Current Implementation Inventory

### Active package foundations already present

```text
src/ai_workroot/agent/native_entry.py
src/ai_workroot/cli/main.py
src/ai_workroot/contracts/*.py
src/ai_workroot/core/*.py
src/ai_workroot/indexing/providers/*.py
src/ai_workroot/runtime/bootstrap.py
src/ai_workroot/runtime/context.py
src/ai_workroot/runtime/doctor.py
src/ai_workroot/runtime/environment.py
src/ai_workroot/runtime/init.py
src/ai_workroot/runtime/registry.py
src/ai_workroot/storage/*.py
```

These files are the active target, but several are still thin compared with legacy behavior.

### Legacy implementation still carrying mature behavior

```text
scripts/workroot_client.py        Work/task/run/action/artifact/batch/session/continue behavior
scripts/workroot_context.py       mature Context Guide selection, budgets, debug trace
scripts/workroot_sqlite.py        older SQLite schema helper
scripts/workroot_state.py         older managed state and registry initialization
scripts/workroot_indexing.py      file chunking and FTS indexing
scripts/workroot_candidates.py    materialized context candidate provider
scripts/workroot_doctor.py        old doctor checks
scripts/workroot_bootstrap.py     old bootstrap-dev implementation
scripts/workroot_cli.py           old command surface and hidden legacy commands
```

### Developer and historical helpers

```text
scripts/validate_kernel.py
scripts/add_registry_row.py
scripts/list_tasks.py
scripts/new_task.py
scripts/new_task_smoke.py
scripts/rebuild_sqlite.py
scripts/setup_workroot.py
scripts/update_usage_direction.py
scripts/upgrade_workroot.py
scripts/workroot_operation_manifest.py
```

These must be moved, wrapped, or labeled based on whether they are developer tools, legacy compatibility, or active package capabilities.

## Target Module Design

### CLI

Target files:

```text
src/ai_workroot/cli/main.py
src/ai_workroot/cli/commands/init.py
src/ai_workroot/cli/commands/list.py
src/ai_workroot/cli/commands/status.py
src/ai_workroot/cli/commands/context.py
src/ai_workroot/cli/commands/doctor.py
src/ai_workroot/cli/commands/bootstrap_dev.py
src/ai_workroot/cli/commands/legacy.py
```

Responsibilities:

- parse arguments;
- call runtime services;
- format text/JSON output;
- keep primary help limited to Clean Workroot commands;
- expose legacy commands only under `workroot legacy ...` or hidden compatibility.

Rules:

- no direct SQLite calls;
- no direct registry file writes;
- no business decisions;
- no Public Seed primary wording.

### Runtime

Target files:

```text
src/ai_workroot/runtime/environment.py
src/ai_workroot/runtime/init.py
src/ai_workroot/runtime/bootstrap.py
src/ai_workroot/runtime/work.py
src/ai_workroot/runtime/assets.py
src/ai_workroot/runtime/release.py
src/ai_workroot/runtime/relationships.py
src/ai_workroot/runtime/indexing.py
src/ai_workroot/runtime/context.py
src/ai_workroot/runtime/doctor.py
src/ai_workroot/runtime/migrations.py
src/ai_workroot/runtime/legacy.py
```

Responsibilities:

- coordinate workflows;
- load and save records through storage modules;
- enforce transaction boundaries;
- invoke core policies;
- call indexing invalidation/update hooks;
- persist diagnostics and traces.

### Core

Existing `core/*.py` files remain the concept home. They should gain behavior only when it is stable domain logic:

- ID validation;
- release-level ordering;
- context budget validation;
- Work lifecycle invariants;
- Asset lifecycle and publication rules;
- Relationship edge validation;
- Health severity and result merging.

Core must not import storage, indexing, runtime, agent, or CLI.

### Storage

Target files:

```text
src/ai_workroot/storage/sqlite.py
src/ai_workroot/storage/migrations.py
src/ai_workroot/storage/repositories.py
src/ai_workroot/storage/jsonl_registry.py
src/ai_workroot/storage/locks.py
src/ai_workroot/storage/filesystem.py
```

Responsibilities:

- initialize and migrate SQLite;
- expose small repository functions for canonical records;
- manage registry JSONL atomically;
- enforce registry-level file locks;
- provide backup/rollback primitives.

Storage does not decide whether something belongs in context. It only stores and retrieves.

### Indexing

Target files:

```text
src/ai_workroot/indexing/pipeline.py
src/ai_workroot/indexing/candidates.py
src/ai_workroot/indexing/fts.py
src/ai_workroot/indexing/global_indexes.py
src/ai_workroot/indexing/relationship_projection.py
src/ai_workroot/indexing/invalidation.py
src/ai_workroot/indexing/providers/*.py
```

Responsibilities:

- chunk supported text files;
- update FTS tables;
- maintain context candidate read models;
- maintain relationship traversal projections;
- maintain global management indexes;
- apply safety/release-aware filters for retrieval inputs.

Indexing owns derived read models, not canonical Work, Asset, Relationship, or Release truth.

### Agent

Target files:

```text
src/ai_workroot/agent/native_entry.py
src/ai_workroot/agent/managed_block.py
src/ai_workroot/agent/templates.py
src/ai_workroot/agent/startup.py
src/ai_workroot/agent/permissions.py
```

Responsibilities:

- render and sync Native Agent Entry files;
- validate only the managed block;
- keep entry files short;
- avoid absolute managed-state path leakage;
- define permission hints without owning Context Control.

## Detailed Migration Steps

### Phase A: Baseline and checkbot

Input:

- current branch;
- existing validation commands;
- current script/package inventory.

Output:

- package release validator remains passing;
- checkbot command is documented and runnable;
- ignored local files do not affect release surface.

Validation:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

### Phase B: CLI and wrapper isolation

Changes:

- split `src/ai_workroot/cli/main.py` into command modules if it grows;
- make `scripts/workroot_cli.py` delegate Clean commands to package runtime;
- move hidden legacy seed commands under `workroot legacy ...` or preserve only as hidden adapters;
- keep package help free of Public Seed primary commands.

Acceptance:

- `python -m ai_workroot --help` shows only Clean Workroot primary commands;
- `scripts/workroot_cli.py init/context/doctor/bootstrap-dev` matches package behavior or delegates to it;
- legacy command tests live under `tests/legacy/` or clearly named legacy test files.

### Phase C: Storage and migrations

Changes:

- move old `workroot_sqlite.py` migration behavior into `storage/sqlite.py` and `storage/migrations.py`;
- ensure all canonical tables and projection tables are package-owned;
- add migration records for old DB shapes;
- keep per-Workroot DB scoping documented and tested;
- keep registry writes protected by locks.

Acceptance:

- old SQLite fixtures migrate;
- duplicate registry writes are concurrency safe;
- package storage tests replace script storage tests.

### Phase D: Work and Asset runtime

Changes:

- extract task/run/action/checkpoint/handoff/retrieval-card/invalidation/session/batch behavior from `workroot_client.py`;
- implement runtime service functions using core models and storage repositories;
- preserve atomic batch/rollback behavior;
- map artifact/decision/mind/knowledge outputs into Asset and Release Control terms.

Acceptance:

- no old Work capability is lost;
- package tests cover every row in the legacy capability preservation matrix;
- old script client becomes legacy adapter or wrapper.

### Phase E: Retrieval & Index Control

Changes:

- migrate text chunking, supported-file detection, content hash, FTS update, and search behavior into package indexing modules;
- keep candidate source flags and safety policies intact;
- ensure repository-level safety filtering is default;
- keep vector retrieval optional and unimplemented.

Acceptance:

- FTS and candidate tests run against package modules;
- safety-blocked candidates are excluded by default;
- debug traces record FTS fallback errors.

### Phase F: Context Control parity

Changes:

- migrate mature budget resolution, query expansion, candidate pool building, scoring, confidence, rendering, debug trace, and hard-limit enforcement from `workroot_context.py`;
- keep runtime orchestration in `runtime/context.py`;
- move token/budget/render helpers into smaller modules only where it reduces risk.

Acceptance:

- package context behavior has parity tests for FTS/query/relationship selection;
- token estimates do not badly undercount English, CJK, or code;
- rendered packages respect hard token limits;
- trace persistence and debug output remain explainable.

### Phase G: Release and Relationship migration

Changes:

- keep `ReleaseRecord.target_type/target_id` canonical;
- keep `context_candidates.source_type/source_id` as candidate source metadata;
- use `CandidateReleaseTargetResolver` for candidate, FTS, and relationship release evaluation;
- migrate graph wording and old graph projection behavior into Relationship Network modules.

Acceptance:

- Relationship Signals section contains only relation-backed signals;
- redacted/deleted targets do not leak through candidates, FTS, or relationships;
- tombstones remain visible as protected state, not raw deleted content.

### Phase H: System Health and validation

Changes:

- move release validation authority into package doctor/checkbot commands;
- keep `validate_kernel.py` as historical baseline until replaced;
- add release-surface checks for root tracked `AGENTS.md`, `CLAUDE.md`, `space/`, `.workroot/`, `.idea/`;
- add checkbot docs and scripts that do not tag or release.

Acceptance:

- `python -m ai_workroot doctor --release` is the primary package release validator;
- shell checkbot uses only temporary user directories for smoke;
- ignored local files do not fail release validation.

### Phase I: Test split and Public Seed quarantine

Changes:

- move legacy tests under `tests/legacy/` or rename them explicitly;
- preserve useful Public Seed fixtures under `tests/fixtures/` or `docs/history/`;
- remove active-root assumptions from current tests;
- update docs and acceptance checklists.

Acceptance:

- no current architecture test requires active root Public Seed layout;
- legacy tests still prove preserved behavior;
- package tests are authoritative for Clean Workroot.

## Compatibility Adapter Design

During migration, old scripts may use this rule:

```text
script command -> package runtime function -> package output
```

Only legacy-only commands may keep old implementations temporarily. Their help text must not appear in the primary Clean Workroot command list.

For Part 1, compatibility adapters are mandatory for old script entry points. A script can become a thin wrapper, but it must remain callable. Archiving a script under `docs/history/0.9.530/scripts/` preserves the old implementation snapshot only; it does not remove the live wrapper.

Examples:

- `scripts/bootstrap-dev.sh` remains a wrapper to `python -m ai_workroot bootstrap-dev`.
- `scripts/install.sh` remains a wrapper installer, not a full GUI/first-run installer.
- `scripts/workroot_cli.py init` delegates to `ai_workroot.cli.main`.
- `scripts/workroot_cli.py legacy task create` may call old compatibility code until `runtime/work.py` reaches parity.

## Test Design

### Package-first tests

Every migrated behavior gets a package test that imports from `ai_workroot.*`.

### Wrapper tests

Wrappers are tested only for delegation and syntax, not business behavior.

### Legacy tests

Legacy tests prove no capability was lost while migration is incomplete. They must not be used as evidence that active package behavior works.

### Negative tests

Required negative coverage:

- Clean Mode does not write managed state into user directory;
- redacted/deleted content does not enter ordinary context;
- safety-blocked candidates are excluded by default;
- root `AGENTS.md` / `CLAUDE.md` are not tracked;
- root `space/` / `.workroot/` are not active architecture;
- ignored `.idea/` does not fail release surface checks;
- legacy commands do not appear in primary package help.

## Rollback Design

Rollback is phase-based:

- revert the last migration commit;
- keep previous package and script paths intact;
- preserve old scripts until package replacement tests pass;
- back up SQLite before destructive schema migrations;
- never require real user directory mutation during rollback.

## Implementation Checkpoints

Suggested checkpoint commits:

1. `Design scripts-to-source migration completion`
2. `Isolate Clean CLI and legacy command wrappers`
3. `Move storage migrations into package`
4. `Migrate Work and Asset runtime capabilities`
5. `Migrate indexing and candidate providers`
6. `Complete Context Control package parity`
7. `Complete release and relationship migration`
8. `Move release validation into package checkbot`
9. `Split tests and quarantine Public Seed compatibility`

No checkpoint creates a tag or release.
