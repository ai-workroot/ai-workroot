# Workroot System Design

AI Workroot is a personal, local-first Workroot for individuals.

This document defines the active 0.9.530 Clean Workroot system shape. The retired Public Seed design is preserved under `docs/history/public-seed/` and should not be treated as the current architecture.

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
- Workroot Management registry and directory bindings.
- Work, Asset, Release Control, Relationship Network, Retrieval & Index Control, Context Control, Agent Interface, System Health, and Extensions concepts.
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

The user-selected directory is user asset space. AI Workroot must not create default generated folders, indexes, runtime state, logs, context files, or control files there.

Native Agent Entry files are the only normal exception, and only after explicit authorization.

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
  core/
  contracts/
  runtime/
  storage/
  indexing/
  agent/
  cli/
  resources/
```

Responsibilities:

- `core`: domain models, value objects, policies, and invariants.
- `contracts`: standard-library-only protocols and DTOs.
- `runtime`: orchestration, command flows, migrations, doctor, and context assembly.
- `storage`: filesystem, JSONL, SQLite, locks, and schema helpers.
- `indexing`: FTS, candidate pools, Relationship Network projections, and retrieval providers.
- `agent`: Native Agent Entry templates and managed block handling.
- `cli`: thin command entry points.
- `resources`: packaged templates.

Dependency rules:

```text
cli -> runtime
runtime -> core
runtime -> contracts
storage -> contracts
indexing -> contracts
agent -> contracts
agent -> runtime where needed
contracts -> standard library only
```

CLI must not import storage or indexing directly. Core must not import storage, indexing, agent, or CLI.

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

Owns factual process records: Task, AgentRun, WorkAction, WorkCheckpoint, RetrievalCard, InvalidationRecord, Handoff, WorkEvent, and OperationTransaction.

### Asset

Owns user value objects and their metadata. Knowledge, decisions, references, results, patterns, principles, and handoff documents are Asset subtypes, not separate top-level domains.

### Release Control

Owns release, quiet, archive, tombstone, redaction, and deletion overlays. Redacted, deleted, and safety-sensitive content must not leak into ordinary context.

### Relationship Network

Owns canonical relationships through relationship nodes, edges, evidence, and policies. Graph is an implementation word only.

### Retrieval & Index Control

Owns local index manifests, FTS, context candidates, retrieval providers, index health, invalidation, and derived projections.

### Context Control

Owns final context selection, mode, confidence, budget trimming, package rendering, and debug traces.

### Agent Interface

Owns Native Agent Entry templates, managed blocks, authorization, startup contract, adapters, permission hints, output style, and routing.

### System Health

Owns doctor checks, diagnostics, migration status, schema checks, index health checks, and release validation.

### Extensions

Reserves future boundaries for capabilities, skills, agent adapters, MCP bridges, storage drivers, retrieval drivers, and export/import drivers.

## Context Control

Context Control builds an explainable Context Package from:

- required rules
- active task state
- materialized context candidates
- SQLite FTS matches
- indexed file chunks
- Relationship Network one-hop signals
- recent and high-importance items
- release/safety filters

Output includes mode, confidence, latency, token usage, selected candidates, dropped candidates, scoring, timing, and debug details when requested.

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

Native Agent Entry files are short launcher files. They should tell Codex or Claude how to ask `workroot context` for the current package. They must not embed absolute local managed-state paths or large context bodies.

## Historical Public Seed

Public Seed is retired as active architecture. It is preserved in:

```text
docs/history/public-seed/
```

Legacy scripts and tests may use this material as explicit compatibility fixtures. Current architecture tests must not require tracked root `space/`, `.workroot/`, `AGENTS.md`, or `CLAUDE.md`.

## References

- `docs/architecture/000-overview.md`
- `docs/architecture/001-core-concepts.md`
- `docs/architecture/002-engineering-structure.md`
- `docs/architecture/003-runtime-layout.md`
- `docs/architecture/004-legacy-capability-preservation.md`
- `docs/specs/README.md`
- `docs/releases/0.9.530.md`
