# 0.9.530 Scripts-to-Source Migration Architecture

## Status

Draft checkpoint for `feat/0.9.530-clean-workroot-domain-reset`.

This document extends the accepted 0.9.530 Clean Workroot architecture reset. It does not replace the core domain architecture. It defines how the remaining mature implementation in `scripts/` moves into `src/ai_workroot/` without capability loss.

Compatibility correction: the remaining migration is split into two parts. Part 1, the current branch target, moves implementation ownership into `src/ai_workroot/` while preserving old script and legacy CLI compatibility. Part 2, a later branch/version, removes or narrows compatibility after separate approval. Do not remove callable script compatibility while completing Part 1.

## Purpose

The current branch has established the Clean Workroot source layout and moved important 0.9.530 foundations into `src/ai_workroot/`. However, much of the mature product behavior still lives in Python scripts:

- old Work process commands and registries in `scripts/workroot_client.py`;
- old Context Guide behavior in `scripts/workroot_context.py`;
- old SQLite, state, path, doctor, indexing, bootstrap, and CLI helpers in `scripts/workroot_*.py`;
- historical first-use/profile/task helpers in smaller `scripts/*.py` files.

That state is acceptable as an intermediate checkpoint, but it is not the final architecture direction. Active Clean Workroot product logic must live under the package structure:

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

The goal is not to delete scripts quickly. The goal is to migrate capabilities safely, prove equivalent behavior with tests, and then reduce `scripts/` to wrappers, developer tooling, release validation, and explicitly legacy Public Seed compatibility.

## Architecture Goals

1. Make `src/ai_workroot/` the active implementation home for Clean Workroot behavior.
2. Preserve all valuable legacy capabilities until their replacements are implemented and tested.
3. Keep user-facing Clean Workroot commands package-based through `python -m ai_workroot` and the installed `workroot` entry point.
4. Keep `scripts/` limited to shell wrappers, developer utilities, release/checkbot commands, and legacy compatibility adapters.
5. Keep Public Seed historical. Do not make `space/`, `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md` active source architecture again.
6. Avoid a heavyweight DDD implementation tree. Keep the accepted Core / Contracts / Runtime / Storage / Indexing / Agent / CLI layout.
7. Keep the system local-first. Do not introduce remote LLM, remote embedding, vector database, or cloud service dependencies.

## Non-goals

- Do not tag or create a release as part of this migration design.
- Do not remove old capability before replacement behavior is mapped and regression-tested.
- Do not introduce a full GUI installer or C-end first-run application in this phase.
- Do not make `Tombstone` invisible in all contexts. Tombstones remain protected recall markers.
- Do not store redacted or deleted content in normal context packages.
- Do not create one file or table per domain noun unless the code needs the separation.

## Target State

### Active Package

`src/ai_workroot/` owns active Clean Workroot behavior:

```text
cli/        command parsing and output formatting
runtime/    application workflows and transaction boundaries
core/       domain concepts, policies, invariants, value objects
contracts/  stable standard-library protocol boundaries
storage/    filesystem, SQLite, JSONL, locks, migration implementations
indexing/   FTS, candidates, relationship projections, global indexes
agent/      Native Agent Entry, agent startup files, permission hints
resources/  package templates and static resources
```

### Scripts

`scripts/` is narrowed to:

```text
scripts/dev/                 checkbot, release validation, review export helpers
scripts/*.sh / *.ps1         wrappers that call package entry points
scripts/legacy/*.py          temporary compatibility commands for Public Seed capability
scripts/validate_kernel.py   historical validator until a package release validator fully replaces it
```

Python scripts that implement product behavior must either move into `src/ai_workroot/` or become thin adapters that import package modules.

### Tests

Tests are split by purpose:

```text
tests/unit/          core policies, value objects, providers, parsers
tests/integration/   storage + runtime + indexing flows
tests/smoke/         command-line and wrapper smoke tests
tests/negative/      redaction/deletion leakage, Public Seed active-root regressions
tests/legacy/        preserved Public Seed compatibility only
tests/fixtures/      old seed fixtures, SQLite fixtures, sample user directories
```

Legacy tests must say they are legacy. Current architecture tests must not require active root `space/`, `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md`.

## Capability Migration Model

Migration is capability-first, not file-first.

Each script is classified into one of five states:

| State | Meaning | Allowed behavior |
|---|---|---|
| Active package | Product behavior lives in `src/ai_workroot/` | Package tests are authoritative |
| Package wrapper | Script delegates to package with no product logic | Wrapper smoke test required |
| Legacy adapter | Script preserves Public Seed behavior temporarily | Hidden/namespaced, legacy tests only |
| Developer tool | Script supports release/checkbot/development only | Must not be documented as user flow |
| Retired fixture/history | Behavior is no longer executable product code | Preserved only as docs or fixtures |

No script can move from active behavior to retired without a matrix entry and a test proving replacement or intentional retirement.

## Capability Ownership

| Legacy script area | Target owner | Notes |
|---|---|---|
| `workroot_paths.py` | `runtime/environment.py`, `runtime/registry.py`, `storage/locks.py` | Clean Mode path and registry rules belong in runtime/storage |
| `workroot_state.py` | `runtime/environment.py`, `storage/jsonl_registry.py`, `storage/locks.py` | Registry concurrency remains storage-backed |
| `workroot_sqlite.py` | `storage/sqlite.py`, future `storage/migrations.py` | Schema and migrations move to package |
| `workroot_candidates.py` | `indexing/providers/candidate_provider.py` | Candidate source flags, safety, FTS projection stay indexing-owned |
| `workroot_indexing.py` | `indexing/providers/sqlite_fts.py`, future `indexing/pipeline.py` | File scanning, chunking, FTS, manifest writes move to indexing |
| `workroot_context.py` | `runtime/context.py`, `core/context.py`, indexing providers | Context Control becomes package runtime |
| `workroot_doctor.py` | `runtime/doctor.py`, `core/health.py` | Doctor checks become package health checks |
| `workroot_bootstrap.py` | `runtime/bootstrap.py`, `agent/native_entry.py` | bootstrap-dev remains developer-only |
| `workroot_agent_entry.py` | `agent/native_entry.py`, `resources/templates/` | Native Agent Entry templates are package resources |
| `workroot_client.py` | `runtime/work.py`, `runtime/assets.py`, `runtime/release.py`, `storage/*` | Largest capability migration; must be phased |
| `workroot_operation_manifest.py` | `core/extensions.py`, `runtime/legacy.py`, docs | Preserve recipes before deciding active command surface |
| `workroot_cli.py` | `cli/main.py`, `cli/commands/*`, `cli/legacy.py` | Active help stays Clean Workroot |
| smaller task/profile helpers | `runtime/work.py`, `agent/startup.py`, or `scripts/legacy/` | Do not expose Public Seed as active flow |

## Runtime Flows

### Clean Workroot init

```text
CLI -> runtime.init -> runtime.environment -> storage/jsonl + storage/locks
    -> storage.sqlite -> optional agent.native_entry
```

Rules:

- create or validate user-selected directory;
- keep managed state under `AI_WORKROOT_HOME`;
- reject `AI_WORKROOT_HOME` as user directory;
- reject duplicate directory bindings under registry lock;
- write only optional Native Agent Entry files into the user directory.

### Context Control

```text
CLI -> runtime.context
  -> runtime.registry resolves Workroot
  -> indexing candidate provider
  -> indexing FTS provider
  -> indexing relationship projection provider
  -> release-aware filters
  -> core/context budget and policy decisions
  -> storage persistence for context packages/traces/selections/trim decisions
```

Rules:

- FTS/query/relationship signals must affect candidate selection, not only display;
- safety and release filters must apply before ordinary rendering;
- debug output must show budgets, sources, scores, drops, timings, and trim steps;
- no remote model or embedding call is allowed.

### Work and Asset operations

```text
CLI -> runtime.work/runtime.assets/runtime.release
  -> core work/assets/release policies
  -> storage repositories
  -> indexing invalidation/update hooks
```

Legacy task/run/action/artifact/decision/retrieval-card/checkpoint/invalidation/session/continue/batch capabilities move here incrementally.

### bootstrap-dev

```text
CLI/scripts wrapper -> runtime.bootstrap
  -> runtime.environment registration
  -> storage.sqlite initialization
  -> agent.native_entry local ignored files
  -> .ai-workroot-local staging if needed
```

Rules:

- developer-only;
- no commit, tag, push, or release;
- idempotent under repeated and concurrent runs;
- does not depend on root tracked `AGENTS.md`, `CLAUDE.md`, `space/`, or `.workroot/`.

## Storage Architecture

Storage stays local-first and explicit.

### Environment control plane

```text
AI_WORKROOT_HOME/
  config.json
  registry/
  global-index/
  global-cache/
  workroots/<workroot_id>/
```

Global state owns management indexes and cache. It must not become a global knowledge body store.

### Per-Workroot state

```text
workroots/<workroot_id>/
  workroot.json
  charter/
  tasks/
  handoffs/
  assets/
  release/
  relationships/
  indexes/
  context/
  diagnostics/
  maintenance/
  cache/workroot.sqlite
  logs/
```

SQLite tables are per-Workroot DB scoped unless a table explicitly documents a global scope. Tables may still include `workroot_id` for safety and query consistency.

## Migration Architecture

The migration uses three lanes:

1. **Package replacement lane**: implement active package behavior and package tests.
2. **Compatibility lane**: keep old scripts callable only as wrappers or legacy commands until replacements pass.
3. **Quarantine lane**: move Public Seed active-root remnants into history/fixtures only after replacement behavior is proven.

Each lane has acceptance gates:

- capability mapped in the preservation matrix;
- package tests exist;
- legacy tests are moved or renamed as legacy;
- CLI help exposes only Clean Workroot primary commands;
- release/checkbot validation passes.

## Checkbot Architecture

Checkbot is a developer validation surface, not a release action. It may live under `scripts/dev/` and call package validators.

Minimum checks:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m ai_workroot doctor --release
python3 scripts/validate_kernel.py --release
scripts/dev/validate-release.sh
git diff --check origin/main...HEAD
```

Additional smoke checks use temporary `AI_WORKROOT_HOME` and temporary user directories only.

## Phasing

1. Baseline and checkbot inventory.
2. CLI and wrapper boundary cleanup.
3. Storage/state/migration package ownership.
4. Work and Asset runtime migration.
5. Retrieval & Index Control package ownership.
6. Context Control parity migration.
7. Release Control and Relationship Network parity migration.
8. System Health and release validator migration.
9. Tests split and legacy isolation.
10. Public Seed quarantine and final docs sweep.

Each phase must be committable and revertible independently.

## Risks

- Capability loss from deleting old scripts before package parity.
- Mixed active paths where `scripts/workroot_cli.py` and `ai_workroot.cli.main` behave differently.
- Tests passing because they still exercise legacy scripts, not active package behavior.
- Context Control regressions during extraction from the large legacy file.
- Release/redaction leakage through derived FTS/candidate/relationship projections.
- Public Seed terms returning through docs, help text, or test fixtures.
- Checkbot becoming a second release system instead of a validation tool.

## Mitigations

- Keep a migration matrix per script and per capability.
- Add package-first tests before retiring script behavior.
- Use wrappers before deletions.
- Split tests into unit, integration, smoke, negative, and legacy groups.
- Keep release-aware filtering centralized and covered by negative tests.
- Run temporary Clean Mode smoke tests after every phase that touches init/context/bootstrap/doctor.
- Keep commits small enough to revert one phase at a time.

## Readiness Criteria For Implementation

Implementation may start only after:

1. this architecture document is reviewed;
2. detailed design and numbered specs exist;
3. the migration order is clear;
4. no blocking ambiguity remains about which old capabilities are preserved, renamed, merged, retired, or deferred.
