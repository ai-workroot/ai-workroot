# Architecture Map

AI Workroot separates user assets, WorkrootEnvironment management, runtime orchestration, storage, indexing, agent entry, and release controls so AI work can continue across agents, models, tools, operating systems, and time.

The active architecture is Clean Workroot:

```text
user-selected directory   user assets, optional authorized Native Agent Entry
AI_WORKROOT_HOME          WorkrootEnvironment and managed state
src/ai_workroot/          CLI / Commands / Capability Modules / Shared / Templates
```

Public Seed is historical and lives under `docs/history/public-seed/` only.

## Core Product Flow

```mermaid
flowchart LR
  User[person] --> Agent[AI agent]
  Agent --> Entry[Native Agent Entry<br/>authorized launcher files]
  Agent --> CLI[workroot CLI]
  CLI --> Commands[Application commands]
  Commands --> Env[WorkrootEnvironment<br/>AI_WORKROOT_HOME]
  Env --> WR[Per-Workroot managed state]
  UserDir[User-selected directory<br/>user assets] --> Commands
  WR --> Context[Context Control<br/>Context Package]
  WR --> Release[Release Control]
  WR --> Rel[Relationship Network]
  WR --> Retrieval[Retrieval & Index Control]
  Retrieval --> Context
  Rel --> Context
  Release --> Context
  Context --> Agent
```

## Engineering Layers

```mermaid
flowchart TB
  CLI[CLI<br/>terminal adapter] --> Commands[Commands<br/>application entrypoints]
  Commands --> State[State<br/>managed state]
  Commands --> Work[Work]
  Commands --> Assets[Assets]
  Commands --> Relationships[Relationships]
  Commands --> Retrieval[Retrieval]
  Commands --> Context[Context]
  Commands --> Release[Release]
  Commands --> Handoff[Handoff]
  Commands --> AgentEntry[Agent Entry]
  Commands --> Diagnostics[Diagnostics]
  State --> Shared[Shared<br/>small primitives and contracts]
  Retrieval --> Shared
  Context --> Shared
  Release --> Shared
  Templates[Templates] --> AgentEntry
```

The historical Agent Operation Layer is preserved through explicit capability mapping. Clean Workroot maps it into CLI, Commands, Work, Context Control, Handoff, and Agent Interface capabilities instead of requiring active Public Seed root files.

## Domain Concepts

```mermaid
flowchart LR
  WM[Workroot Management<br/>WorkrootEnvironment] --> Work[Work]
  Work --> Asset[Asset]
  Work --> RN[Relationship Network]
  Asset --> RC[Release Control]
  RN --> RIC[Retrieval & Index Control]
  Asset --> RIC
  Work --> RIC
  RC --> CC[Context Control]
  RIC --> CC
  RN --> CC
  CC --> Handoff[Handoff<br/>derived transfer packages]
  Handoff --> AI[Agent Interface]
  WM --> Health[System Health]
  Extensions[Extensions] --> RIC
```

Domain arrows describe product flow and references between capabilities, not source import dependencies.

## Managed State Layout

```mermaid
flowchart TB
  Home[AI_WORKROOT_HOME] --> Registry[registry]
  Home --> GlobalIndex[global-index<br/>management read models]
  Home --> GlobalCache[global-cache<br/>derived cache]
  Home --> Workroots[workroots]
  Workroots --> One[wr_xxx]
  One --> Charter[charter]
  One --> Tasks[tasks]
  One --> Assets[assets]
  One --> Release[release]
  One --> Relationships[relationships]
  One --> Indexes[indexes]
  One --> Context[context]
  One --> Handoff[handoff]
  One --> Diagnostics[diagnostics]
  One --> Cache[cache]
```

## Context Loading

```mermaid
flowchart LR
  Req[ContextRequest] --> Rules[Required rules<br/>agent, mode, budget]
  Req --> Candidates[Materialized Context Candidates]
  Req --> FTS[SQLite FTS]
  Req --> Rel[Relationship one-hop signals]
  Req --> Recent[recent and high-importance items]
  Rules --> Select[merge, score, filter, trim]
  Candidates --> Select
  FTS --> Select
  Rel --> Select
  Recent --> Select
  Select --> Package[ContextPackage]
  Select --> Trace[ContextTrace]
```

## Daily Loop

```mermaid
flowchart LR
  Orient[orient] --> Choose[choose]
  Choose --> Work[work]
  Work --> Preserve[preserve]
  Preserve --> Promote[promote]
  Promote --> Release[release when needed]
  Release --> Handoff[handoff]
  Handoff --> Orient
```

## Rule

Ordinary users should not need this map before they get value.

Agents and contributors use the map to keep user directories clean, managed state explicit, context explainable, release controls enforceable, and legacy Public Seed material safely historical.
