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
- WorkEvent
- OperationTransaction
- WorkflowRecipe

Boundaries:

- Task is retained. WorkItem is not a formal product term.
- Task can be decomposed through Relationship Network edges.
- Task/Action/Run are factual process records. They are not mutated into tombstone states.

## 3. Handoff

Owns derived transfer packages.

Entities and concepts:

- HandoffPackage
- HandoffTarget
- HandoffBody

Boundaries:

- May reference Work facts, context packages, assets, relationships, and release filters.
- Does not own durable Work truth.
- Does not own final Context Package selection.

## 4. Asset

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

## 5. Release Control

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
- Release Control owns target resolution and release filtering for recallable outputs.
- Tombstone/quiet/archive are modeled, visible, traceable, but not strongly excluded by default in 0.9.530.
- Redaction/deletion/safety-sensitive content must be protected immediately.

## 6. Relationship Network

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

## 7. Retrieval & Index Control

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
- Does not own release filtering or release target resolution.

## 8. Context Control

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
- Consumes Work, Asset, Release Control, Relationship Network, Retrieval & Index Control, and Handoff.

## 9. Agent Interface

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

## 10. System Health

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

## 11. Extensions

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
