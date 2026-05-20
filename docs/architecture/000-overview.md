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
