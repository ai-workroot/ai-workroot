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

DDD was used only to understand the domain. The final implementation does not use a heavyweight DDD directory layout. The eleven core concepts are:

1. Workroot Management
2. Work
3. Asset
4. Release Control
5. Relationship Network
6. Retrieval & Index Control
7. Context Control
8. Handoff
9. Agent Interface
10. System Health
11. Extensions

These concepts are implemented through a command-first, capability-owned module structure:

```text
cli/
commands/
protocol/
state/
work/
assets/
relationships/
retrieval/
context/
release/
handoff/
agent_entry/
diagnostics/
shared/
templates/
```

## Engineering principles

- Docs are domain-language-first.
- Code is command-first, capability-owned, and shared-minimal.
- Keep `cli` as a thin terminal adapter.
- Put application entrypoints in `commands`.
- Let each capability own its local models, operations, and helpers.
- Keep `shared` small and stable.
- Preserve old capabilities through explicit mapping.
- Do not create one class/file/table for every domain term.
- Do not use technical names for core domain concepts.
- Do not restore old layer-first source packages.

## 0.9.530 release goal

0.9.530 is an architecture reset release:

- Retire active Public Seed layout.
- Establish Clean Workroot as default.
- Establish bootstrap-dev dogfood flow.
- Introduce the lightweight engineering structure.
- Preserve old Work, Asset, Index, Release, Tombstone, Relationship, Context, Handoff, Agent, and Extension capabilities.
- Rewrite docs/specs/roadmap/release validation around the new model.

## 0.9.531 release line

0.9.531 extends the Clean Workroot architecture with the Agent Protocol and Task Continuity foundation:

- `protocol/` is the Agent-facing application control layer for sync and commit.
- `commands/` adapts CLI and future transport inputs into protocol or capability calls.
- Capability modules keep owning their own facts and operations.
- `state/` remains managed state infrastructure.
- `shared/` remains a tiny shared kernel, not a new core.

For the current runtime layering, see [Runtime Layering](010-runtime-layering.md).
