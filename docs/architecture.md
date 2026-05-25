# AI Workroot Architecture

AI Workroot is a personal, local-first Workroot foundation for individuals.

The core architectural claim remains:

> The Workroot is the durable continuity layer.  
> AI agents are replaceable collaborators.

0.9.530 resets the active architecture to **Clean Workroot**. The old Public Seed layout is preserved under `docs/history/public-seed/` for history and legacy capability tests, but it is not the active source or user-directory model.

## Active Architecture

Clean Workroot has two active scenarios:

1. **Clean Workroot user directories**
   - A user selects a directory.
   - That directory is user asset space.
   - AI Workroot does not create managed folders or control files there by default.
   - Managed state lives under `AI_WORKROOT_HOME` through `WorkrootEnvironment`.
   - Native Agent Entry files are written only with explicit authorization.

2. **bootstrap-dev dogfood**
   - The AI Workroot source repository can register itself as a Clean Workroot.
   - `workroot.project.json` identifies the repo.
   - Root `AGENTS.md` and `CLAUDE.md` are generated locally and Git ignored.
   - `.ai-workroot-local/` is local staging, not formal managed state and not source.

## Engineering Structure

The active source layout is lightweight, not heavy DDD:

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

DDD is used only for strategic modeling. Implementation is command-first and capability-owned:

- `cli`: thin terminal adapter.
- `commands`: application command entrypoints.
- `state`: managed state, registry, SQLite, JSONL, locking, and migrations.
- `work`, `assets`, `relationships`, `retrieval`, `context`, `release`, `agent_entry`, and `diagnostics`: capability-owned models and operations.
- `shared`: small cross-capability primitives and standard-library-only contracts.
- `templates`: packaged templates.

Old layer-first packages are not part of the active source tree.

## Core Concepts

The active domain language is:

1. Workroot Management / WorkrootEnvironment
2. Work
3. Asset
4. Release Control
5. Relationship Network
6. Retrieval & Index Control
7. Context Control
8. Agent Interface
9. System Health
10. Extensions

Do not use Public Seed, Mind, Memory, Graph, Context Gate, TombstoneMarker, or ReleaseMarker as active top-level domain names. Public Seed may appear in history; graph may appear only as technical implementation wording.

## Work Model

Work keeps factual process continuity:

- Task
- L0 / L1 / L2 process levels
- AgentRun
- WorkAction
- WorkCheckpoint
- Retrieval Card
- InvalidationRecord
- Handoff
- OperationTransaction

Legacy seed commands are not active compatibility tooling. Clean Workroot users should use the primary commands: `init`, `list`, `status`, `context`, `doctor`, and `bootstrap-dev`.

The old Agent Operation Layer capability has been migrated into active Clean Workroot behavior through Work records, application commands, CLI, Context Control, and Agent Interface rather than through active root Public Seed files.

## Runtime Layout

`AI_WORKROOT_HOME` owns managed state by default:

```text
$AI_WORKROOT_HOME/
  config.json
  registry/
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

The user-selected directory remains clean by default. User-owned files remain there; managed runtime state does not.

## Retrieval And Context

0.9.530 favors explainable local retrieval:

- SQLite FTS
- materialized context candidates
- file metadata
- explicit project files
- recent activity
- relationship-backed signals
- git state when available

Vector databases, remote embeddings, and remote LLM calls are not required for P0 context generation.

Context Control produces bounded, explainable Context Packages with mode, confidence, latency, token usage, selected candidates, filtered candidates, scoring, retrieval channels, and debug traces.

## Release Control

Release Control overlays recallable Workroot objects without mutating their factual identity.

The primary concepts are:

- ReleaseRecord
- ReleaseTargetRef
- ReleaseLevel
- Tombstone
- Redaction
- DeletionRecord
- RecallRule
- ReleasePolicy
- ReleasePropagationEvent

Tombstone is a first-class entity. Redacted, deleted, and safety-sensitive content must not leak into ordinary context. Tombstone, quiet, and archive states remain modeled and traceable.

## Historical Material

The retired Public Seed material is preserved at:

```text
docs/history/public-seed/
```

That history exists for compatibility review, legacy capability preservation, and migration reasoning. It must not be reintroduced as active root architecture.

## Source Of Truth

For the 0.9.530 architecture, read:

- `docs/architecture/000-overview.md`
- `docs/architecture/001-core-concepts.md`
- `docs/architecture/002-engineering-structure.md`
- `docs/architecture/003-runtime-layout.md`
- `docs/architecture/004-legacy-capability-preservation.md`
- `docs/specs/README.md`
- `docs/validation/acceptance-checklist.md`
- `docs/releases/0.9.530.md`
