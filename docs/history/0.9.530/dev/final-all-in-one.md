# AI Workroot 0.9.530 Final Codex Package — All In One

> This is a raw imported package snapshot retained for traceability.
> If this file conflicts with `docs/history/0.9.530/dev/final-architect-review-clarifications.md`, `docs/specs/`, `docs/architecture/`, `docs/adr/`, or `docs/history/0.9.530/plans/2026-05-20-0530-clean-workroot-domain-reset-plan.md`, the later clarified documents win.
> In particular: build replacement architecture first, then quarantine the old Public Seed active root.

This file concatenates the final architecture, specs, execution plans, migration plans, test plans, acceptance checklist, and ADRs.



---

<!-- SOURCE: README.md -->

# AI Workroot 0.9.530 Final Codex Implementation Package

This package is the final source of truth for the 0.9.530 Clean Workroot architecture reset.

It combines:

- the strategic domain model clarified through discussion;
- the lightweight engineering architecture to implement it;
- detailed specs;
- migration plans;
- documentation rewrite plans;
- testing and negative test plans;
- Codex execution order;
- release validation gates.

Codex must not redesign the architecture. Codex should implement the plan, report deviations, and ask for review when a required behavior cannot be implemented safely.

Recommended branch:

```text
feat/0.9.530-clean-workroot-domain-reset
```

Primary all-in-one file:

```text
FINAL_ALL_IN_ONE.md
```



---

<!-- SOURCE: 00_FINAL_MASTER_PLAN.md -->

# 0.9.530 Clean Workroot Architecture Reset — Final Master Plan

## 1. Purpose

0.9.530 is a major architecture reset. The project is moving from the retired Public Seed / Portable Seed layout into the Clean Workroot architecture.

The work has three simultaneous goals:

1. Retire the old active source-tree shape: `space/`, `.workroot/`, and committed root `AGENTS.md` / `CLAUDE.md`.
2. Preserve valuable legacy capabilities: tasks, runs, actions, checkpoints, retrieval cards, invalidations, artifacts, decisions, mind/release/tombstone concepts, link registry, global indexes, capability registry, doctor, migrations, Context Guide behavior, and bootstrap-dev.
3. Implement a simpler open-source-friendly engineering layout: `core / contracts / runtime / storage / indexing / agent / cli`.

The project uses DDD only as strategic modeling. The implementation must not become a heavy DDD tree.

## 2. Final engineering structure

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

The rest of the repository:

```text
install/
  unix/install.sh
  windows/install.ps1
scripts/dev/
docs/architecture/
docs/specs/
docs/adr/
docs/releases/
docs/dev/
docs/history/
tests/unit/
tests/integration/
tests/smoke/
tests/fixtures/
templates/native-agent-entry/
.github/workflows/
```

## 3. Final core concepts

The final conceptual model has 10 core areas:

1. Workroot Management
2. Work
3. Asset
4. Release Control
5. Relationship Network
6. Retrieval & Index Control
7. Context Control
8. Agent Interface
9. System Health
10. Extensions

These names must be used in docs and new code. Old terms must be retired from active architecture:

```text
Public Seed active profile
space/ as active product root
.workroot/ as active runtime root
Memory as formal term
Mind as formal term
Knowledge as top-level domain
Graph as business domain name
Context Gate
TombstoneMarker / ReleaseMarker / DeletionMarker
```

## 4. Implementation rule

Codex must implement in dependency order:

1. Branch and baseline.
2. Documentation source of truth.
3. Source layout scaffold.
4. Legacy active-tree quarantine.
5. WorkrootEnvironment and managed state.
6. Native Agent Entry templates.
7. Storage/schema alignment.
8. Core models.
9. Runtime orchestration.
10. Indexing and retrieval providers.
11. Context Control.
12. Release Control propagation.
13. Relationship Network.
14. System Health / Doctor.
15. CLI and install scripts.
16. Tests.
17. As-built documentation and release validation.

## 5. No silent capability loss

Before deleting or moving any old file or behavior, Codex must map it in the Legacy Capability Preservation Matrix.

Old active source structures may be quarantined into `docs/history/` or `tests/fixtures/legacy-public-seed-history/`, but must not remain active root architecture.

## 6. Release principle

This release may make major source tree changes. It must not automatically migrate real user directories because current usage is limited and the old Public Seed product shape is retired. However, it must preserve old project files in history/fixtures to avoid losing design knowledge or test evidence.



---

<!-- SOURCE: architecture/006-final-core-concepts-and-boundaries.md -->

# Final Core Concepts and Boundaries

## 1. Workroot Management

Owns global and per-Workroot identity.

Entities and concepts:

- WorkrootEnvironment
- EnvironmentConfig
- EnvironmentHome
- WorkrootRegistry
- WorkrootRegistration
- WorkrootDirectoryBinding
- WorkrootAlias
- WorkrootRelationship
- Workroot
- WorkrootCharter
- GlobalPreferences
- GlobalPolicyDefaults

Boundaries:

- Owns `AI_WORKROOT_HOME` control plane.
- Owns registry truth.
- Owns Workroot binding truth.
- Does not own task process, assets, relationship edges, indexes, context packages, or release records.

## 2. Work

Owns factual work process records.

Entities and concepts:

- Task
- TaskStatus
- TaskKind
- TaskProcessLevel
- TaskDecompositionPolicy
- AgentRun
- WorkAction
- WorkCheckpoint
- RetrievalCard
- InvalidationRecord
- Handoff
- WorkEvent
- OperationTransaction
- WorkflowRecipe

Boundaries:

- Task is retained. WorkItem is not a formal product term.
- Task can be decomposed through Relationship Network edges.
- Task/Action/Run are factual process records. They are not mutated into tombstone states.

## 3. Asset

Owns user value objects.

Entities and concepts:

- Asset
- AssetType
- AssetLifecycleStatus
- AssetSurface
- AssetPublication
- AssetPublicationPolicy
- AssetPublicationStatus
- AssetPathHistory
- AssetFingerprint
- AssetProvenance

Boundaries:

- Knowledge, Decision, Result, Reference, and Handoff document are Asset subtypes.
- Asset is not always a user-directory file.
- Published Asset is user-visible file output.
- Internal Asset may stay in managed state.

## 4. Release Control

Owns recall/release overlays over recallable Workroot objects.

Entities and concepts:

- ReleaseRecord
- ReleaseTargetRef
- ReleaseLevel
- Tombstone
- Redaction
- DeletionRecord
- RecallRule
- ReleasePolicy
- ReleasePropagationEvent

Boundaries:

- Tombstone is a first-class entity. Do not call it TombstoneMarker.
- Release Control overlays targets. It does not mutate target identity/status.
- Tombstone/quiet/archive are modeled, visible, traceable, but not strongly excluded by default in 0.9.530.
- Redaction/deletion/safety-sensitive content must be protected immediately.

## 5. Relationship Network

Owns canonical relationships among Workroot objects.

Entities and concepts:

- RelationshipNode
- RelationshipEdge
- RelationshipType
- RelationshipEvidence
- RelationshipPolicy

Boundaries:

- Business domain name is Relationship Network, not Graph.
- Graph remains only a technical term: graph traversal, graph projection, future graph database adapter.
- RelationshipEdge is canonical relationship truth.
- Traversal projection is an index/read model.

## 6. Retrieval & Index Control

Owns domain indexes, retrieval requests, provider orchestration, and management query indexes.

Entities and concepts:

- Index
- IndexScope
- IndexTier
- IndexKind
- IndexManifest
- IndexEntry
- IndexBuild
- IndexInvalidation
- IndexHealth
- IndexPolicy
- RetrievalRequest
- RetrievalResult
- RetrievalPlan
- RetrievalProvider
- GlobalWorkrootIndex
- ContextCandidateIndex
- AssetTextIndex
- RelationshipTraversalIndex

Boundaries:

- Not a database index layer.
- Not merely RAG.
- Serves Context Control and local maintenance/query features.
- Providers are connected through contracts and adapters.

## 7. Context Control

Owns final context selection, budget, package, and trace.

Entities and concepts:

- ContextRequest
- ContextMode
- ContextBudget
- ContextRecallPolicy
- ContextController
- ContextPackage
- ContextTrace
- CandidateSelection
- BudgetTrimDecision

Boundaries:

- Does not write user directory.
- Does not publish Assets.
- Does not own indexes.
- Does not own relationships.
- Consumes Work, Asset, Release Control, Relationship Network, and Retrieval & Index Control.

## 8. Agent Interface

Owns agent startup and protocol-facing behavior.

Entities and concepts:

- NativeAgentEntry
- AgentEntryTemplate
- ManagedBlock
- AgentEntryAuthorization
- AgentStartupContract
- AgentAdapter
- PermissionHint
- AgentOutputStyle
- AgentRouting

Boundaries:

- Native Agent Entry templates are committed.
- Root `AGENTS.md` / `CLAUDE.md` are generated locally and ignored.
- Agent-ready Workroot requires authorized Native Agent Entry.

## 9. System Health

Owns diagnosis, maintenance, migration, and release validation.

Entities and concepts:

- DoctorRun
- DiagnosticCheck
- DiagnosticFinding
- MaintenanceAction
- MigrationRecord
- ReleaseValidation
- SchemaCheck
- IndexHealthCheck
- EnvironmentHealthCheck

Boundaries:

- Doctor default is read-only.
- Maintenance requires explicit action.
- Migration records schema/data upgrades.

## 10. Extensions

Owns future capability and extension boundaries.

Entities and concepts:

- Capability
- Skill
- AgentAdapter
- McpBridge
- StorageDriver
- RetrievalDriver
- ExportImportDriver

Boundaries:

- Reserved in 0.9.530.
- Do not implement a heavy plugin system now.



---

<!-- SOURCE: architecture/000-overview.md -->

# Architecture Overview

## What changed

AI Workroot started as a Public Seed / Portable Seed layout centered around `space/` and `.workroot/`. That layout is no longer the active architecture. 0.9.530 resets the project around **Clean Workroot** and **bootstrap-dev dogfood**.

The new architecture keeps the valuable capabilities from the old seed, but removes the old structure and names that no longer fit.

## Product model

AI Workroot is a local-first system that helps a user manage multiple Workroots, assets, work processes, relationships, indexes, context packages, agent entry points, releases/tombstones, and system health.

It is not a memory system. It is not a graph database. It is not a RAG-only tool. It is not a Public Seed project tree.

## Runtime modes

There are two active scenarios:

1. **Clean Workroot**
   - A user selects a directory.
   - That directory is the user asset directory.
   - Managed state lives under `AI_WORKROOT_HOME`.
   - Native Agent Entry files are written only with explicit user authorization.

2. **bootstrap-dev / dogfood**
   - The AI Workroot source repository is itself treated as a Clean Workroot user directory.
   - Managed state still lives under `AI_WORKROOT_HOME`.
   - `AGENTS.md` / `CLAUDE.md` are generated locally from templates and Git ignored.
   - `.ai-workroot-local/` is a local staging area, not managed state and not formal source.

Public Seed is retired as an active architecture. It may appear only in history docs or legacy fixtures.

## Strategic domain model

DDD was used only to understand the domain. The final implementation does not use a heavyweight DDD directory layout. The ten core concepts are:

1. Workroot Management
2. Work
3. Asset
4. Release Control
5. Relationship Network
6. Retrieval & Index Control
7. Context Control
8. Agent Interface
9. System Health
10. Extensions

These concepts are implemented through a lightweight module structure:

```text
core/
contracts/
runtime/
storage/
indexing/
agent/
cli/
```

## Engineering principles

- Keep `core` cohesive and small.
- Keep `contracts` independent.
- Keep `runtime` as orchestration, not a business-logic dumping ground.
- Keep `storage`, `indexing`, and `agent` as implementation/adaptation modules.
- Keep `cli` command-based and thin.
- Preserve old capabilities through explicit mapping.
- Do not create one class/file/table for every domain term.
- Do not use technical names for core domain concepts.

## 0.9.530 release goal

0.9.530 is an architecture reset release:

- Retire active Public Seed layout.
- Establish Clean Workroot as default.
- Establish bootstrap-dev dogfood flow.
- Introduce the lightweight engineering structure.
- Preserve old Work, Asset, Index, Release, Tombstone, Relationship, Context, Agent, and Extension capabilities.
- Rewrite docs/specs/roadmap/release validation around the new model.



---

<!-- SOURCE: architecture/001-core-concepts.md -->

# Core Concepts

This document defines the domain language. Codex must use these names in code, docs, specs, tests, and release notes.

## Forbidden or retired domain terms

Do not use these as active domain terms:

- Public Seed
- Portable Seed
- Mind
- Memory
- Knowledge as a top-level domain
- Graph as a top-level business domain
- Context Gate
- TombstoneMarker
- ReleaseMarker
- DeletionMarker
- RedactionMarker

Allowed use:

- Public Seed may appear in history docs.
- Graph may appear as a technical term: graph traversal, graph projection, graph-like implementation, future graph database adapter.
- Knowledge may appear as an `AssetType`, not as a top-level domain.

## Core concept 1: Workroot Management

**Purpose:** Manage the local environment, multiple Workroots, global configuration, registry, bindings, aliases, relationships, and Workroot metadata.

Primary concepts:

- `WorkrootEnvironment`
- `EnvironmentConfig`
- `EnvironmentHome`
- `WorkrootRegistry`
- `WorkrootRegistration`
- `WorkrootDirectoryBinding`
- `WorkrootAlias`
- `WorkrootRelationship`
- `Workroot`
- `WorkrootCharter`
- `GlobalPreferences`
- `GlobalPolicyDefaults`

Rules:

- `WorkrootEnvironment` represents `AI_WORKROOT_HOME` as a domain concept.
- `WorkrootRegistration` is a global record; `Workroot` is the per-Workroot identity/state object.
- Global config/preferences are not global knowledge.
- Cross-Workroot content recall is not automatic.

## Core concept 2: Work

**Purpose:** Record work process facts and continuity.

Primary concepts:

- `Task`
- `TaskStatus`
- `TaskKind`
- `TaskProcessLevel`
- `TaskDecompositionPolicy`
- `AgentRun`
- `WorkAction`
- `WorkCheckpoint`
- `RetrievalCard`
- `InvalidationRecord`
- `Handoff`
- `WorkEvent`
- `OperationTransaction`
- `WorkflowRecipe`

Rules:

- `Task` remains a first-class concept.
- `WorkItem` is not a product term.
- Task hierarchy is represented through Relationship Network, not by tightly coupling fields into Task.
- Work facts are factual records. Release Control may overlay them, but does not mutate their core factual identity.

## Core concept 3: Asset

**Purpose:** Manage user value objects.

Primary concepts:

- `Asset`
- `AssetType`
- `AssetLifecycleStatus`
- `AssetSurface`
- `AssetPublication`
- `AssetPublicationPolicy`
- `AssetPublicationStatus`
- `AssetPathHistory`
- `AssetFingerprint`
- `AssetProvenance`

Rules:

- Knowledge, Decision, Result, Reflection, Pattern, Principle, Reference, Handoff document are Asset subtypes.
- Asset is not necessarily a user directory file.
- Published Asset is a user-visible file or user-visible output.
- Internal Asset can live only in managed state.
- Asset metadata must anticipate rename, move, delete, hash change, ambiguous path, missing file.

## Core concept 4: Release Control

**Purpose:** Manage release, quiet, archive, tombstone, redaction, and deletion overlays over recallable objects.

Primary concepts:

- `ReleaseRecord`
- `ReleaseTargetRef`
- `ReleaseLevel`
- `Tombstone`
- `Redaction`
- `DeletionRecord`
- `RecallRule`
- `ReleasePolicy`
- `ReleasePropagationEvent`

Rules:

- `Tombstone` is the entity name. Do not call it `TombstoneMarker`.
- Release Control overlays any recallable object without mutating that target object.
- Tombstone/quiet/archive are modeled, visible, traceable in 0.9.530 but not forcibly excluded from ordinary context.
- Redaction/deletion/safety-sensitive must be strictly protected in 0.9.530.

## Core concept 5: Relationship Network

**Purpose:** Manage canonical relationships among Workroot objects.

Primary concepts:

- `RelationshipNode`
- `RelationshipEdge`
- `RelationshipType`
- `RelationshipEvidence`
- `RelationshipPolicy`

Rules:

- Business domain name is Relationship Network.
- Graph is only an implementation/algorithm word.
- Relationship truth is canonical. Traversal indexes are derived.

## Core concept 6: Retrieval & Index Control

**Purpose:** Manage layered/scoped indexes and retrieval providers for context recall and local management queries.

Primary concepts:

- `Index`
- `IndexScope`
- `IndexTier`
- `IndexKind`
- `IndexManifest`
- `IndexEntry`
- `IndexBuild`
- `IndexInvalidation`
- `IndexHealth`
- `IndexPolicy`
- `RetrievalRequest`
- `RetrievalResult`
- `RetrievalPlan`
- `RetrievalProvider`

Rules:

- This is not database indexing only.
- This is not just RAG.
- It serves Context Control and local management/doctor/UI queries.
- Providers must be connected through contracts/adapters.

## Core concept 7: Context Control

**Purpose:** Decide what enters an agent's context.

Primary concepts:

- `ContextRequest`
- `ContextMode`
- `ContextBudget`
- `ContextRecallPolicy`
- `ContextController`
- `ContextPackage`
- `ContextTrace`
- `CandidateSelection`
- `BudgetTrimDecision`

Rules:

- Context Control does not write user directories.
- Context Control does not publish assets.
- Context Control consumes Retrieval, Relationship, Asset, Work, Release, and Charter state.

## Core concept 8: Agent Interface

**Purpose:** Define how native agents enter, read, and operate inside a Workroot.

Primary concepts:

- `NativeAgentEntry`
- `AgentEntryTemplate`
- `ManagedBlock`
- `AgentEntryAuthorization`
- `AgentStartupContract`
- `AgentAdapter`
- `PermissionHint`
- `AgentOutputStyle`
- `AgentRouting`

Rules:

- Native Entry files are generated only with explicit authorization.
- Root repo AGENTS.md / CLAUDE.md are local generated files, not committed.

## Core concept 9: System Health

**Purpose:** Diagnose, maintain, migrate, and validate system state.

Primary concepts:

- `DoctorRun`
- `DiagnosticCheck`
- `DiagnosticFinding`
- `MaintenanceAction`
- `MigrationRecord`
- `ReleaseValidation`

Rules:

- Doctor is read-only by default.
- Maintenance actions are explicit.
- Migration must record status and backups when destructive.

## Core concept 10: Extensions

**Purpose:** Reserve extension boundaries for capabilities, skills, agent adapters, MCP, storage/retrieval/export drivers.

Primary concepts:

- `Capability`
- `Skill`
- `AgentAdapter`
- `McpBridge`
- `StorageDriver`
- `RetrievalDriver`
- `ExportImportDriver`

Rules:

- 0.9.530 should preserve the boundary, not implement a full plugin system.



---

<!-- SOURCE: architecture/002-engineering-structure.md -->

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



---

<!-- SOURCE: architecture/003-runtime-layout.md -->

# Runtime Layout

## User directory

The user-selected directory is a user asset directory.

Rules:

- AI Workroot does not treat same-named user folders such as `state/`, `logs/`, `cache/`, or `context/` as managed state.
- AI Workroot does not create internal runtime folders in the user directory by default.
- Native Agent Entry files are written only after explicit user authorization.
- Published Assets may be written to the user directory only through Asset Publication Policy.

Example:

```text
<user-directory>/
  user files...
  AGENTS.md   # only if authorized
  CLAUDE.md   # only if authorized
```

## AI_WORKROOT_HOME

`AI_WORKROOT_HOME` is represented by `WorkrootEnvironment`.

Target layout:

```text
$AI_WORKROOT_HOME/
  config.json

  registry/
    workroots.jsonl
    directory-bindings.jsonl
    aliases.jsonl
    relationships.jsonl
    .registry.lock

  preferences/
    operator-preferences.json
    policy-defaults.json
    agent-defaults/

  global-index/
    workroots.index.jsonl
    tasks.index.jsonl
    assets.index.jsonl
    decisions.index.jsonl
    handoffs.index.jsonl
    time.index.jsonl
    levels/

  global-cache/
    global.sqlite

  migrations/
    global.jsonl
    history/
    locks/

  concurrency/
    locks/

  workroots/
    wr_xxx/
      workroot.json
      charter/
      state/
      tasks/
      handoffs/
      assets/
      release/
      relationships/
      indexes/
      context/
      diagnostics/
      maintenance/
      cache/
      logs/
```

## Global layer rules

- `EnvironmentConfig`, `WorkrootRegistry`, `DirectoryBinding`, `Alias`, and `WorkrootRelationship` are canonical global state.
- `global-index` is a derived read model for navigation and management.
- `global-cache` is a derived/auxiliary store.
- No global knowledge body store.
- No global user profile. Use operator preferences and policy defaults only.
- Workroot role/persona/purpose belongs to `WorkrootCharter`.

## Per-Workroot rules

Each Workroot has:

- `workroot.json`: Workroot metadata.
- `charter/`: purpose, role, boundaries, collaboration rules.
- `tasks/`: task/process records where file-backed records are used.
- `assets/`: internal asset metadata or managed internal asset records.
- `release/`: release/tombstone/redaction/deletion records.
- `relationships/`: relationship network exports/backups if used.
- `indexes/`: per-Workroot derived indexes.
- `context/`: ContextPackage history and ContextTrace diagnostics.
- `diagnostics/`: doctor/check outputs.
- `cache/`: derived caches.

## Source repository under bootstrap-dev

The AI Workroot source repository is a Clean Workroot user directory.

Active root must not contain tracked:

```text
AGENTS.md
CLAUDE.md
space/
.workroot/
.idea/
```

Allowed local-only:

```text
AGENTS.md
CLAUDE.md
.ai-workroot-local/
```

These must be ignored.

## `.ai-workroot-local/`

Purpose: local staging for bootstrap-dev.

```text
.ai-workroot-local/
  drafts/
  reviews/
  patches/
  smoke-output/
  context-packages/
```

Rules:

- Not managed state.
- Not formal source.
- Not committed.
- Formal content must be promoted into `docs/`, `src/`, `tests/`, `templates/`, or `.github/`.



---

<!-- SOURCE: architecture/004-legacy-capability-preservation.md -->

# Legacy Capability Preservation Matrix

This matrix prevents regression during the architecture reset. Codex must not delete a preserved capability without mapping it into the new structure and tests.

Status values:

- `preserve`: keep capability with same semantics.
- `rename`: keep capability under a better name.
- `merge`: merge into a broader concept.
- `retire`: intentionally remove as active architecture.
- `defer`: reserve boundary but do not fully implement now.

| Old capability/location | New module | New concept | Status | Acceptance requirement |
|---|---|---|---|---|
| `space/` active layout | docs/history or fixtures | Public Seed history | retire | Root active tree no longer contains tracked `space/`. |
| `.workroot/` active runtime | docs/history or fixtures | Public Seed history | retire | Root active tree no longer contains tracked `.workroot/`. |
| root `AGENTS.md` / `CLAUDE.md` | `agent/` + resources templates | Native Agent Entry templates | rename | Root files generated locally and ignored, not tracked. |
| `task_registry.csv` | `core/work.py`, storage schema | Task | preserve | Task status/kind/process level preserved. |
| `process_level=L0/L1/L2` | `core/work.py` | TaskProcessLevel | preserve | L0/L1/L2 semantics documented and tested. |
| quick/session/daily tasks | `core/work.py` | TaskKind=session | preserve | Session task does not automatically publish assets. |
| long-running/project task | `core/work.py` | TaskKind=project | preserve | TaskDecompositionPolicy exists. |
| `run_registry.csv` | `core/work.py` | AgentRun | preserve | AgentRun can be recorded and related to Task. |
| `action_registry.csv` | `core/work.py` | WorkAction | preserve | Actions keep type/risk/evidence fields. |
| `checkpoint_registry.csv` | `core/work.py` | WorkCheckpoint | preserve | Checkpoints can be recorded and recalled. |
| `retrieval_card_registry.csv` | `core/work.py` + `indexing/` | RetrievalCard | preserve | Retrieval cards mapped to retrieval/index records. |
| `invalidation_registry.csv` | `core/work.py` / `core/assets.py` | InvalidationRecord | preserve | Invalidation affects relationships/assets/context policy. |
| `artifact_registry.csv` | `core/assets.py` | Asset | merge | Artifact becomes Asset. |
| `decision_registry.csv` | `core/assets.py` | Asset(type=decision) | merge | No top-level Decision domain. |
| `mind_registry.csv` | `core/assets.py` + `core/release.py` | Asset subtypes / Release Control | merge | No formal Mind/Memory terms. |
| `forgetting-policy` | `core/release.py` | ReleasePolicy / Tombstone / Redaction / DeletionRecord | rename | Tombstone is first-class; redaction/deletion protected. |
| tombstone entries | `core/release.py` | Tombstone | preserve | Entity named Tombstone, not TombstoneMarker. |
| released/deleted/redacted records | `core/release.py` | ReleaseRecord / DeletionRecord / Redaction | preserve | Derived indexes must not leak deleted/redacted content. |
| `link_registry.csv` | `core/relationships.py` | RelationshipEdge | rename | Relationship Network replaces Graph domain wording. |
| SQLite `graph_nodes`/`graph_edges` | `storage/sqlite` + `core/relationships.py` | relationship nodes/edges | rename | Business docs use Relationship Network. |
| `global-index/workroots.index.jsonl` | `indexing/global_indexes.py` | GlobalWorkrootIndex | preserve | Environment scope index exists. |
| `global-index/tasks.index.jsonl` | `indexing/global_indexes.py` | GlobalTaskIndex | preserve | Global task navigation index is supported. |
| `global-index/assets.index.jsonl` | `indexing/global_indexes.py` | GlobalAssetIndex | preserve | Asset metadata can be queried globally. |
| `knowledge.index.jsonl` | `indexing/global_indexes.py` | Asset index filtered by type | merge | Knowledge is Asset subtype. |
| `decisions.index.jsonl` | `indexing/global_indexes.py` | Asset index filtered by type=decision | merge | Decision is Asset subtype. |
| FTS indexed files/chunks | `indexing/fts.py` | AssetTextIndex / FTS provider | preserve | FTS works locally; no vector/remote dependency. |
| Context Candidates | `indexing/candidates.py` | ContextCandidateIndex | preserve | Candidate is read model, not Asset. |
| Context Guide Builder | `core/context.py` + `runtime/context.py` | Context Control | rename | CLI remains `workroot context`. |
| Context Package history | `core/context.py` | ContextPackage | preserve | Not user asset by default. |
| Debug Trace | `core/context.py` + `core/health.py` | ContextTrace | preserve | Not user asset by default. |
| Doctor | `core/health.py` + `runtime/doctor.py` | System Health | preserve | Doctor read-only by default. |
| schema migrations | `storage/sqlite/migrations.py` | MigrationRecord | preserve | Migration state is recorded. |
| capability registry | `core/extensions.py` | Capability | defer | Boundary preserved, full plugin system deferred. |
| MCP interface | `core/extensions.py` + `agent/` | McpBridge | defer | Boundary preserved. |
| permission hints | `core/agent.py` / contracts | PermissionHint | preserve | Agent and safety specs retain permission rules. |
| storage-policy | `core/health.py` + storage specs | StoragePolicy | preserve | Canonical vs derived stores documented. |
| export/import interface | extensions/system health | ExportImportDriver / future manifest | defer | Boundary documented, not fully implemented. |
| bootstrap-dev | `runtime/bootstrap.py` + `agent/` | bootstrap-dev dogfood | preserve | No commit/tag/push; local entries ignored. |
| install scripts | `install/` | user installation | preserve | Moved from scripts to install. |
| `scripts/*.py` product logic | `src/ai_workroot/*` | core/runtime/storage/indexing/agent/cli | rename | Scripts become wrappers/dev tools only. |

Codex must update this matrix if it discovers additional legacy capabilities. New discoveries must not be silently dropped.



---

<!-- SOURCE: architecture/005-dependency-rules.md -->

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



---

<!-- SOURCE: matrix/legacy-capability-preservation-matrix.md -->

# Legacy Capability Preservation Matrix

This matrix prevents capability loss during the 0.9.530 reset.

| Old capability / location | New concept | New module | Status | Required acceptance |
|---|---|---|---|---|
| Public Seed root `space/` | Historical Public Seed | docs/history or tests/fixtures | retired/quarantined | Not active root; preserved if useful |
| Public Seed root `.workroot/` | Historical runtime contracts/fixtures | docs/history or tests/fixtures | retired/quarantined | Not active root |
| Root `AGENTS.md` | Native Agent Entry template/local generated entry | agent + templates | renamed | Root file not tracked; template committed |
| Root `CLAUDE.md` | Native Agent Entry template/local generated entry | agent + templates | renamed | Root file not tracked; template committed |
| `task_registry.csv` | Task / Task index | core/work + indexing | preserved | Task model and index tests |
| `run_registry.csv` | AgentRun | core/work | preserved | run persistence/index tests |
| `action_registry.csv` | WorkAction | core/work | preserved | action model test |
| `artifact_registry.csv` | Asset | core/assets | merged | asset model supports result/generated/source |
| `decision_registry.csv` | Asset(asset_type=decision) | core/assets | merged | no top-level decision domain required |
| `retrieval_card_registry.csv` | RetrievalCard | core/work + indexing | preserved | retrieval card model/index test |
| `checkpoint_registry.csv` | WorkCheckpoint | core/work | preserved | checkpoint persistence test |
| `invalidation_registry.csv` | InvalidationRecord | core/work/assets/release | preserved | invalidation/release test |
| `mind_registry.csv` | Asset + Release Control | core/assets + core/release | renamed/merged | no Memory/Mind official term |
| old `knowledge` records | Asset(asset_type=knowledge) | core/assets | merged | no canonical knowledge_items table |
| old `released/tombstone/deleted` | ReleaseRecord / Tombstone / DeletionRecord | core/release | preserved | redaction/deletion protections |
| `link_registry.csv` | RelationshipEdge | core/relationships | renamed | relationship tests |
| graph tables/signals | Relationship Network / traversal projection | relationships + indexing | renamed | docs use Relationship Network |
| batch transaction journal | OperationTransaction | core/work/runtime | preserved | rollback/transaction record test |
| session summarize | Work summary / Context Trace / Asset optional | runtime/context/work | preserved/deferred | no loss of summarization capability |
| continue/handoff | Handoff + ContextPackage | core/work + core/context | preserved | handoff tests |
| context-policy | ContextControl policy | core/context | preserved | context mode/budget tests |
| forgetting-policy | Release Control policy | core/release | renamed | tombstone/redaction/deletion tests |
| storage-policy | Storage policy | core/common + storage | preserved | canonical/derived tests |
| permission hints | Agent Interface / Policy | core/agent | preserved | native entry permission tests |
| privacy policy | Release/Asset/Agent policy | core/common/release/assets | preserved | redaction tests |
| globalization policy | Common/time/localization policy | core/common | preserved/deferred | docs mention policy |
| extension policy | Extensions | core/extensions | preserved/deferred | capability boundary exists |
| test policy | System Health / release validation | core/health + docs/specs | preserved | validation docs/tests |
| global-index | Global indexes | indexing | preserved | global index test |
| global-cache | Global cache state | storage/indexing | preserved | not knowledge store |
| capability registry | Capability | core/extensions | preserved/deferred | capability model reserved |
| MCP interface | McpBridge | core/extensions/agent | preserved/deferred | reserved docs |
| export/import interface | ExportImportDriver | core/extensions/storage | preserved/deferred | reserved docs |
| install scripts | install/unix + install/windows | install | preserved | parse/smoke test |
| bootstrap-dev | Clean Workroot dogfood | runtime/bootstrap + agent | preserved | idempotent smoke |
| doctor | System Health | core/health + runtime/doctor | preserved | doctor tests |
| SQLite schema | storage schema | storage/sqlite | preserved/rewritten | schema tests |
| FTS indexing | FTS provider | indexing/providers | preserved | FTS tests |
| Context Candidates | Candidate index/read model | indexing + core/retrieval | preserved | candidate tests |
| Debug trace | ContextTrace / Diagnostics Evidence | core/context + health | preserved | trace tests |



---

<!-- SOURCE: specs/001-project-structure-and-naming.spec.md -->

# Spec 001 — Project Structure and Naming

Status: accepted
Target: 0.9.530

## Purpose

Reset the source tree from Public Seed to Clean Workroot architecture and establish stable naming rules.

## Required source structure

Create or migrate toward:

```text
src/ai_workroot/core/
src/ai_workroot/contracts/
src/ai_workroot/runtime/
src/ai_workroot/storage/
src/ai_workroot/indexing/
src/ai_workroot/agent/
src/ai_workroot/cli/
src/ai_workroot/resources/
install/unix/install.sh
install/windows/install.ps1
scripts/dev/
docs/architecture/
docs/specs/
docs/adr/
docs/dev/
docs/history/
```

## Active root must not contain tracked retired seed files

These must not be tracked in active repo root:

```text
AGENTS.md
CLAUDE.md
space/
.workroot/
.idea/
```

If historical content is needed, move it to:

```text
docs/history/public-seed.md
tests/fixtures/legacy-public-seed-history/
```

## Naming rules

Use:

```text
Clean Workroot
bootstrap-dev dogfood
Workroot Management
WorkrootEnvironment
Asset
Release Control
Tombstone
Relationship Network
Retrieval & Index Control
Context Control
Agent Interface
System Health
```

Do not use as active domain names:

```text
Public Seed
Portable Seed
Mind
Memory
Graph
Context Gate
TombstoneMarker
ReleaseMarker
DeletionMarker
RedactionMarker
```

## Template and local entry rules

The repo may contain templates:

```text
templates/native-agent-entry/AGENTS.md.template
templates/native-agent-entry/CLAUDE.md.template
src/ai_workroot/resources/templates/native-agent-entry/...
```

The repo must not track generated root:

```text
/AGENTS.md
/CLAUDE.md
```

`.gitignore` must include:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

## Acceptance

- `git ls-files AGENTS.md CLAUDE.md` returns no active root files.
- `git ls-files | grep '^space/'` returns no active root files except explicit fixtures/history.
- `git ls-files | grep '^.workroot/'` returns no active root files except explicit fixtures/history.
- `README.md` no longer says current architecture is Public Seed.
- `ROADMAP.md` no longer has Public Seed stabilization as current P0.
- `docs/specs/README.md` lists new specs and statuses.



---

<!-- SOURCE: specs/002-clean-workroot-installation.spec.md -->

# Spec 002 — Clean Workroot Installation

Status: accepted
Target: 0.9.530

## Purpose

Define user-facing Clean Workroot initialization.

## User directory rules

The selected directory is a user asset directory.

AI Workroot must not:

- create internal managed state folders in the user directory;
- treat same-named folders like `logs/`, `cache/`, `state/`, `context/` as managed state;
- write ContextPackage, ContextTrace, candidates, FTS rows, logs, cache, registry, or indexes into the user directory;
- write Native Agent Entry files without explicit authorization.

AI Workroot may:

- create or update `AGENTS.md` / `CLAUDE.md` only after explicit authorization;
- publish user-visible assets only through Asset Publication Policy;
- leave all other user directory contents untouched unless explicitly requested.

## Init flow

1. Resolve `AI_WORKROOT_HOME`.
2. Initialize or load `WorkrootEnvironment`.
3. Validate selected user directory.
4. Acquire registry lock.
5. Check duplicate active directory binding.
6. Create `WorkrootRegistration` and `WorkrootDirectoryBinding`.
7. Create per-Workroot state directory.
8. Initialize storage schema.
9. Initialize default WorkrootCharter placeholder.
10. Ask for Native Agent Entry authorization.
11. If authorized, write managed block into `AGENTS.md` / `CLAUDE.md`.
12. Run post-init doctor check.

## Native Agent Entry authorization

The prompt must explain:

- files will be created/updated in the user directory;
- contents are short launchers;
- no state path, Workroot ID, logs, indexes, handoffs, or traces will be embedded;
- user content outside managed block is preserved.

## Agent-ready state

A Workroot can be registered without Native Agent Entry for admin/test use.

An agent-ready Workroot requires authorized Native Agent Entry files.

## Acceptance

- Init creates managed state under `AI_WORKROOT_HOME`, not user directory.
- Init rejects duplicate active binding.
- Init can run without Native Agent Entry only as registered/non-agent-ready.
- Native Entry write requires explicit authorization.
- ContextPackage and ContextTrace are not written to user directory.
- User-created `logs/` or `cache/` inside user dir does not cause violation.



---

<!-- SOURCE: specs/003-workroot-environment-managed-state.spec.md -->

# Spec 003 — WorkrootEnvironment and Managed State

Status: accepted
Target: 0.9.530

## Purpose

Model `AI_WORKROOT_HOME` as `WorkrootEnvironment` and define global/per-Workroot state.

## Canonical global entities

- `EnvironmentConfig`
- `WorkrootRegistry`
- `WorkrootRegistration`
- `WorkrootDirectoryBinding`
- `WorkrootAlias`
- `WorkrootRelationship`
- `GlobalPreferences`
- `GlobalPolicyDefaults`

## Derived global entities

- `GlobalWorkrootIndex`
- `GlobalTaskIndex`
- `GlobalAssetIndex`
- `GlobalTimeIndex`
- `global-cache/global.sqlite`

## Target layout

```text
AI_WORKROOT_HOME/
  config.json
  registry/
    workroots.jsonl
    directory-bindings.jsonl
    aliases.jsonl
    relationships.jsonl
    .registry.lock
  preferences/
    operator-preferences.json
    policy-defaults.json
    agent-defaults/
  global-index/
  global-cache/
  migrations/
  concurrency/
  workroots/
```

## Global preferences rules

- No global user profile.
- No global knowledge body store.
- Global preferences are operator/system preferences: language, timezone, default context mode, default budgets, policy defaults.
- Per-Workroot role/purpose is stored in `WorkrootCharter`.

## Per-Workroot layout

```text
workroots/wr_xxx/
  workroot.json
  charter/
  state/
  tasks/
  handoffs/
  assets/
  release/
  relationships/
  indexes/
  context/
  diagnostics/
  maintenance/
  cache/
  logs/
```

## Registry locking

All registry writes must hold `.registry.lock`.

Inside the lock, re-read registry before writing to avoid races.

## WorkrootRegistration vs Workroot

`WorkrootRegistration` lives in global registry. It points to user directory and state directory.

`Workroot` lives in per-Workroot state. It stores Workroot metadata and Workroot-level settings.

## Acceptance

- Environment initializes without global user profile.
- Registry writes are locked.
- Duplicate directory binding is race-safe.
- `global-index` is treated as derived read model.
- Doctor can detect registry-state mismatch.



---

<!-- SOURCE: specs/004-bootstrap-dev-dogfood.spec.md -->

# Spec 004 — bootstrap-dev Dogfood

Status: accepted
Target: 0.9.530

## Purpose

Define AI Workroot self-management through Clean Workroot dogfood.

## Rules

- bootstrap-dev treats the AI Workroot source repo as a Clean Workroot user directory.
- It does not use Public Seed assumptions.
- It does not require root `AGENTS.md`.
- It does not require `.workroot/kernel/VERSION`.
- It must not commit, tag, push, or create release.
- It must be idempotent.
- It must be safe under concurrent runs.

## Project marker

Use:

```text
workroot.project.json
```

Required fields:

```json
{
  "project": "ai-workroot",
  "bootstrapDevSupported": true,
  "architecture": "clean-workroot",
  "version": "0.9.530"
}
```

## Local generated files

bootstrap-dev creates:

```text
AGENTS.md
CLAUDE.md
.ai-workroot-local/
```

These must be ignored:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

## `.ai-workroot-local/`

Use for:

- drafts
- reviews
- patches
- smoke output
- context package samples
- temporary analysis

Do not use for:

- managed state
- canonical assets
- formal architecture docs
- formal specs
- source code
- tests
- release notes

## bootstrap-dev publication policy

bootstrap-dev uses project-native asset publication:

```text
architecture doc -> docs/architecture/
spec -> docs/specs/
ADR -> docs/adr/
release note -> docs/releases/
history -> docs/history/
source code -> src/ai_workroot/
test -> tests/
template -> templates/
CI -> .github/workflows/
process draft -> .ai-workroot-local/
```

## Acceptance

- bootstrap-dev succeeds without root AGENTS.md and without `.workroot/`.
- second bootstrap-dev run reuses existing Workroot registration.
- generated entry files are ignored.
- `.ai-workroot-local/` is ignored.
- no commit/tag/push command is executed.



---

<!-- SOURCE: specs/005-core-model.spec.md -->

# Spec 005 — Core Model

Status: accepted
Target: 0.9.530

## Purpose

Define core model files and lightweight implementation style.

## Core files

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

Do not create one file per entity unless a file grows too large.

## Common concepts

`common.py` should define small shared concepts only:

- typed IDs or ID helpers
- `ActorRef`
- `SourceRef`
- `EvidenceRef`
- `PolicyRef`
- `DomainEvent`
- time helpers/value objects where needed

It must not become a garbage bin.

## Rich model rules

Core objects must include behavior when local to the concept:

Examples:

- `Task.can_transition_to()`
- `Task.close()`
- `Asset.publish()`
- `Asset.mark_missing()`
- `Tombstone.allows_explicit_review()`
- `RelationshipEdge.attach_evidence()`
- `IndexManifest.is_stale()`
- `ContextBudget.requires_trim()`

## Avoid over-ceremony

Do not require:

- repository for every entity;
- service for every entity;
- handler for every use case;
- class for every enum;
- one file per enum.

## External capabilities

Core may use contracts only when necessary.

Prefer:

- core policies for pure rules;
- runtime orchestration for workflows;
- contracts for abstract external capabilities;
- storage/indexing/agent for implementations.

## Acceptance

- core files contain domain behavior, not just dataclasses.
- core does not import storage/indexing/agent/cli/runtime.
- contracts imports are minimal and justified.
- retired terms are not present as active entity names.



---

<!-- SOURCE: specs/006-asset-model.spec.md -->

# Spec 006 — Asset Model

Status: accepted
Target: 0.9.530

## Purpose

Unify user value objects under Asset and define publication/staging/path tracking.

## Asset definition

Asset is a user value object. It may be internal, staged, or published.

Asset subtypes include:

```text
source
generated
knowledge
decision
result
reference
handoff
architecture_doc
spec
adr
release_note
review_report
code
test
template
history_note
dev_note
```

`Knowledge`, `Decision`, and `Result` are not top-level domains.

## Asset fields

Minimum fields:

```text
asset_id
workroot_id
asset_type
title
summary
lifecycle_status
publication_status
surface_id
current_path
original_path
content_hash
size_bytes
modifiedAt
lastSeenAt
missingSince
createdAt
updatedAt
```

## Lifecycle statuses

```text
draft
active
quiet
archived
superseded
tombstoned
released
missing
```

Note: tombstoned lifecycle state must be coordinated with Release Control `Tombstone`.

## Publication status

```text
internal
staged
published
unpublished
```

## AssetSurface

Represents allowed output surface.

Fields:

```text
surface_id
workroot_id
path
surface_type
allowed_asset_types
git_policy
is_local_only
created_by
createdAt
```

## AssetPublication

Records a publication event.

Fields:

```text
publication_id
asset_id
workroot_id
surface_id
target_path
publication_status
publishedAt
published_by
source_task_id
reason
git_policy
```

## Publication policy

Modes:

```text
project-native
existing-surfaces-only
workroot-managed-asset-folder
internal-drafts-only
```

bootstrap-dev uses `project-native`.

## Path history

Must anticipate:

- file renamed;
- file moved;
- file deleted;
- file modified;
- same hash at new path;
- same path with new hash;
- missing path;
- ambiguous duplicates.

Do not fully implement advanced resolver if too large, but schema/model must preserve fields.

## User directory write rules

Only Published Assets write to user directory.

ContextPackage, ContextTrace, Candidate, FTS row, logs, and debug output are not user assets.

## Acceptance

- `knowledge_items` no longer represents top-level Knowledge domain.
- Decision/Knowledge/Result map to Asset type.
- Asset publication has explicit policy/surface.
- bootstrap-dev maps formal assets to project-native directories.
- no unstructured auto-generated junk is written to user root.



---

<!-- SOURCE: specs/007-release-control.spec.md -->

# Spec 007 — Release Control

Status: accepted
Target: 0.9.530

## Purpose

Define release, quiet, archive, tombstone, redaction, and deletion control over recallable objects.

## Entities

### ReleaseRecord

General release overlay record.

Fields:

```text
release_id
workroot_id
target_ref
release_level
recall_rule
reason
createdAt
created_by
policy_ref
```

### ReleaseTargetRef

References a recallable object without coupling to its schema.

Fields:

```text
target_type
target_id
workroot_id
target_title
target_summary
```

Allowed target types:

```text
asset
task
work_action
agent_run
checkpoint
handoff
context_package
context_trace
retrieval_card
relationship_edge
```

### ReleaseLevel

```text
quiet
archived
tombstone
redacted
deleted
```

### Tombstone

Entity name is `Tombstone`. Do not use `TombstoneMarker`.

Fields:

```text
tombstone_id
workroot_id
target_ref
title
symbolic_note
lesson_asset_id
memorial_date
recall_rule
visibility_policy
createdAt
created_by
```

Tombstone means intentional remembrance. It is visible and explicitly reviewable.

### Redaction

Fields:

```text
redaction_id
workroot_id
target_ref
redacted_fields
redaction_reason
createdAt
created_by
```

### DeletionRecord

Fields:

```text
deletion_id
workroot_id
target_ref
minimum_audit_note
createdAt
created_by
```

DeletionRecord must not preserve deleted sensitive details.

## Default behavior in 0.9.530

- `quiet`: annotate/deprioritize, no hard exclusion.
- `archived`: annotate/lower default recall, no hard exclusion.
- `tombstone`: model, annotate, trace, visible, explicit review allowed; no hard ordinary-context exclusion yet.
- `redacted`: strict protection.
- `deleted`: strict protection.
- safety-sensitive: strict protection according to safety policy.

## Propagation

Release Control emits `ReleasePropagationEvent` to update:

- indexes;
- context candidates;
- FTS entries;
- relationship traversal projections;
- context selection traces;
- doctor checks.

## Negative rules

- Do not mutate `Task.status` to `tombstone`.
- Do not mutate `WorkAction.status` to `tombstone`.
- Do not convert deletion to Tombstone without user choice.
- Do not hide deleted/redacted details in derived indexes.

## Acceptance

- Tombstone entity exists with correct name.
- ReleaseRecord can cover Task without modifying Task.
- Redaction/deletion is enforced in ordinary context and indexes.
- Tombstone is visible and traceable, but not forcibly excluded in 0.9.530.
- ContextTrace records release state when relevant.



---

<!-- SOURCE: specs/008-relationship-network.spec.md -->

# Spec 008 — Relationship Network

Status: accepted
Target: 0.9.530

## Purpose

Replace Graph as business domain with Relationship Network.

## Entities

### RelationshipNode

Represents an object in the relationship network.

Node types:

```text
workroot
task
asset
agent_run
work_action
handoff
context_package
release_record
tombstone
external_reference
```

### RelationshipEdge

Canonical relationship.

Fields:

```text
edge_id
workroot_id
from_node_id
to_node_id
relationship_type
confidence
status
createdAt
updatedAt
created_by
```

### RelationshipType

Initial allowlist:

```text
uses
produces
updates
supersedes
supports
contradicts
references
belongs_to
related_to
derived_from
handoff_to
used_in_context
decomposes_to
covered_by_release
```

### RelationshipEvidence

Evidence for a relationship.

Fields:

```text
evidence_id
edge_id
evidence_type
source_ref
asset_id
task_id
context_trace_id
snippet_hash
note
createdAt
```

## Canonical vs projection

RelationshipEdge is canonical.

Relationship traversal index is derived and belongs to Retrieval & Index Control.

## Naming

Docs and core code must use Relationship Network terms.

Allowed technical terms:

```text
graph traversal
graph projection
future graph database adapter
```

## Storage

Preferred 0.9.530 schema names:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

If migration risk is too large, compatibility views from old `graph_*` names may be kept temporarily, but docs must use Relationship Network.

## Acceptance

- Business docs do not call the domain Graph.
- RelationshipEdge persists canonical relationship.
- Relationship traversal projection is derived.
- Task decomposition uses Relationship Network.
- Release Control can cover RelationshipEdge without mutating edge truth.



---

<!-- SOURCE: specs/009-retrieval-index-control.spec.md -->

# Spec 009 — Retrieval & Index Control

Status: accepted
Target: 0.9.530

## Purpose

Define retrieval and indexing as a core system capability serving context recall and local management queries.

## Entities and objects

### Index

Domain index, not database index.

Fields:

```text
index_id
workroot_id_or_environment_id
scope
tier
kind
source_domain
status
last_built_at
last_refreshed_at
row_count
staleness
rebuild_policy
retention_policy
```

### IndexScope

```text
environment
workroot
task
asset
extension
system
```

### IndexTier

```text
startup
active
registry
evidence
asset_recall
relationship
deep
accelerator
```

### IndexKind

```text
navigation
registry
metadata
text
fts
candidate
relationship_projection
vector
search
time
capability
```

### IndexManifest

Describes purpose, sources, provider, refresh strategy, release handling, and rebuild policy.

### IndexEntry

Generic read model row. Specific projections may implement structured entries:

- `GlobalWorkrootIndexEntry`
- `GlobalTaskIndexEntry`
- `GlobalAssetIndexEntry`
- `TextChunkEntry`
- `ContextCandidateEntry`
- `RelationshipTraversalEntry`

### RetrievalRequest / RetrievalResult / RetrievalPlan

Request/response/plan objects for retrieval.

## Provider / Contract / Adapter

Contracts define protocols:

```text
RetrievalProvider
IndexRepository
IndexRefreshGateway
```

Adapters implement protocols:

```text
SQLiteFtsProvider
CandidateProvider
RelationshipTraversalProvider
MetadataProvider
VectorProvider (reserved)
SearchProvider (reserved)
```

No actual vector DB, remote embedding, or remote LLM dependency in 0.9.530.

## Uses

### Context recall

Context Control uses Retrieval & Index Control for:

- candidates;
- FTS matches;
- metadata;
- relationship traversal projection;
- future provider fusion.

### Management queries

CLI/UI/System Health use Retrieval & Index Control for:

- list Workroots;
- list Tasks;
- list Assets;
- list Releases/Tombstones;
- index status;
- stale/corrupt index reporting.

## Release handling

Indexes must recognize:

- quiet;
- archived;
- tombstone;
- redacted;
- deleted;
- safety-sensitive.

0.9.530 behavior:

- tombstone/quiet/archive: annotate and trace.
- redacted/deleted/safety-sensitive: strictly protect.

## Acceptance

- Global indexes are environment-scoped.
- Workroot indexes are Workroot-scoped.
- ContextCandidate is read model, not Asset.
- FTS rows are read models, not Assets.
- Relationship traversal indexes are derived.
- Redacted/deleted entries cannot leak through FTS/candidates.



---

<!-- SOURCE: specs/010-context-control.spec.md -->

# Spec 010 — Context Control

Status: accepted
Target: 0.9.530

## Purpose

Generate agent-ready context through explicit control of recall, safety, relevance, budget, and traceability.

## Inputs

- WorkrootEnvironment / WorkrootRegistration
- WorkrootCharter
- active Task / Task hierarchy summary
- Assets
- Release Control records
- Relationship Network projections
- Retrieval results
- Context mode
- Agent type
- Query
- Token/latency budget

## Outputs

- ContextPackage
- ContextTrace
- selected/dropped candidate records
- budget trim decisions
- usage events

## ContextController responsibilities

- resolve Workroot;
- load Charter and active Task;
- request retrieval;
- read release state;
- read relationship signals;
- filter safety and lifecycle;
- score candidates;
- trim by budget;
- render context package;
- write trace;
- emit usage events.

## Non-responsibilities

Context Control must not:

- publish assets;
- write user directory;
- maintain Relationship canonical truth;
- build indexes;
- run migrations;
- repair system state;
- create Native Agent Entry.

## Modes

```text
fast
standard
quality
deep
```

Rules:

- `deep` requires explicit request.
- `quality` must be traceable; if only budget expansion in current version, trace must say so.
- No remote LLM, remote embedding, or vector DB hot path in 0.9.530.

## Budget

Use conservative token estimate. Do not rely only on whitespace split.

Must support:

- target tokens;
- hard token limit;
- agent budget;
- final fallback if trim sections cannot satisfy limit.

## Release behavior

- tombstone/quiet/archive: trace and annotate, no hard default exclusion in 0.9.530.
- redacted/deleted/safety-sensitive: must not enter ordinary ContextPackage.

## Acceptance

- ContextPackage not written to user directory.
- ContextTrace not written to user directory.
- ContextTrace includes selected/dropped reasons.
- Redacted/deleted content excluded.
- Hard token limit respected using conservative estimate/fallback.
- Graph business wording replaced with Relationship Network in output/docs where appropriate.



---

<!-- SOURCE: specs/011-agent-interface-native-entry.spec.md -->

# Spec 011 — Agent Interface and Native Agent Entry

Status: accepted
Target: 0.9.530

## Purpose

Define how Codex, Claude, and generic agents enter a Workroot.

## Domain name

The domain is Agent Interface. Native Agent Entry is one capability inside it.

## Templates

Templates must be committed:

```text
templates/native-agent-entry/AGENTS.md.template
templates/native-agent-entry/CLAUDE.md.template
src/ai_workroot/resources/templates/native-agent-entry/...
```

Generated root files must not be committed:

```text
/AGENTS.md
/CLAUDE.md
```

## Native Entry content

Native Entry must be short and only instruct:

```text
workroot context --agent <agent> --cwd .
```

It must not include:

- absolute managed state path;
- Workroot ID;
- AI_WORKROOT_HOME;
- logs;
- handoffs;
- indexes;
- debug trace;
- context package history.

## Managed block

Only the AI Workroot managed block may be updated.

User content outside managed block must be preserved.

## Authorization

User explicit authorization required before writing Native Entry in a user directory.

bootstrap-dev may generate local root entries because the developer invoked bootstrap-dev, but they must be ignored.

## Agent-ready Workroot

A registered Workroot can exist without Native Entry.

An agent-ready Workroot requires Native Entry.

## Acceptance

- `AGENTS.md` and `CLAUDE.md` generated from templates.
- generated files are ignored in bootstrap-dev.
- no private state path in generated entry.
- user content outside managed block preserved.
- default repo does not track generated entry files.



---

<!-- SOURCE: specs/012-system-health-doctor-migration.spec.md -->

# Spec 012 — System Health, Doctor, Maintenance, Migration

Status: accepted
Target: 0.9.530

## Purpose

Define diagnostics, maintenance, migration, and release validation.

## Doctor

Doctor is read-only by default.

Checks:

- WorkrootEnvironment exists.
- EnvironmentConfig schema valid.
- registry exists and is lockable.
- duplicate active directory binding absent.
- WorkrootRegistration points to valid state directory.
- Workroot state has expected structure.
- Native Entry is safe.
- generated entry files are ignored under bootstrap-dev.
- SQLite schema valid.
- relationship tables valid.
- release records valid.
- redacted/deleted content not present in ordinary indexes/context.
- index manifests and health valid.
- migrations recorded.
- Public Seed active root retired.

## Maintenance

Maintenance actions are explicit:

```text
reindex
compact
backup
restore
prune
repair
```

Doctor may recommend these but not run them by default.

## Migration

MigrationRecord fields:

```text
migration_id
scope
version
status
started_at
completed_at
backup_ref
error
```

Scopes:

```text
environment
workroot
storage
index
```

## Release validation

Before tag:

- full tests pass;
- smoke tests pass;
- negative tests pass;
- docs/specs are consistent;
- active root free of retired seed files;
- branch final report produced.

## Acceptance

- `workroot doctor` runs clean in a fresh Clean Workroot.
- Doctor reports registry/index/schema/release/native-entry state.
- Doctor does not mutate without explicit flag.
- Migration records exist and are queryable.



---

<!-- SOURCE: specs/013-storage-sqlite-schema.spec.md -->

# Spec 013 — Storage and SQLite Schema

Status: accepted
Target: 0.9.530

## Purpose

Define storage schema direction for new core model.

## Storage principles

- SQLite can hold canonical state and derived read models.
- Do not call all SQLite data cache.
- Relationship Network canonical tables are not cache.
- FTS/candidates/projections are derived.
- Environment registry may remain JSONL in 0.9.530 but has domain model.

## Required schema areas

### migrations

```text
schema_migrations
```

### workroot management

```text
workroots
directory_bindings
workroot_aliases
workroot_relationships
```

Environment-level records may be JSONL initially, but schema must be documented.

### assets

```text
assets
asset_surfaces
asset_publications
asset_path_history
asset_provenance
```

Remove top-level `knowledge_items` as active model. If old table remains for compatibility, it must map to `assets(asset_type='knowledge')`.

### release control

```text
release_records
tombstones
redactions
deletion_records
release_propagation_events
```

### work

```text
tasks
agent_runs
work_actions
work_checkpoints
retrieval_cards
invalidation_records
handoffs
work_events
operation_transactions
```

### relationships

Preferred:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

Compatibility views for `graph_*` may exist if needed.

### retrieval/index

```text
indexes
index_manifests
index_builds
index_invalidations
indexed_files
indexed_chunks
indexed_chunks_fts
context_candidates
context_candidates_fts
global_index_entries
```

### context

```text
context_packages
context_traces
candidate_selections
budget_trim_decisions
```

### system health

```text
doctor_runs
diagnostic_findings
maintenance_actions
```

## Redaction/deletion requirements

Derived tables must not keep redacted/deleted details.

Doctor must be able to check derived stores for violations.

## Acceptance

- schema migration path documented.
- old `knowledge_items` not treated as top-level domain.
- relationship tables exist.
- release tables exist.
- index manifest/build/invalidation tables exist.
- redacted/deleted negative tests pass.



---

<!-- SOURCE: specs/014-cli-user-flows.spec.md -->

# Spec 014 — CLI User Flows

Status: accepted
Target: 0.9.530

## Primary commands

```text
workroot init
workroot list
workroot status
workroot context
workroot doctor
workroot bootstrap-dev
```

## Optional/future commands

These can be introduced when implementation is ready:

```text
workroot task ...
workroot asset ...
workroot release ...
workroot index ...
workroot relationship ...
```

## Legacy commands

Old seed commands must not appear as current Clean Workroot primary flow. If retained temporarily, put under:

```text
workroot legacy ...
```

## CLI rules

- CLI is thin.
- CLI calls runtime.
- CLI does not import storage directly.
- CLI help must not describe Public Seed as active architecture.
- CLI should use Clean Workroot wording.

## `workroot init`

Creates registered Workroot and optionally agent-ready entry.

## `workroot context`

Calls Context Control.

Required options:

```text
--agent
--cwd
--query
--mode
--target-tokens
--hard-token-limit
--debug
```

## `workroot bootstrap-dev`

Dogfood only. No commit/tag/push.

## Acceptance

- `python -m ai_workroot --help` works.
- `workroot --help` shows Clean Workroot primary commands.
- legacy commands hidden or namespaced.
- context exposes hard token limit.
- bootstrap-dev output confirms generated local entries are ignored.



---

<!-- SOURCE: specs/015-installation-scripts.spec.md -->

# Spec 015 — Installation Scripts

Status: accepted
Target: 0.9.530

## Purpose

Move user install scripts out of generic `scripts/` and separate user install from developer tooling.

## Target layout

```text
install/
  README.md
  unix/
    install.sh
  windows/
    install.ps1

scripts/
  dev/
    bootstrap-dev.sh
    bootstrap-dev.ps1
    validate-release.sh
```

## Rules

- `install/` is user-facing.
- `scripts/dev/` is developer-facing.
- Product core logic must not live in shell scripts.
- Install scripts should call packaged CLI or install package wrapper.

## Unix installer

Covers macOS/Linux for now.

Do not split macOS/Linux until behavior truly diverges.

## Windows installer

PowerShell script under `install/windows/install.ps1`.

## Acceptance

- old `scripts/compat/install.sh` and `scripts/compat/install.ps1` are wrappers or moved.
- docs point to new install paths.
- shell parse passes for unix installer.
- PowerShell parse/documented validation included where possible.



---

<!-- SOURCE: specs/016-source-layout-migration.spec.md -->

# Spec 016 — Source Layout Migration

Status: accepted
Target: 0.9.530

## Purpose

Migrate product logic from `scripts/` into `src/ai_workroot/` without losing capabilities.

## Strategy

1. Create new package structure.
2. Move or wrap CLI entry.
3. Move product logic gradually into core/runtime/storage/indexing/agent/cli.
4. Keep scripts as wrappers/dev utilities only.
5. Do not delete old capability until mapped and tested.

## Product logic target mapping

| Old script area | New module |
|---|---|
| workroot paths/state | core/environment + runtime/environment + storage/filesystem |
| sqlite schema | storage/sqlite |
| context guide | core/context + runtime/context + indexing providers |
| candidates/FTS | indexing/candidates + indexing/fts + storage/sqlite |
| bootstrap | runtime/bootstrap + agent/native_entry |
| agent entry | agent/native_entry |
| doctor | core/health + runtime/doctor |
| CLI | cli/ |
| install | install/ |

## Formatting requirement

All Python source must be normally formatted.

No collapsed one-line files.

Add validation:

- py_compile all `src` and remaining `scripts`.
- max line length guard for Python files, with reasonable threshold.
- JSON files pretty printed.

## Active tree quarantine

Move or retire:

```text
space/
.workroot/
AGENTS.md
CLAUDE.md
.idea/
```

## Acceptance

- `src/ai_workroot` importable.
- `python -m ai_workroot --help` works.
- remaining scripts are wrappers/dev only.
- old capabilities have mapping and tests.



---

<!-- SOURCE: specs/017-release-validation.spec.md -->

# Spec 017 — Release Validation

Status: accepted
Target: 0.9.530

## Required validation before tag

```text
python3 -m py_compile $(find src -name "*.py")
python3 -m py_compile scripts/*.py  # if remaining scripts exist
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release  # until replaced or retired
python3 -m ai_workroot --help
git diff --check
```

## Smoke tests

- Clean Workroot init.
- Native Agent Entry authorization.
- Native Agent Entry local ignored under bootstrap-dev.
- bootstrap-dev first run.
- bootstrap-dev second run idempotency.
- Context Control package generation.
- Context Trace generation.
- Asset publication staging/publish.
- Release Control redaction/deletion protection.
- Tombstone visible/traceable.
- Relationship Network relationship creation/traversal.
- Retrieval & Index Control global/workroot index status.
- Doctor check.
- Migration check.

## Git hygiene

These must be empty unless fixture/history paths are explicitly allowed:

```text
git ls-files | grep '^AGENTS.md$'
git ls-files | grep '^CLAUDE.md$'
git ls-files | grep '^space/'
git ls-files | grep '^.workroot/'
git ls-files | grep '^.idea/'
```

## Docs validation

- README reflects Clean Workroot.
- ROADMAP reflects 0.9.530 reset.
- specs have statuses.
- ADRs exist.
- Public Seed only appears in history/retired context.
- Core terms are consistent.

## Final report

Codex must produce final report with:

- commit hash;
- changed file summary;
- validation command outputs;
- smoke outputs;
- known limitations;
- items deferred intentionally.



---

<!-- SOURCE: specs/018-codex-execution-plan.spec.md -->

# Spec 018 — Codex Execution Plan

Status: accepted
Target: 0.9.530

## Branch

Use:

```text
feat/0.9.530-clean-workroot-domain-reset
```

## Execution order

Codex must follow this order.

### Phase 0 — Baseline

- Create branch.
- Record current status.
- Run current tests if feasible.
- Do not tag.

### Phase 1 — Source of truth docs

- Add architecture docs.
- Add ADRs.
- Add specs with statuses.
- Add legacy preservation matrix.

### Phase 2 — New package scaffold

- Add `pyproject.toml` if missing.
- Create `src/ai_workroot/` structure.
- Add module placeholders with minimal importable code.
- Add `python -m ai_workroot --help` path.

### Phase 3 — Contracts

- Add `contracts/` protocols/DTOs.
- Ensure contracts do not import core.

### Phase 4 — Core models

- Add core files.
- Implement minimal rich models and policies.
- Do not over-split files.

### Phase 5 — Storage and environment

- Move environment/state path logic.
- Add WorkrootEnvironment model support.
- Add registry lock and registry store implementation.
- Update SQLite schema/migrations.

### Phase 6 — Agent Interface

- Move templates.
- Add local generated entry behavior.
- Update `.gitignore`.
- Remove root tracked AGENTS/CLAUDE.

### Phase 7 — bootstrap-dev

- Add `workroot.project.json`.
- Rewrite bootstrap-dev identity.
- Remove dependency on root AGENTS and `.workroot/kernel/VERSION`.
- Ensure idempotency.

### Phase 8 — Retrieval & Index Control

- Implement index manifests/build/health basics.
- Implement FTS/candidate provider integration.
- Implement global index projections.
- Implement release-aware filtering for redacted/deleted.

### Phase 9 — Relationship Network

- Rename business docs/code to relationships.
- Add/modify schema for relationship nodes/edges/evidence.
- Maintain compatibility if required.

### Phase 10 — Context Control

- Rename Context Guide docs to Context Control.
- Keep CLI `workroot context`.
- Ensure hard token limit conservative.
- Ensure trace includes release/relationship/index details.

### Phase 11 — Asset and Release Control

- Implement Asset unified model.
- Merge knowledge/decision/result into Asset types.
- Implement ReleaseRecord/Tombstone/Redaction/DeletionRecord basics.
- Enforce redaction/deletion strict protection.

### Phase 12 — System Health

- Update doctor checks.
- Add import-boundary checks.
- Add Public Seed retirement checks.
- Add release/index/schema checks.

### Phase 13 — Public Seed quarantine

- Move/delete active root `space/`, `.workroot/`, `AGENTS.md`, `CLAUDE.md`, `.idea/`.
- Preserve history/fixtures if useful.

### Phase 14 — Tests

- Add/modify unit, integration, smoke, negative tests.
- Ensure no old tests enforce Public Seed active structure.

### Phase 15 — Final docs sweep

- README
- START_HERE_FOR_HUMANS
- ROADMAP
- CHANGELOG
- release note
- docs/specs/README
- docs/history/public-seed.md

### Phase 16 — Validation and report

- Run all validations.
- Produce final report.
- Do not tag until user approves.

## Codex rules

- Do not invent new domain names.
- Do not delete legacy capability without matrix entry.
- Do not add remote LLM/embedding/vector dependencies.
- Do not commit generated root AGENTS/CLAUDE.
- Do not reintroduce Public Seed as active architecture.
- Keep implementation lightweight.



---

<!-- SOURCE: specs/019-full-test-and-migration-plan.spec.md -->

# Spec 019 — Full Test and Migration Plan

Status: accepted
Applies to: 0.9.530

## Purpose

This spec binds implementation to explicit migration and test coverage. 0.9.530 is too large to rely on normal happy path tests.

## Migration requirements

1. Preserve old Public Seed material in history/fixtures before removing from active root.
2. Back up old SQLite DB before destructive schema changes.
3. Do not rely on root AGENTS/CLAUDE or `.workroot/kernel/VERSION` for bootstrap-dev.
4. Replace global user profile with operator preferences and policy defaults.
5. Convert knowledge/decision/result concepts to Asset subtypes.
6. Convert Graph business language to Relationship Network.
7. Preserve old run/action/checkpoint/retrieval-card/invalidation capabilities.
8. Preserve release/tombstone/redaction/deletion semantics.

## Test requirements

1. Unit tests for core behavior.
2. Contract import isolation tests.
3. Storage/schema integration tests.
4. Runtime flow tests.
5. Indexing provider tests.
6. Context Control tests.
7. Agent Interface tests.
8. Release Control protection tests.
9. Relationship Network tests.
10. System Health / Doctor tests.
11. bootstrap-dev smoke.
12. Clean Workroot smoke.
13. Negative tests for retired Public Seed assumptions.

## Acceptance

Implementation is incomplete if it lacks either migration handling or negative tests.



---

<!-- SOURCE: specs/020-documentation-rewrite.spec.md -->

# Spec 020 — Documentation Rewrite

Status: accepted
Applies to: 0.9.530

## Purpose

All public docs must describe the current Clean Workroot architecture. Public Seed must be historical only.

## Required rewrites

- README.md
- ROADMAP.md
- START_HERE_FOR_HUMANS.md if retained
- CHANGELOG.md
- docs/architecture-map.md
- docs/workroot-system-design.md
- docs/kernel-implementation-specification.md
- docs/specs/README.md
- docs/releases/0.9.530.md

## Required additions

```text
docs/architecture/clean-workroot-architecture.md
docs/architecture/final-core-concepts.md
docs/architecture/lightweight-core-runtime-architecture.md
docs/architecture/runtime-layout.md
docs/architecture/relationship-network.md
docs/architecture/retrieval-index-control.md
docs/architecture/release-control.md
docs/architecture/workroot-environment.md
docs/history/public-seed.md
```

## Language rules

Forbidden active-architecture language:

```text
Current Public Seed
space/ + .workroot as current layout
Memory as formal domain
Mind as formal domain
Graph as business domain
Context Gate
TombstoneMarker
```

Required active-architecture language:

```text
Clean Workroot
WorkrootEnvironment
Core / Contracts / Runtime / Storage / Indexing / Agent / CLI
Relationship Network
Retrieval & Index Control
Release Control
Tombstone
Agent Interface
```

## Acceptance

Run textual audit:

```bash
grep -R "Current Public Seed" README.md docs || true
grep -R "Context Gate" README.md docs src || true
grep -R "TombstoneMarker" README.md docs src || true
grep -R "Memory" README.md docs/src || true
```

Mentions inside `docs/history/` are allowed if clearly historical.



---

<!-- SOURCE: specs/021-codex-checkpoint-protocol.spec.md -->

# Spec 021 — Codex Checkpoint Protocol

Status: accepted
Applies to: 0.9.530

## Purpose

Codex must work in checkpoints because this release touches many files.

## Checkpoint rules

After each implementation phase, Codex must report:

1. Files changed.
2. Capabilities preserved.
3. Tests run.
4. Failures or risks.
5. Deviations from plan.
6. Next phase.

## Mandatory checkpoints

1. Documentation source of truth.
2. Source scaffold.
3. Legacy quarantine.
4. WorkrootEnvironment runtime.
5. Agent templates.
6. Storage/schema.
7. Core behavior.
8. Runtime flows.
9. Indexing.
10. Context Control.
11. Release Control protections.
12. Relationship Network.
13. Doctor.
14. CLI/install.
15. Tests.
16. Final docs and report.

## Stop conditions

Codex must stop and ask for review if:

- a legacy capability has no clear new owner;
- a migration would delete old files rather than quarantine;
- a test requires keeping active Public Seed layout;
- redaction/deletion protection cannot be enforced;
- contracts need to import core;
- implementation requires adding vector/search/remote LLM dependency;
- bootstrap-dev still requires root AGENTS/CLAUDE or `.workroot`.



---

<!-- SOURCE: specs/022-ci-and-release-gates.spec.md -->

# Spec 022 — CI and Release Gates

Status: accepted
Applies to: 0.9.530

## Required CI jobs

At minimum:

```text
Python compile
Unit tests
Integration tests
Smoke tests
Release validation
Git diff check
Install script syntax check
```

Example commands:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release
git diff --check
bash -n install/unix/install.sh
```

PowerShell parse should be included if available. If not, document limitation.

## Release gate

Before tag:

1. Final report complete.
2. Acceptance checklist complete.
3. Negative tests complete.
4. Smoke tests complete.
5. Known limitations documented.
6. Human review approves tag.

## No automatic tag

Codex must not tag unless explicitly instructed after review.



---

<!-- SOURCE: execution/001-implementation-order-and-checkpoints.md -->

# Implementation Order and Checkpoints

This plan is mandatory for Codex. The work is large and must not be done in random order.

## Phase 0 — Branch and baseline

Branch:

```text
feat/0.9.530-clean-workroot-domain-reset
```

Baseline commands:

```bash
python3 -m py_compile scripts/*.py
python3 scripts/compat/validate_kernel.py --release
python3 -m unittest discover -s tests -v
```

If baseline tests fail because old Public Seed contracts conflict with new architecture, record them in the implementation report before modifying them.

Checkpoint output:

- branch name
- current commit
- baseline test result
- known baseline failures

## Phase 1 — Documentation source of truth

Create/update:

```text
docs/architecture/
docs/specs/
docs/adr/
docs/history/
docs/dev/
```

Required docs:

- Architecture overview.
- Final core concepts and boundaries.
- Engineering structure.
- Runtime layout.
- Legacy capability preservation matrix.
- Dependency rules.
- Clean Workroot installation spec.
- WorkrootEnvironment managed state spec.
- Bootstrap-dev dogfood spec.
- Core model spec.
- Storage/schema spec.
- Testing plan.
- Release validation plan.

Checkpoint:

- docs exist
- old Public Seed active language removed or marked retired
- spec statuses updated

## Phase 2 — Source scaffold

Create target structure:

```text
src/ai_workroot/core/
src/ai_workroot/contracts/
src/ai_workroot/runtime/
src/ai_workroot/storage/
src/ai_workroot/indexing/
src/ai_workroot/agent/
src/ai_workroot/cli/
src/ai_workroot/resources/
```

Add `pyproject.toml` entry points if missing.

Checkpoint:

```bash
python3 -m py_compile $(find src -name "*.py")
python3 -m ai_workroot --help
```

## Phase 3 — Legacy active-tree quarantine

Quarantine active Public Seed artifacts:

```text
space/      -> docs/history/ or tests/fixtures/legacy-public-seed-history/
.workroot/  -> docs/history/ or tests/fixtures/legacy-public-seed-history/
AGENTS.md   -> remove from tracked root, replace with template
CLAUDE.md   -> remove from tracked root, replace with template
.idea/      -> remove from Git
```

Do not delete historical information without preserving it.

Checkpoint:

```bash
git ls-files | grep '^AGENTS.md$'      # empty
git ls-files | grep '^CLAUDE.md$'      # empty
git ls-files | grep '^space/'          # empty unless fixture/history path
git ls-files | grep '^.workroot/'      # empty unless fixture/history path
git ls-files | grep '^.idea/'          # empty
```

## Phase 4 — WorkrootEnvironment and runtime state

Implement WorkrootEnvironment and managed state layout.

Required changes:

- Global `user/profile.md` retired.
- Operator preferences and policy defaults introduced.
- Registry remains canonical global state.
- Global index remains derived read model.
- Global cache is not knowledge.

Checkpoint:

- init creates correct AI_WORKROOT_HOME layout
- duplicate binding rejected
- registry lock works
- doctor validates environment

## Phase 5 — Agent Interface

Implement templates and local generation:

```text
templates/native-agent-entry/AGENTS.md.template
templates/native-agent-entry/CLAUDE.md.template
src/ai_workroot/resources/templates/native-agent-entry/
```

`.gitignore` must contain:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

Checkpoint:

- bootstrap-dev generates local root AGENTS/CLAUDE
- generated files ignored
- templates contain only launcher instructions
- no state path or Workroot ID leaks

## Phase 6 — Storage and schema

Implement schema aligned with:

- WorkrootEnvironment
- Asset unified model
- Release Control
- Relationship Network
- Retrieval & Index Control
- Context Control
- System Health

Checkpoint:

- schema_migrations present
- no top-level `knowledge_items` as canonical domain table
- relationship tables exist
- release tables exist
- index tables exist
- redaction/deletion protection fields present

## Phase 7 — Core behavior

Implement core files lightly:

```text
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

Do not create one class per file unless necessary.

Checkpoint:

- unit tests for entity behavior
- no infrastructure imports in core

## Phase 8 — Runtime orchestration

Implement flows:

- initialize environment
- init Clean Workroot
- bootstrap-dev
- generate context
- publish/stage asset
- create release/tombstone/redaction/deletion
- refresh indexes
- run doctor

Checkpoint:

- CLI calls runtime
- runtime wires contracts/adapters
- old scripts are wrappers only where needed

## Phase 9 — Indexing and retrieval

Implement:

- global indexes
- workroot indexes
- FTS
- Context candidates
- relationship traversal projection
- release-aware index entries
- provider contracts/adapters

Checkpoint:

- indexing refresh works
- retrieval result includes source/provider metadata
- redacted/deleted content is not exposed
- tombstone can be annotated/traced

## Phase 10 — Context Control

Implement:

- ContextRequest
- ContextBudget
- hard token fallback
- retrieval provider usage
- relationship signal usage
- release state annotation/protection
- ContextPackage
- ContextTrace

Checkpoint:

- context command works
- trace records selection/drop/budget/release information
- context does not write user directory

## Phase 11 — System Health

Doctor checks:

- Environment config
- registry integrity
- duplicate bindings
- state directory boundary
- SQLite schema
- relationship tables
- release propagation
- index health
- agent entry safety
- bootstrap-dev ignored files
- legacy active root not present

Checkpoint:

- doctor PASS on clean environment
- negative cases produce WARN/FAIL

## Phase 12 — Tests and validation

Run full validation and update tests.

Required:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release
git diff --check
git status --short
```

Checkpoint:

- acceptance checklist passed
- negative tests passed
- final report produced

## Phase 13 — As-built docs and release note

Update:

- README
- START_HERE_FOR_HUMANS if retained
- ROADMAP
- CHANGELOG
- docs/releases/0.9.530.md
- docs/specs statuses
- docs/architecture as-built notes

Checkpoint:

- no active Public Seed language
- release notes mention architecture reset
- validation output included



---

<!-- SOURCE: execution/002-migration-and-quarantine-plan.md -->

# Migration and Quarantine Plan

## 1. Principles

- Do not silently delete old capability evidence.
- Do not keep old Public Seed as active architecture.
- Preserve old files in history/fixtures when useful.
- Treat 0.9.530 as an architecture reset with minimal real-user migration obligations.
- Rebuild derived data when safe; back up canonical relationship/release/asset/work records before destructive migration.

## 2. Active source tree migration

### Root files/directories

| Old path | Action | New location |
|---|---|---|
| `space/` | Quarantine | `docs/history/public-seed/space/` or `tests/fixtures/legacy-public-seed-history/space/` |
| `.workroot/` | Quarantine | `docs/history/public-seed/.workroot/` or fixture |
| `AGENTS.md` | Remove from tracked root | `templates/native-agent-entry/AGENTS.md.template` |
| `CLAUDE.md` | Remove from tracked root | `templates/native-agent-entry/CLAUDE.md.template` |
| `.idea/` | Remove from Git | none |
| `scripts/compat/install.sh` | Move/wrap | `install/unix/install.sh` |
| `scripts/compat/install.ps1` | Move/wrap | `install/windows/install.ps1` |
| product logic in `scripts/*.py` | Migrate | `src/ai_workroot/*` |
| dev helper scripts | Move | `scripts/dev/` |

## 3. Documentation migration

Old docs must be rewritten or retired:

| Old doc | Action |
|---|---|
| README Public Seed sections | Rewrite to Clean Workroot |
| ROADMAP Public Seed P0 | Rewrite |
| docs/workroot-system-design.md | Rewrite or replace |
| docs/architecture-map.md | Rewrite |
| docs/kernel-implementation-specification.md | Mark retired or replace with release validation spec |
| old specs with Draft status | Update status and content |
| old handoffs/review notes | Move to `docs/dev/` or remove if obsolete |

## 4. Managed state migration

### Environment-level

Current global layout contains `user/profile.md`, `preferences.md`, and `global-principles.md`. New model should not create global user profile.

Action:

- Replace with `preferences/operator-preferences.json` and `preferences/policy-defaults.json`.
- If old files exist, preserve as `docs/history` in source or as environment backup in runtime, but do not treat as active global profile.

### Per-Workroot

New per-Workroot layout should include:

```text
workroot.json
charter/
state/
tasks/
handoffs/
assets/
release/
relationships/
indexes/
context/
diagnostics/
maintenance/
cache/
logs/
```

If old `knowledge/` exists, migrate conceptually to `assets/` with `asset_type=knowledge` or keep as legacy directory only until runtime migration.

## 5. SQLite migration

### Required precondition

Before schema migration, run backup where old DB exists:

```text
cache/workroot.sqlite -> cache/backups/workroot.sqlite.<timestamp>.bak
```

### New canonical/derived split

Canonical:

- workroots / registrations
- tasks / runs / actions / checkpoints / handoffs
- assets
- release records / tombstones / redactions / deletion records
- relationship nodes / edges / evidence
- migrations

Derived:

- indexed files / chunks
- FTS rows
- context candidates
- global navigation indexes
- relationship traversal projections
- context package history unless explicitly retained as diagnostics

### Table direction

Old top-level `knowledge_items` must not remain the canonical knowledge table. Knowledge becomes:

```text
assets.asset_type = 'knowledge'
```

Old `graph_nodes` / `graph_edges` should become:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

If implementation risk is high, compatibility views may be created temporarily, but docs must use Relationship Network.

## 6. CLI migration

Old main commands:

```text
init
list
status
context
doctor
bootstrap-dev
```

Legacy seed commands must not appear as Clean Workroot primary flow. They may be moved under:

```text
workroot legacy ...
```

or kept as hidden/compat wrappers with clear warning.

## 7. Test migration

Tests that assert active Public Seed layout must be rewritten or moved to legacy fixture tests. No current architecture test may require root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.

## 8. Rollback approach

Because source tree migration is large, Codex must commit/checkpoint per phase. If a phase fails, revert that phase rather than rolling back the whole branch.

Do not tag until final validation passes.



---

<!-- SOURCE: execution/003-testing-plan.md -->

# Testing Plan

## 1. Test structure

Target structure:

```text
tests/unit/
tests/integration/
tests/smoke/
tests/fixtures/
```

## 2. Unit tests

### Core model

Test core files:

- environment.py
- work.py
- assets.py
- release.py
- relationships.py
- retrieval.py
- context.py
- agent.py
- health.py
- extensions.py

Required unit cases:

- Task status transitions.
- TaskKind and TaskProcessLevel behavior.
- Task decomposition policy decisions.
- Asset publication state transitions.
- Asset fingerprint/path history behavior.
- ReleaseRecord and Tombstone behavior.
- Redaction/deletion protection rules.
- RelationshipEdge validation.
- IndexManifest stale/refresh decisions.
- ContextBudget trim decisions.
- Native Agent Entry managed block validation.

## 3. Contracts tests

Contracts must be importable without core/runtime/storage/indexing/agent/cli.

Test:

```python
import ai_workroot.contracts.storage
import ai_workroot.contracts.retrieval
import ai_workroot.contracts.filesystem
```

and verify contracts do not import `ai_workroot.core`.

## 4. Storage integration tests

Required:

- SQLite schema initialization.
- schema_migrations table.
- relationship tables.
- release tables.
- asset tables.
- index tables.
- backup before migration.
- JSONL registry lock behavior.
- duplicate user directory rejection.
- WorkrootEnvironment config creation.

## 5. Indexing integration tests

Required:

- global workroot index creation.
- workroot task/asset index creation.
- FTS index refresh.
- ContextCandidate generation.
- Relationship traversal projection.
- release-aware index annotation.
- redacted/deleted content not exposed by index result.
- tombstone result is traceable/annotated.

## 6. Context Control tests

Required:

- context package generated from Clean Workroot.
- Context Control uses retrieval providers, not direct SQLite.
- Context Trace records selected/dropped candidates.
- hard token limit fallback.
- relationship signal inclusion.
- release/tombstone/redaction/deletion handling.
- no user-directory writes.

## 7. Agent Interface tests

Required:

- templates exist.
- templates are short launchers.
- generated AGENTS.md / CLAUDE.md are local and ignored.
- no absolute state path.
- no Workroot ID leak.
- managed block replacement preserves user content.

## 8. bootstrap-dev tests

Required:

- identifies repo by workroot.project.json.
- does not require root AGENTS.md.
- does not require .workroot/kernel/VERSION.
- initializes Clean Workroot state.
- creates .ai-workroot-local/.
- generated files are ignored.
- second run is idempotent.
- concurrent run does not duplicate registry records.
- no commit/tag/push.

## 9. System Health tests

Required doctor checks:

- environment exists.
- config schema correct.
- registry valid.
- no duplicate active binding.
- state path under AI_WORKROOT_HOME.
- SQLite schema valid.
- relationship tables valid.
- release records valid.
- index health valid.
- agent entry safe.
- legacy active root absent.
- .idea not tracked.

## 10. Smoke tests

Smoke scripts should cover:

- clean init with temporary user directory.
- init with Native Agent Entry authorized.
- context command output.
- bootstrap-dev first run.
- bootstrap-dev second run.
- doctor after init.
- release/tombstone creation if CLI exists; otherwise runtime test.
- index refresh.

## 11. Full validation commands

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release
git diff --check
git status --short
```

If `validate_kernel.py` is retired or replaced, create a new release validation script and document it.



---

<!-- SOURCE: execution/004-negative-test-plan.md -->

# Negative Test Plan

Negative tests are mandatory. A green happy path is not enough.

## 1. Retired Public Seed tests

- Root `space/` must not be required.
- Root `.workroot/` must not be required.
- Root committed `AGENTS.md` must not be required.
- Root committed `CLAUDE.md` must not be required.
- bootstrap-dev must fail if it still checks `.workroot/kernel/VERSION`.
- README/ROADMAP must not describe Public Seed as current architecture.

## 2. User directory contamination tests

- `workroot init` must not create `.workroot/` in user directory.
- `workroot init` must not create `.ai-workroot/` in user directory.
- `workroot init` must not treat user-created `logs/`, `cache/`, `state/`, or `context/` as managed state.
- Context Control must not write ContextPackage or ContextTrace to user directory.

## 3. Native Agent Entry negative tests

- Generated entry must not contain AI_WORKROOT_HOME.
- Generated entry must not contain per-Workroot state path.
- Generated entry must not contain Workroot ID.
- Generated entry must not include handoffs/logs/indexes/debug paths.
- Managed block update must not delete user content outside block.
- Entry files must be Git ignored in bootstrap-dev.

## 4. Release Control negative tests

- Redacted content must not appear in normal ContextPackage.
- Deleted content must not appear in indexes or normal ContextPackage.
- Deleted content must not be preserved in hidden FTS rows.
- Tombstone must not be auto-created without explicit decision.
- Tombstone must not mutate TaskStatus or Asset core identity.
- Tombstone must be visible/traceable if explicitly queried.
- Tombstone must not be hard-excluded in 0.9.530 unless explicit policy says so.

## 5. Relationship Network negative tests

- New docs/code must not use Graph as business domain name.
- Relationship traversal projection loss must not delete RelationshipEdge truth.
- RelationshipEdge must require valid RelationshipType.
- Cross-Workroot relationship traversal must not be used for default context recall.

## 6. Retrieval & Index Control negative tests

- Contracts must not import core.
- Indexing must not call CLI.
- Context Control must not directly query SQLite FTS.
- Retrieval provider failure must be recorded and handled.
- Redacted/deleted records must invalidate or suppress affected index entries.
- Vector/search provider must remain reserved; no actual dependency introduced.

## 7. Storage/schema negative tests

- `knowledge_items` must not be canonical knowledge table.
- Graph table names must not be introduced as new business docs. If compatibility tables remain, docs must explain them as technical compatibility.
- schema_migrations missing must cause doctor warning/fail.
- old DB migration must back up before destructive change.

## 8. WorkrootEnvironment negative tests

- Duplicate active directory binding must fail.
- Unsafe Workroot ID must fail.
- State directory escaping AI_WORKROOT_HOME must fail.
- Global preferences must not become global knowledge/profile store.
- Global index must not contain knowledge body.

## 9. Git hygiene negative tests

- `.idea/` must not be tracked.
- `/AGENTS.md` must not be tracked.
- `/CLAUDE.md` must not be tracked.
- `/.ai-workroot-local/` must not be tracked.
- Generated bootstrap-dev files must not appear in `git status --short` except ignored files.



---

<!-- SOURCE: execution/005-acceptance-checklist-final.md -->

# Final Acceptance Checklist

## 1. Source tree

- [ ] `src/ai_workroot/core` exists.
- [ ] `src/ai_workroot/contracts` exists.
- [ ] `src/ai_workroot/runtime` exists.
- [ ] `src/ai_workroot/storage` exists.
- [ ] `src/ai_workroot/indexing` exists.
- [ ] `src/ai_workroot/agent` exists.
- [ ] `src/ai_workroot/cli` exists.
- [ ] `install/unix/install.sh` exists.
- [ ] `install/windows/install.ps1` exists.
- [ ] `scripts/dev/` exists.
- [ ] `workroot.project.json` exists.

## 2. Retired active root

- [ ] Root `space/` not active.
- [ ] Root `.workroot/` not active.
- [ ] Root `AGENTS.md` not tracked.
- [ ] Root `CLAUDE.md` not tracked.
- [ ] `.idea/` not tracked.
- [ ] Public Seed preserved only in history/fixtures if needed.

## 3. Docs

- [ ] README describes Clean Workroot, not Public Seed.
- [ ] ROADMAP updated.
- [ ] Architecture docs updated.
- [ ] Specs detailed and status-managed.
- [ ] ADRs present.
- [ ] docs/history/public-seed.md exists.
- [ ] docs/releases/0.9.530.md exists.

## 4. Runtime

- [ ] AI_WORKROOT_HOME creates WorkrootEnvironment structure.
- [ ] No global user profile body store.
- [ ] Operator preferences / policy defaults exist.
- [ ] WorkrootCharter is per Workroot.
- [ ] Registry lock exists.
- [ ] Duplicate directory binding rejected.

## 5. Storage/schema

- [ ] schema_migrations present.
- [ ] Asset table supports asset_type for knowledge/decision/result.
- [ ] Release Control tables present.
- [ ] Relationship Network tables present.
- [ ] Index tables/read models present.
- [ ] Context tables present.
- [ ] Doctor validates schema.

## 6. Release Control

- [ ] ReleaseRecord exists.
- [ ] Tombstone exists and is named Tombstone.
- [ ] Redaction exists.
- [ ] DeletionRecord exists.
- [ ] Redacted/deleted content protection implemented.
- [ ] Tombstone visible/traceable but not aggressively excluded by default.

## 7. Relationship Network

- [ ] Business docs use Relationship Network.
- [ ] RelationshipEdge canonical truth exists.
- [ ] RelationshipEvidence exists.
- [ ] Relationship traversal projection is treated as index/read model.

## 8. Retrieval & Index Control

- [ ] Global index implemented or scaffolded.
- [ ] Workroot-level index implemented or scaffolded.
- [ ] ContextCandidate remains read model.
- [ ] FTS implemented or migrated.
- [ ] Provider contracts exist.
- [ ] Reserved vector/search adapters introduce no real dependency.

## 9. Context Control

- [ ] Command `workroot context` works.
- [ ] Uses retrieval providers via contracts/runtime.
- [ ] Generates ContextPackage.
- [ ] Generates ContextTrace.
- [ ] Does not write user directory.
- [ ] Hard token fallback works.

## 10. Agent Interface

- [ ] Templates committed.
- [ ] Local root entries generated by bootstrap-dev.
- [ ] User Clean Workroot entries generated only after authorization.
- [ ] Entry files are safe and short.
- [ ] Entry files are ignored in bootstrap-dev.

## 11. System Health

- [ ] `workroot doctor` works.
- [ ] Doctor checks environment, registry, schema, indexes, release, relationship, native entry.
- [ ] Doctor default is read-only.

## 12. Commands

Run:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release
git diff --check
git status --short
```

Git checks:

```bash
git ls-files | grep '^AGENTS.md$'      # must be empty
git ls-files | grep '^CLAUDE.md$'      # must be empty
git ls-files | grep '^space/'          # must be empty unless history/fixture path
git ls-files | grep '^.workroot/'      # must be empty unless history/fixture path
git ls-files | grep '^.idea/'          # must be empty
```



---

<!-- SOURCE: execution/006-release-validation-and-final-report.md -->

# Release Validation and Final Report

## 1. Required final report sections

Codex must provide a final report with:

1. Branch and commit hash.
2. Summary of implemented architecture changes.
3. Files moved/quarantined.
4. Legacy capability preservation matrix status.
5. Schema changes.
6. Test results.
7. Smoke results.
8. Negative test results.
9. Known limitations.
10. Items deferred to next version.
11. Confirmation that no tag/release was created unless explicitly instructed.

## 2. Required command output

Include output for:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
python3 scripts/compat/validate_kernel.py --release
git diff --check
git status --short
```

If `scripts/compat/validate_kernel.py` is retired or replaced, provide the replacement command and reason.

## 3. Smoke scenarios

### Clean Workroot smoke

- Create temp user dir.
- Run init.
- Verify AI_WORKROOT_HOME state created.
- Verify user dir only contains authorized Native Agent Entry if enabled.
- Run context.
- Run doctor.

### bootstrap-dev smoke

- Run bootstrap-dev in repo.
- Verify workroot.project.json used.
- Verify local AGENTS/CLAUDE generated.
- Verify ignored.
- Run bootstrap-dev again.
- Verify idempotent.

### Release Control smoke

- Create Tombstone.
- Verify target object unchanged.
- Verify Tombstone visible/traceable.
- Create Redaction.
- Verify redacted content suppressed.
- Create DeletionRecord.
- Verify deleted content not exposed.

### Retrieval & Index Control smoke

- Refresh indexes.
- Query global workroot index.
- Query workroot task/asset index.
- Query FTS/candidates.
- Verify provider metadata in result.

### Relationship Network smoke

- Create relationship edge.
- Attach evidence.
- Query traversal projection.
- Verify relationship truth remains canonical.

## 4. Known limitations to document

If not fully implemented, document:

- Vector/search providers are reserved only.
- Extensions remain reserved/lightweight.
- Complex Tombstone exclusion policy deferred.
- Full user-file rename/move/delete resolver may be partial.
- Legacy Public Seed automatic migration not supported.

## 5. Tagging

Do not tag until human review approves final report.



---

<!-- SOURCE: validation/acceptance-checklist.md -->

# Acceptance Checklist

## Architecture

- [ ] Public Seed retired as active architecture.
- [ ] Clean Workroot and bootstrap-dev dogfood are the only active scenarios.
- [ ] Core terms are consistent.
- [ ] No `Memory` as formal domain term.
- [ ] No `Graph` as business domain term.
- [ ] `Tombstone` entity named correctly.
- [ ] Relationship Network docs/specs exist.
- [ ] Retrieval & Index Control docs/specs exist.
- [ ] WorkrootEnvironment docs/specs exist.

## Source tree

- [ ] `src/ai_workroot/core` exists.
- [ ] `src/ai_workroot/contracts` exists.
- [ ] `src/ai_workroot/runtime` exists.
- [ ] `src/ai_workroot/storage` exists.
- [ ] `src/ai_workroot/indexing` exists.
- [ ] `src/ai_workroot/agent` exists.
- [ ] `src/ai_workroot/cli` exists.
- [ ] user install scripts under `install/`.
- [ ] scripts are dev wrappers only.

## Git hygiene

- [ ] root `AGENTS.md` not tracked.
- [ ] root `CLAUDE.md` not tracked.
- [ ] root `space/` not active tracked.
- [ ] root `.workroot/` not active tracked.
- [ ] `.idea/` not tracked.
- [ ] `.gitignore` ignores `/AGENTS.md`, `/CLAUDE.md`, `/.ai-workroot-local/`.

## WorkrootEnvironment

- [ ] `AI_WORKROOT_HOME` maps to WorkrootEnvironment.
- [ ] global config exists.
- [ ] global registry exists.
- [ ] registry lock exists.
- [ ] global preferences are not user profile.
- [ ] global index treated as derived read model.

## bootstrap-dev

- [ ] uses `workroot.project.json`.
- [ ] does not require root AGENTS.
- [ ] does not require `.workroot/kernel/VERSION`.
- [ ] creates local generated entry files.
- [ ] creates `.ai-workroot-local/`.
- [ ] no commit/tag/push.
- [ ] idempotent second run.

## Asset

- [ ] Asset unifies knowledge/decision/result.
- [ ] Asset publication policy exists.
- [ ] Published Asset only writes user directory.
- [ ] ContextPackage/Trace/Candidate/FTS row are not Assets.
- [ ] path history/fingerprint fields exist or are reserved.

## Release Control

- [ ] ReleaseRecord exists.
- [ ] Tombstone exists.
- [ ] Redaction exists.
- [ ] DeletionRecord exists.
- [ ] Tombstone does not mutate target object.
- [ ] redacted/deleted strictly protected.
- [ ] tombstone visible/traceable but not hard excluded in 0.9.530.

## Relationship Network

- [ ] RelationshipNode/Edge/Evidence exists.
- [ ] docs use Relationship Network.
- [ ] Relationship traversal projection is derived.

## Retrieval & Index Control

- [ ] Index manifest/build/health exists.
- [ ] environment/global index scope exists.
- [ ] workroot index scope exists.
- [ ] candidate/FTS/text providers exist.
- [ ] release-aware filtering prevents redacted/deleted leakage.

## Context Control

- [ ] CLI remains `workroot context`.
- [ ] docs/specs use Context Control.
- [ ] ContextPackage generated.
- [ ] ContextTrace generated.
- [ ] hard token limit conservative.
- [ ] no user directory write by Context Control.

## System Health

- [ ] Doctor checks environment.
- [ ] Doctor checks registry.
- [ ] Doctor checks schema.
- [ ] Doctor checks index health.
- [ ] Doctor checks Native Entry safety.
- [ ] Doctor read-only by default.

## Validation commands

- [ ] `python3 -m py_compile $(find src -name "*.py")`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] `python3 -m ai_workroot --help`
- [ ] `git diff --check`
- [ ] relevant smoke commands recorded.



---

<!-- SOURCE: validation/negative-tests.md -->

# Negative Test Checklist

Codex must add or update tests for these negative cases.

## Retired Public Seed

- [ ] bootstrap-dev must not require root `AGENTS.md`.
- [ ] bootstrap-dev must not require `.workroot/kernel/VERSION`.
- [ ] root tracked `AGENTS.md` fails Git hygiene check.
- [ ] root tracked `CLAUDE.md` fails Git hygiene check.
- [ ] active root tracked `space/` fails architecture check unless fixture/history.
- [ ] active root tracked `.workroot/` fails architecture check unless fixture/history.

## User directory

- [ ] user-created `logs/` must not be treated as managed state.
- [ ] user-created `cache/` must not be treated as managed state.
- [ ] ContextPackage must not write user directory.
- [ ] ContextTrace must not write user directory.
- [ ] Candidate/FTS rows must not write user directory.

## Native Agent Entry

- [ ] entry file containing state path fails validation.
- [ ] entry file containing Workroot ID fails validation.
- [ ] entry file containing debug trace path fails validation.
- [ ] entry update must preserve user content outside managed block.

## Release Control

- [ ] Redacted content cannot enter ContextPackage.
- [ ] Deleted content cannot enter ContextPackage.
- [ ] Deleted content cannot remain in FTS/candidate indexes.
- [ ] Tombstone does not mutate Task.status.
- [ ] Tombstone can target Task through ReleaseTargetRef.
- [ ] Tombstone is visible/traceable.
- [ ] Deletion cannot be auto-converted to Tombstone.

## Retrieval & Index Control

- [ ] Index provider must not bypass release/deletion filtering.
- [ ] Context Control must not call SQLite/FTS adapter directly if provider contract exists.
- [ ] Graph/relationship traversal projection loss does not delete canonical RelationshipEdge.
- [ ] Redacted/deleted entries cannot remain in global indexes.

## Relationship Network

- [ ] invalid relationship type rejected.
- [ ] relationship edge without valid nodes rejected or flagged.
- [ ] cross-Workroot relationship not allowed without explicit WorkrootRelationship/global policy.

## Contracts and imports

- [ ] `contracts` importing `core` fails import-boundary test.
- [ ] `core` importing `storage` fails import-boundary test.
- [ ] `cli` importing `storage` directly fails import-boundary test.

## Asset model

- [ ] `knowledge_items` as active top-level domain rejected.
- [ ] Decision not modeled as top-level separate domain.
- [ ] ContextPackage cannot be published as user asset unless explicit asset publication flow is used.
- [ ] Missing asset path does not delete asset identity.

## bootstrap-dev

- [ ] bootstrap-dev must not commit/tag/push.
- [ ] second bootstrap-dev run must not duplicate registry records.
- [ ] concurrent bootstrap-dev must not duplicate registry records.
- [ ] generated AGENTS/CLAUDE must be ignored.



---

<!-- SOURCE: adr/ADR-0001-clean-workroot-reset.md -->

# ADR-0001 — Clean Workroot Reset

Status: accepted

## Decision

Public Seed is retired as active architecture. Clean Workroot and bootstrap-dev dogfood are the only active scenarios.

## Rationale

The original seed structure mixed user space, system runtime, agent entry, kernel contracts, and project development files. Clean Workroot separates user assets from managed state and supports product usage and self-dogfood through the same architecture.

## Consequences

- `space/` and `.workroot/` leave active root.
- Root `AGENTS.md` / `CLAUDE.md` are local generated and ignored.
- Public Seed lives only in history or fixtures.



---

<!-- SOURCE: adr/ADR-0002-lightweight-core-runtime-architecture.md -->

# ADR-0002 — Lightweight Core/Runtime Architecture

Status: accepted

## Decision

Use DDD only for strategic modeling. Implement with `core / contracts / runtime / storage / indexing / agent / cli`.

## Rationale

Pure DDD directories are too heavy for an early open-source project. The chosen structure preserves domain clarity while keeping contributors oriented by practical modules.

## Consequences

- Core holds domain concepts.
- Contracts holds protocols.
- Runtime orchestrates.
- Storage/indexing/agent implement capabilities.
- CLI stays thin.



---

<!-- SOURCE: adr/ADR-0003-relationship-network-not-graph.md -->

# ADR-0003 — Relationship Network, not Graph

Status: accepted

## Decision

The business domain is named Relationship Network. Graph remains only a technical/implementation term.

## Rationale

AI Workroot maintains relationships among tasks, assets, releases, context packages, and agents. Calling the domain Graph overemphasizes a data structure or graph database implementation.

## Consequences

- Use RelationshipNode/RelationshipEdge/RelationshipEvidence in core language.
- Graph traversal/projection may still appear in indexing/technical docs.



---

<!-- SOURCE: adr/ADR-0004-release-control-and-tombstone.md -->

# ADR-0004 — Release Control and Tombstone

Status: accepted

## Decision

Release Control is a core domain. Tombstone is a first-class entity named `Tombstone`, not `TombstoneMarker`.

## Rationale

Release, tombstone, redaction, and deletion can apply to any recallable object without mutating the target object's factual identity. Tombstone is a human-centered memorial concept, not a technical marker.

## Consequences

- Release Control overlays targets through `ReleaseTargetRef`.
- Tombstone/quiet/archive are modeled and traceable in 0.9.530.
- Redaction/deletion/safety-sensitive content is protected immediately.
