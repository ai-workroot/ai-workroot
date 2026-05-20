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
