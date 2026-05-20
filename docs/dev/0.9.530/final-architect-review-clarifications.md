# Final Architect Review of Codex Implementation Readiness Report

**Project:** AI Workroot 0.9.530 Clean Workroot Domain Reset  
**Target branch:** `feat/0.9.530-clean-workroot-domain-reset`  
**Purpose:** Final clarification before implementation begins  
**Instruction:** Codex may begin implementation only after applying the clarifications in this document.

---

## 1. Final Verdict

Codex's readiness report is broadly correct. It understands the major architectural direction:

- 0.9.530 is a **Clean Workroot architecture reset**, not a bugfix.
- Public Seed active layout must retire.
- Old capabilities must not be lost.
- Engineering implementation should use **Core / Contracts / Runtime / Storage / Indexing / Agent / CLI**.
- DDD is used for strategic modeling, not for heavyweight code structure.
- Clean Workroot and bootstrap-dev dogfood are the only active scenarios.

There is no blocking misunderstanding in Codex's report. Implementation may proceed after the clarifications below are applied.

The most important clarification is:

> Build the replacement architecture first, then quarantine the old Public Seed active root.

This means Codex must not start by deleting or moving `space/`, `.workroot/`, root `AGENTS.md`, or root `CLAUDE.md` before replacement templates, wrappers, docs, tests, and runtime entry points exist.

---

## 2. Required Correction: Execution Order

Codex correctly noticed a possible ordering tension and recommended:

> First build replacement architecture, then quarantine Public Seed active root.

This is the correct order and should be treated as final.

The implementation order must be:

1. Baseline validation and inventory.
2. Source-of-truth docs/specs/ADR import or rewrite.
3. New `src/ai_workroot/` package skeleton.
4. Contracts and core model.
5. Runtime/storage/environment basics.
6. Agent templates and bootstrap-dev replacement path.
7. Asset / Release Control / Relationship Network / Retrieval & Index Control / Context Control migration.
8. CLI/install wrapper migration.
9. Public Seed quarantine.
10. Test migration and negative tests.
11. Final docs sweep and validation.

Do **not** quarantine old root structures until replacement flows are working.

---

## 3. Clarification: Engineering Structure

The final engineering structure is:

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

This is not a heavy DDD directory structure.

### Meaning of each module

| Module | Meaning |
|---|---|
| `core/` | Core concepts, rules, value objects, policies, lightweight domain behavior. |
| `contracts/` | Protocols and DTOs. This is the ports layer. |
| `runtime/` | Orchestration, dependency assembly, transaction boundaries, application flows. |
| `storage/` | SQLite, JSONL, filesystem state, migrations, backup/restore, locks. |
| `indexing/` | Index pipeline, projections, FTS, candidates, global indexes, provider orchestration. |
| `agent/` | Agent Interface, native entry templates, startup protocol, Codex/Claude/generic adapters. |
| `cli/` | Thin CLI command parsing and output formatting. |
| `resources/` | Packaged templates and static resources. |

### Important rule

Do not explode `core/` into one file per entity. For 0.9.530, `core/` should remain compact:

```text
core/
  common.py
  environment.py
  work.py
  assets.py
  release.py
  relationships.py
  retrieval.py
  context.py
  agent.py
  health.py
  extensions.py
```

If a file becomes too large later, split it in a future iteration. Do not over-DDD this release.

---

## 4. Clarification: Contracts Layer

Codex correctly stated that contracts should depend only on the standard library. This is final.

### Required dependency rules

```text
contracts -> standard library only
core -> contracts only when necessary
runtime -> core + contracts
storage -> contracts
indexing -> contracts, and core only when policy interpretation is required
agent -> contracts + resources, runtime only where appropriate
cli -> runtime
```

### Contracts must not import

```text
ai_workroot.core
ai_workroot.runtime
ai_workroot.storage
ai_workroot.indexing
ai_workroot.agent
ai_workroot.cli
```

If a contract needs data, define a small DTO inside `contracts/`. Runtime maps between contract DTOs and core objects.

### Add import-boundary tests

Codex must add tests or validation scripts to ensure:

- `contracts/` does not import project-local modules.
- `core/` does not import `storage/`, `indexing/`, `agent/`, or `cli/`.
- `cli/` does not directly call `storage/` or `indexing/`; it calls `runtime/`.

---

## 5. Clarification: Core Is Not a Passive Model

Core must not become an anemic model.

Core objects should include local behavior, rules, and invariants. Examples:

```text
Task.close()
Task.can_transition_to()
Task.should_request_decomposition()
Asset.publish()
Asset.mark_missing()
Asset.update_fingerprint()
Tombstone.allows_explicit_review()
RelationshipEdge.attach_evidence()
IndexManifest.is_stale()
ContextBudget.requires_trim()
```

However, core objects must not depend on infrastructure implementation details.

External capabilities should be accessed through contracts and usually coordinated by runtime services or core services, not by long-lived entity-held adapters.

Allowed:

```text
Entity uses a pure policy or receives a contract collaborator as a method parameter when appropriate.
```

Not allowed:

```text
Entity stores SQLite adapter, filesystem gateway, vector adapter, or repository implementation.
```

---

## 6. Clarification: Relationship Network vs Graph

Codex understood this correctly, but it must be enforced in implementation.

### Domain name

Use:

```text
Relationship Network
RelationshipNode
RelationshipEdge
RelationshipType
RelationshipEvidence
RelationshipPolicy
```

Do not use `Graph` as the business/domain name.

### Technical name

The word `graph` may appear only as a technical implementation term, such as:

```text
graph traversal
graph projection
future graph database adapter
```

### Schema preference

For the 0.9.530 reset, prefer new canonical table names:

```text
relationship_nodes
relationship_edges
relationship_evidence
```

If migration risk is too high, Codex may keep compatibility views or temporary legacy mapping, but the active domain/API/docs must use Relationship Network terminology.

Codex must not keep `graph_*` as active architecture language.

---

## 7. Clarification: Release Control

Codex correctly understood most of Release Control. The final rules are:

### Entity names

Use:

```text
ReleaseRecord
ReleaseTargetRef
ReleaseLevel
Tombstone
Redaction
DeletionRecord
RecallRule
ReleasePolicy
ReleasePropagationEvent
```

Do not use:

```text
TombstoneMarker
ReleaseMarker
RedactionMarker
DeletionMarker
```

`Tombstone` is a first-class domain entity and should be named exactly that.

### Release Control target model

Release Control can cover any recallable object, including:

```text
Asset
Task
WorkAction
AgentRun
Checkpoint
Handoff
ContextPackage
ContextTrace
RetrievalCard
RelationshipEdge
```

Release Control must not mutate the target object's own status field. It is an independent overlay/control layer.

Example:

```text
Task.status = closed
Tombstone(target_ref=task:task_123)
```

Both may coexist.

### Default behavior in 0.9.530

```text
Tombstone / quiet / archive:
  model, annotate, make visible, trace;
  do not hard-exclude by default in 0.9.530.

Redaction / deletion / safety-sensitive:
  strictly protect immediately;
  ordinary context, FTS, candidates, and global indexes must not leak protected content.
```

Codex must implement negative tests for redaction/deletion leakage.

---

## 8. Clarification: Retrieval & Index Control

Codex correctly identified this as a core area. It must remain visible in implementation.

### It is not just RAG

Retrieval & Index Control serves two purposes:

1. Context recall for Context Control.
2. Local management queries for CLI, future UI, doctor, and Workroot management.

Examples of local management queries:

```text
What Workroots exist?
What tasks exist?
What assets exist?
What decisions exist?
Which indexes are stale?
Which objects are tombstoned or redacted?
```

These do not go through Context Control.

### Provider / Adapter design

Contracts should define retrieval protocols. Infrastructure and indexing modules implement them.

Suggested structure:

```text
contracts/retrieval.py
indexing/providers/sqlite_fts.py
indexing/providers/candidate_provider.py
indexing/providers/relationship_provider.py
indexing/providers/metadata_provider.py
indexing/providers/vector_provider.py   # reserved only
indexing/providers/search_provider.py   # reserved only
```

No actual vector DB, remote embedding, remote LLM, or external search dependency may be introduced in 0.9.530.

Reserved provider files are allowed only as protocol placeholders.

---

## 9. Clarification: Workroot Management and Global Environment

Codex understood WorkrootEnvironment, but the preservation matrix should explicitly include global control-plane pieces.

Add or explicitly map these items:

```text
AI_WORKROOT_HOME/config.json
registry/workroots.jsonl
registry/directory-bindings.jsonl
registry/aliases.jsonl
registry/relationships.jsonl
registry lock
preferences / policy defaults
global-index/*
global-cache/global.sqlite
migrations/global state
concurrency locks
workroots/<id>/workroot.json
```

New concept mapping:

```text
WorkrootEnvironment
EnvironmentConfig
EnvironmentHome
WorkrootRegistry
WorkrootRegistration
WorkrootDirectoryBinding
WorkrootAlias
WorkrootRelationship
GlobalPreferences
GlobalPolicyDefaults
GlobalIndexCatalog
GlobalCacheState
EnvironmentMigrationState
```

Important rule:

```text
Global index is for navigation and management, not automatic cross-Workroot knowledge recall.
```

---

## 10. Clarification: Legacy Capability Matrix Needs a Few Additions

Codex's matrix is strong, but it should add the following explicit rows before implementation:

### Work process additions

```text
TaskKind
TaskProcessLevel
TaskDecompositionPolicy
OwnerScope
Visibility
WorkAction
WorkCheckpoint
RetrievalCard
InvalidationRecord
OperationTransaction
WorkflowRecipe
RunValidity
ActionType
RiskLevel
```

### Common model additions

```text
ActorRef
DomainEvent
SourceRef
EvidenceRef
PolicyRef
PolicyVersion
TimeEvent
LocalizationPolicy
StoragePolicy
PrivacyLevel
PermissionHint
```

### Global environment additions

```text
WorkrootEnvironment
EnvironmentConfig
WorkrootRegistration
WorkrootAlias
WorkrootRelationship
GlobalPreferences
GlobalPolicyDefaults
GlobalIndexCatalog
GlobalCacheState
```

### Extensions additions

```text
Capability
Skill
AgentAdapter
McpBridge
StorageDriver
RetrievalDriver
ExportImportDriver
```

These do not all need heavy implementation in 0.9.530, but they must be preserved, renamed, merged, retired, or deferred explicitly. They must not silently disappear.

---

## 11. Clarification: Templates Source of Truth

Avoid duplicated template content.

For 0.9.530, Codex should use this as the runtime source of truth:

```text
src/ai_workroot/resources/templates/native-agent-entry/
  AGENTS.md.template
  CLAUDE.md.template
```

A top-level `templates/native-agent-entry/` directory is optional. If Codex creates it, it must either:

1. Be documented as a human-readable mirror, or
2. Be kept synchronized by a validation test.

Simplest option: use only the packaged resources path and reference it in docs.

Root `AGENTS.md` and `CLAUDE.md` must not be tracked.

`.gitignore` must include:

```text
/AGENTS.md
/CLAUDE.md
/.ai-workroot-local/
```

---

## 12. Clarification: `validate_kernel.py --release`

Codex listed:

```text
python3 scripts/validate_kernel.py --release until replaced
```

This is acceptable for Phase 0 baseline only.

However, `validate_kernel.py` is tied to old Public Seed/kernel assumptions. It cannot remain the final release validator unless it is rewritten to validate the new Clean Workroot architecture.

Final validation must either:

1. Rewrite `validate_kernel.py` to the new architecture, or
2. Replace it with a new validation entry point, for example:

```text
python3 -m ai_workroot.cli.main doctor --release
python3 -m ai_workroot.runtime.doctor --release
python3 scripts/dev/validate-release.sh
```

Codex must not report final release readiness using old Public Seed validation alone.

---

## 13. Clarification: Public Seed Quarantine

Do not delete old content outright.

Quarantine strategy:

```text
space/      -> docs/history/public-seed/ and/or tests/fixtures/legacy-public-seed-history/
.workroot/  -> docs/history/public-seed/ and/or tests/fixtures/legacy-public-seed-history/
AGENTS.md   -> remove from tracked active root after templates and bootstrap generation are ready
CLAUDE.md   -> remove from tracked active root after templates and bootstrap generation are ready
.idea/      -> remove from git tracking if tracked; keep ignored
```

Use `git mv` where appropriate so history remains traceable.

Before quarantine, Codex must finish the preservation matrix for the old content.

---

## 14. Clarification: SQLite / Storage Schema

New schema direction:

```text
workroot_environment / environment metadata where needed
workroot registrations / bindings / aliases / relationships
assets
asset_surfaces
asset_publications
asset_path_history
release_records
tombstones
redactions
deletion_records
relationship_nodes
relationship_edges
relationship_evidence
indexes / index_manifest / index_builds / index_invalidations / index_health
context_candidates
indexed_files
indexed_chunks
context_packages
context_traces
doctor_runs
migration_records
```

Important mapping:

```text
knowledge_items -> assets where asset_type = knowledge
decision_registry / decisions -> assets where asset_type = decision
artifact_registry -> assets
link_registry / graph_edges -> relationship_edges
```

Derived tables/read models:

```text
FTS indexes
Context candidates
Relationship traversal projections
Global navigation indexes
```

Canonical tables:

```text
assets
release_records / tombstones / redactions / deletion_records
relationship_edges
tasks / work records
workroot environment registry
```

Graph/relationship tables are not ordinary rebuildable cache.

---

## 15. Clarification: Context Control Boundaries

Context Control must not become a catch-all.

Context Control is responsible for:

```text
context request
selection
filtering
ranking
budget trim
release annotation
context package rendering
context trace
```

Context Control is not responsible for:

```text
publishing user assets
maintaining indexes
owning relationship truth
running migrations
writing Native Agent Entry
writing user directory files except through explicit Asset publication flows
```

Management queries such as task list, asset list, index status, release list do not go through Context Control.

---

## 16. Additional Required Negative Tests

Add or ensure these tests exist:

### Architecture / import boundary

```text
contracts does not import ai_workroot.core
contracts does not import ai_workroot.runtime
contracts does not import ai_workroot.storage
contracts does not import ai_workroot.indexing
core does not import storage/indexing/agent/cli
cli does not directly import storage adapters
```

### Public Seed retirement

```text
root space/ is not active architecture
root .workroot/ is not active architecture
root AGENTS.md is not tracked
root CLAUDE.md is not tracked
bootstrap-dev does not require root AGENTS.md
bootstrap-dev does not require .workroot/kernel/VERSION
```

### Release Control leakage

```text
redacted content does not appear in ordinary ContextPackage
redacted content does not remain in FTS/candidates/global indexes
DeletionRecord leaves only minimal trace
Tombstone is visible and traceable but not hard-excluded by default
```

### Relationship Network

```text
RelationshipEdge is canonical
Relationship traversal projection is derived
Relationship terminology appears in docs/core API, not Graph as domain name
```

### Retrieval & Index Control

```text
no real vector DB dependency
no remote embedding dependency
no remote LLM dependency
reserved vector/search adapters do not import external packages
```

---

## 17. Codex May Proceed If It Accepts These Corrections

Codex's report is good enough to proceed, but implementation must incorporate this document.

Codex should update its plan with:

1. The execution order correction.
2. The additional preservation matrix rows.
3. The contracts independence rule.
4. The final template source-of-truth rule.
5. The `validate_kernel.py` baseline-only clarification.
6. The Relationship Network naming rule.
7. The Release Control naming and default behavior rule.
8. The Public Seed quarantine-before-delete rule.

After acknowledging these, Codex may begin Phase 0 and Phase 1.

---

## 18. Final Architect Judgment

Codex understood the architecture well enough. There is no need for another broad architecture discussion before implementation.

The remaining issues are implementation guardrails, not architecture blockers.

Final go/no-go:

```text
Status: Ready to implement after applying this clarification document.
Branch: feat/0.9.530-clean-workroot-domain-reset
First action: baseline validation and preservation matrix completion.
Do not tag.
Do not release.
Do not delete old capabilities.
```
