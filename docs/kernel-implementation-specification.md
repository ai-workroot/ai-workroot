# Clean Workroot Implementation Specification

This is the implementation-grade companion to `docs/workroot-system-design.md` for the Clean Workroot architecture through the 0.9.531 Agent Protocol and Task Continuity line.

The retired Public Seed kernel specification is preserved under `docs/history/public-seed/` and 0.9.529 history docs. It is not the current active implementation specification.

## Active Scope

The active implementation establishes:

- Clean Workroot user-directory behavior.
- `AI_WORKROOT_HOME` managed state through WorkrootEnvironment.
- Command-first, capability-owned source boundaries.
- Workroot Agent Protocol sync/commit runtime boundaries.
- bootstrap-dev dogfood support for this source repository.
- SQLite schema and migrations for per-Workroot state.
- Context Control with explainable local retrieval.
- Release Control protections for tombstone, redaction, and deletion.
- Relationship Network as the business relationship model.
- System Health and release validation.

## Source Layout

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

Key source paths are `entrypoints/`, `commands/`, `protocol/`, `capabilities/`, `state/`, `shared/`,
`capabilities/work/`, `capabilities/assets/`, `capabilities/relationships/`, `capabilities/retrieval/`,
`capabilities/context/`, `capabilities/release/`, `capabilities/handoff/`, `capabilities/system_health/`, and
`entrypoints/native_agent/`.

Required import rules:

- `entrypoints/cli` calls `commands`; it does not call state, retrieval, storage, indexing, or runtime internals directly.
- `commands` coordinates protocol runtime and capability modules.
- `protocol` implements Agent-facing sync/commit control and calls capability modules; capability modules must not import `protocol`.
- capability modules own local models and operations.
- `shared/contracts` uses only the Python standard library.
- old layer-first package directories must not exist in active source.

## User Directory Rules

Given a user-selected directory:

- Do not create managed folders there by default.
- Do not create indexes, context packages, handoffs, logs, cache, runtime files, kernel files, or control files there by default.
- Allow existing user folders named `state`, `logs`, `cache`, `context`, or similar without treating them as managed AI Workroot state.
- Write Native Agent Entry files only after explicit authorization.
- Published Assets may be written to the user directory only through explicit Asset Publication behavior.

## WorkrootEnvironment Layout

Managed state lives under `AI_WORKROOT_HOME` by default:

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
  global-index/
  global-cache/
  migrations/
  concurrency/
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

Rules:

- Registry writes require a registry-level lock.
- Duplicate Workroot IDs are rejected.
- Duplicate user-directory bindings are rejected under the lock.
- `global-index` is a management read model, not a global knowledge body store.
- Knowledge belongs to individual Workroots as Assets.

## SQLite Schema

Per-Workroot SQLite lives under the Workroot managed state cache, normally:

```text
$AI_WORKROOT_HOME/workroots/<workroot-id>/cache/workroot.sqlite
```

Required schema areas:

- `schema_migrations`
- Workroot management tables
- Work tables
- Asset tables
- Release Control tables
- Relationship Network tables
- Retrieval/index tables
- Context candidate and FTS tables
- Health/diagnostic tables where applicable

Schema changes must use `schema_migrations` or `PRAGMA user_version` based migration. Migration tests must cover old database fixtures or old-schema initialization.

## Work

Work keeps factual process continuity. Required concepts include:

- Task
- L0 / L1 / L2 / L3 process levels
- TaskRun
- TaskItem
- protocol commit batches and protocol events
- AgentRun for lower-level direct work-operation records where needed
- WorkAction
- WorkCheckpoint
- Retrieval Card
- InvalidationRecord
- Handoff
- OperationTransaction

Clean Workroot user flows center on `init`, `list`, `status`, `context`, `doctor`, and `bootstrap-dev`. Runnable legacy Public Seed commands are not part of the active implementation path.

## Asset

Assets represent user value objects and internal managed value records.

Required concepts:

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

Knowledge, decisions, results, references, patterns, principles, and handoff documents are Asset subtypes.

## Release Control

Required concepts:

- ReleaseRecord
- ReleaseTargetRef
- ReleaseLevel
- Tombstone
- Redaction
- DeletionRecord
- RecallRule
- ReleasePolicy
- ReleasePropagationEvent

Rules:

- Tombstone is the entity name. Do not use `TombstoneMarker`.
- Release Control overlays recallable targets without mutating target identity.
- Tombstone, quiet, and archive are modeled and traceable.
- Redacted, deleted, and safety-sensitive content must not enter ordinary context, FTS, candidates, or global indexes.
- DeletionRecord keeps only minimal audit information.

## Relationship Network

Relationship Network owns canonical relationships. Required concepts:

- RelationshipNode
- RelationshipEdge
- RelationshipType
- RelationshipEvidence
- RelationshipPolicy

Graph is not the business domain name. Graph may appear only as technical implementation wording.

Context graph signals must be relation-backed and related to selected candidates, active task, query, or domains. Do not insert unrelated high-importance global nodes as context signals.

## Retrieval & Index Control

P0 retrieval is local-first and explainable:

- SQLite FTS
- file metadata
- materialized context candidates
- recent activity
- explicit project files
- Relationship Network one-hop signals
- git state when available

No vector database, remote embedding provider, or remote LLM dependency is required in the current local-first implementation line.

FTS failures should degrade gracefully and record trace errors/fallbacks.

## Context Control

Context Control accepts a ContextRequest and returns a ContextPackage plus optional ContextTrace.

Required output metadata:

- mode
- confidence
- latency
- target token budget
- hard token limit
- token usage
- selected candidates
- FTS matches
- Relationship Network signals
- filtered candidates and reasons in debug mode
- timing and budget trim steps in debug mode

Token estimation must be conservative enough for English, CJK/no-whitespace text, and code. Hard token limits require final fallback trimming if normal trimming is insufficient.

## Agent Interface

Native Agent Entry files are generated from templates under package resources.

Rules:

- Write only with explicit authorization or bootstrap-dev dogfood behavior.
- Keep files short.
- Do not include absolute local managed-state paths.
- Do not embed large Context Packages.
- Root repo `AGENTS.md` and `CLAUDE.md` are generated local files and Git ignored.

## bootstrap-dev

bootstrap-dev must:

- identify the repo through `workroot.project.json`.
- not require root tracked `AGENTS.md`, `CLAUDE.md`, `space/`, or `.workroot/`.
- initialize Workroot managed state and SQLite.
- create ignored `.ai-workroot-local/` staging.
- be idempotent for the same repo.
- reject the same Workroot ID for a different repo.
- not commit, tag, push, or release.

## System Health And Release Validation

Required gates:

```bash
python3 -m py_compile $(find src scripts -name "*.py")
python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m ai_workroot doctor --release
scripts/dev/validate-release.sh
git diff --check
```

Install script syntax checks:

```bash
bash -n install/unix/install.sh
bash -n scripts/dev/bootstrap-dev.sh
```

PowerShell parse validation should run when `pwsh` is available. If unavailable, document the gap.

## Public Seed Quarantine

Active root must not track:

```text
AGENTS.md
CLAUDE.md
space/
.workroot/
.idea/
```

Historical Public Seed material may remain under:

```text
docs/history/public-seed/
```

Legacy tests may copy that historical fixture into temporary directories. They must not require active root Public Seed files.

## Release Definition Of Done

The current implementation line is release-ready when:

- Clean Workroot docs/specs are current.
- Agent Protocol sync/commit docs and tests are current.
- Public Seed is historical only.
- Package import boundaries pass.
- Clean Mode smoke tests pass.
- bootstrap-dev smoke tests pass.
- Native Agent Entry smoke tests pass.
- SQLite schema/migration tests pass.
- Context Control tests pass.
- Release Control negative tests pass.
- Public Seed active-root negative tests pass.
- No vector database, remote embedding, or remote LLM dependency is introduced.
- Known limitations are documented in release notes.
