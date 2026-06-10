# Workroot System Design

AI Workroot is a personal, local-first Workroot for individuals.

This document defines the active Clean Workroot system shape through the 0.9.531 Agent Protocol and Task Continuity line. The retired Public Seed design is preserved under `docs/history/public-seed/` and should not be treated as the current architecture.

## Purpose

AI Workroot exists to give AI-assisted work a durable home without tying continuity to one AI tool, model, provider, or chat session.

The product promise is:

```text
The user owns the Workroot.
AI agents help do the work.
Managed state is local and inspectable.
The next agent can continue.
```

## Scope

AI Workroot defines:

- Clean Workroot directory rules.
- WorkrootEnvironment under `AI_WORKROOT_HOME`.
- Workroot Agent Protocol sync/commit interaction and task continuity.
- Workroot Management registry and directory bindings.
- Work, Asset, Release Control, Relationship Network, Retrieval & Index Control, Context Control, Handoff, Agent Interface, System Health, and Extensions concepts.
- Native Agent Entry behavior for Codex and Claude-compatible local agents.
- Local-first retrieval, SQLite schema, migrations, doctor checks, and release validation.

AI Workroot does not define:

- a hosted service
- a model provider
- team collaboration as the core product
- a mandatory vector database
- mandatory remote embeddings
- mandatory remote LLM calls
- a complete desktop GUI

## Design Principles

### Human First

The person remains the subject. AI agents are replaceable collaborators. The Workroot is the durable continuity layer.

### Clean User Directories

The user-selected directory is user asset space. AI Workroot must not create indexes, runtime state, logs, context files, or control files there.

Allowed user-space writes are explicit user-facing assets:

- Native Agent Entry files, only after explicit authorization or bootstrap-dev dogfood behavior.
- `workroot-output/START_HERE.txt` and the default output directory created by initialization as a user-visible guide and asset destination.

`workroot-output/` is not managed runtime state.

### Managed State Outside User Content

Managed state lives under `AI_WORKROOT_HOME` by default. This includes Workroot metadata, indexes, context packages, debug traces, handoffs, runtime records, SQLite databases, logs, migrations, and internal metadata.

### Local First

AI Workroot is local-first. Retrieval and Context Control prefer explainable local mechanisms: SQLite, FTS, metadata, recent activity, explicit project files, and Relationship Network signals.

### Simple For Users, Strict For Agents

Ordinary users should not need to understand internal architecture before getting value. Agents and runtime flows enforce the rules behind the scenes.

## Active Runtime Scenarios

### Clean Workroot

A user registers a directory with `workroot init`. The directory remains clean by default. Managed state is created under `AI_WORKROOT_HOME/workroots/<workroot-id>/`.

### bootstrap-dev Dogfood

The AI Workroot source repository can register itself through `workroot bootstrap-dev`. It uses `workroot.project.json`, generates local ignored `AGENTS.md` and `CLAUDE.md` when needed, creates `.ai-workroot-local/` as local staging, and stores managed state under `AI_WORKROOT_HOME`.

bootstrap-dev must not commit, tag, push, or release automatically.

## Engineering Structure

The active source structure is:

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

Responsibilities:

- `entrypoints`: thin external adapters such as CLI and Native Agent Entry.
- `commands`: reusable application-level command entrypoints.
- `protocol`: Agent-facing application control for sync, commit, focus resolution, leases, idempotency, and projection routing.
- `state`: managed state layout, environment config, registry, SQLite, JSONL, migrations, and locks.
- `capabilities/work`: durable work facts and time events.
- `capabilities/assets`: asset metadata, lifecycle, and publication operations.
- `capabilities/relationships`: canonical Relationship Network truth and operations.
- `capabilities/retrieval`: indexing, FTS, candidate pools, recall hints, global indexes, and retrieval providers.
- `capabilities/context`: context package building, selection, rendering, tracing, and diagnostic logging.
- `capabilities/release`: Release Control models, operations, target resolution, and release filtering.
- `capabilities/handoff`: derived transfer packages for the next agent, tool, session, human, or future self.
- `capabilities/system_health`: doctor, release surface validation, health models, and reports.
- `entrypoints/native_agent`: Native Agent Entry templates and managed block handling.
- `shared`: small cross-capability primitives and standard-library-only contracts.

Old layer-first source package names are removed from the active source tree and must not be restored.

Migration status:

- `src/ai_workroot/` is the active package direction for Clean Workroot.
- `scripts/dev/` holds developer, release, review, and smoke helpers.
- Runnable legacy Public Seed compatibility has been removed from active paths.
- Historical legacy source is preserved as non-runnable `.txt` snapshots under `docs/history/public-seed/code-archive/`.
- New Clean Workroot behavior should be implemented in the package path first.

Dependency rules:

```text
cli -> commands
commands -> protocol
commands -> capability modules
protocol -> capability modules
protocol -> state
capability modules -> shared
capability modules -> state when persistence is needed
state -> shared
shared/contracts -> standard library only
```

CLI must not bypass `commands`. Capability modules must not import `protocol`. `shared/contracts` must not import project modules.

## AI_WORKROOT_HOME Layout

`AI_WORKROOT_HOME` is represented by WorkrootEnvironment.

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

Global layer rules:

- The global registry owns Workroot registration, directory binding, aliases, and Workroot relationships.
- `global-index` is a derived management read model.
- `global-cache` is derived cache.
- There is no global knowledge body store.
- Knowledge belongs to individual Workroots as Assets.

## Core Concepts

### Workroot Management

Owns `WorkrootEnvironment`, config, registry, directory bindings, aliases, Workroot metadata, and Workroot relationships.

### Work

Owns factual process records: Task, TaskRun, TaskItem, protocol events and protocol commit batches, AgentRun where direct work operations need a lower-level run record, WorkAction, WorkCheckpoint, RetrievalCard, InvalidationRecord, WorkEvent, and OperationTransaction.

### Handoff

Owns derived transfer packages used to pass current Workroot state to another agent, tool, session, human, or future self.

A handoff may reference work facts, context packages, assets, relationships, and release filters, but it must not become the owner of durable work truth.

### Asset

Owns user value objects and their metadata. Knowledge, decisions, references, results, patterns, principles, and handoff documents are Asset subtypes, not separate top-level domains.

### Release Control

Owns release, quiet, archive, tombstone, redaction, and deletion overlays. Redacted, deleted, and safety-sensitive content must not leak into ordinary context.

### Relationship Network

Owns canonical relationships through relationship nodes, edges, evidence, and policies. Graph is an implementation word only.

### Retrieval & Index Control

Owns local index manifests, FTS, context candidates, retrieval providers, index health, invalidation, and derived projections.

### Context Control

Owns internal context strategy, final context selection, mode, confidence, budget trimming, package rendering, and debug traces.

### Agent Interface

Owns Native Agent Entry templates, managed blocks, authorization, startup contract, Agent descriptors, transport metadata, adapters, permission hints, output style, and routing.

### System Health

Owns doctor checks, diagnostics, migration status, schema checks, index health checks, and release validation.

### Extensions

Reserves future boundaries for capabilities, skills, agent adapters, MCP bridges, storage drivers, retrieval drivers, and export/import drivers.

## Context Control

Context Control builds an explainable Context Package from a strategy plan.

Strategy runs before detailed retrieval:

```text
focus boundary
-> context policy
-> safety and budget constraints
-> disclosure plan
-> recall plan
-> plan-constrained retrieval
-> final budget fit
-> rendering
```

The internal disclosure model is layered:

- L1: orientation map, task/run/handoff metadata, and refs.
- L2: summaries, decisions, assets, relationships, and handoff summaries.
- L3: scoped evidence, indexed chunks, source snippets, and raw references.

These layer names are internal implementation language. They should not appear
as ordinary user-facing protocol vocabulary.

Context Control consumes:

- required rules
- active Work records
- protocol focus and WorkSignal
- lease freshness as an internal strategy signal
- materialized context candidates
- SQLite FTS matches
- indexed file chunks
- Relationship Network one-hop signals
- recent and high-importance items
- release/safety filters

Output includes mode, confidence, latency, token usage, selected candidates, dropped candidates, scoring, timing, and debug details when requested.

Context recall is non-blocking. Missing evidence, missing indexes, stale lease
signals, or unclear focus should degrade to safe shallow context rather than
blocking the user's work.

## Release Control

Release Control uses:

- ReleaseRecord
- ReleaseTargetRef
- ReleaseLevel
- Tombstone
- Redaction
- DeletionRecord
- RecallRule
- ReleasePolicy
- ReleasePropagationEvent

Tombstone is not `TombstoneMarker`. Release overlays recallable targets without mutating their factual identity.

## Agent Interface

Native Agent Entry files are short launcher files. They should tell the Agent
how to call `workroot agent sync` for state alignment and compact current
context, passing the current user request as `--query`. `workroot context`
remains a read-only auxiliary command for startup recovery, manual recall, and
debugging.

At the protocol level, `--agent` is an Agent descriptor string, not a fixed
Codex/Claude enum. `--transport` is adapter metadata and defaults to `cli`.
Future MCP or SDK entrypoints should preserve the same protocol semantics.

Native Agent Entry files must not embed absolute local managed-state paths or
large context bodies.

## Historical Public Seed

Public Seed is retired as active architecture. It is preserved in:

```text
docs/history/public-seed/
```

Historical tests may reference this material as non-runnable archive fixtures. Current architecture tests must not require tracked root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.

## References

- `docs/architecture/000-overview.md`
- `docs/architecture/001-core-concepts.md`
- `docs/architecture/002-engineering-structure.md`
- `docs/architecture/003-runtime-layout.md`
- `docs/architecture/004-legacy-capability-preservation.md`
- `docs/architecture/010-runtime-layering.md`
- `docs/specs/README.md`
- `docs/releases/0.9.531.md`
- `docs/releases/0.9.530.md`
