# Architecture Map

AI Workroot separates user work, kernel law, extensions, runtime state, indexes, and handoff so that AI work can continue across agents, models, tools, operating systems, and time.

The public architecture is:

```text
space/       user-visible workspace
.workroot/   kernel, extensions, and rebuildable runtime state
```

## Core Product Flow

```mermaid
flowchart LR
  User[human, team, role, or project] --> Agent[AI agent]
  Agent --> Profile[space/profile<br/>subject identity]
  Agent --> Work[space/work<br/>visible results]
  Agent --> RuntimeWork[.workroot/runtime/work<br/>internal task state]
  Agent --> Mind[space/mind<br/>memory, knowledge, principles, decisions]
  RuntimeWork --> Index[.workroot/runtime/index<br/>registries and links]
  Mind --> Index
  Work --> Index
  Index --> Context[.workroot/runtime/context<br/>current state and handoff]
  Context --> Agent
```

## Operating Layers

```mermaid
flowchart TB
  Human[subject<br/>person, team, role, project, or organization] --> Space[space/<br/>owned user space]
  Space --> Profile[profile<br/>identity and boundaries]
  Space --> VisibleWork[work<br/>outputs, summaries, reports]
  Space --> Mind[mind<br/>long-term externalized mind]
  Space --> Files[files and inbox<br/>source material and capture]

  Agent[AI agent<br/>product interface] --> Kernel[.workroot/kernel<br/>stable law]
  Agent --> Ops[Agent Operation Layer<br/>fast-start, CLI, batch, continuation]
  Kernel --> Boot[boot<br/>small startup context]
  Kernel --> Product[product<br/>ordinary user behavior]
  Kernel --> Protocol[protocol<br/>work, memory, release, handoff]
  Kernel --> Contracts[contracts and schemas<br/>machine-readable policy]
  Kernel --> Interfaces[interfaces<br/>extension boundaries]

  Ops --> Boot
  Ops --> Registries
  Ops --> Runtime
  Interfaces --> Extensions[.workroot/extensions<br/>replaceable capabilities]
  Extensions --> Runtime[.workroot/runtime<br/>generated state]
  Runtime --> Context[context<br/>current and handoff]
  Runtime --> Registries[index<br/>registries and relationships]
  Runtime --> Stores[data, cache, logs<br/>rebuildable accelerators]
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

## Context Loading

```mermaid
flowchart LR
  L0[L0 boot<br/>AGENTS, START_HERE, boot] --> L1[L1 active<br/>profile, current, handoff]
  L1 --> L2[L2 indexes<br/>registries and links]
  L2 --> L3[L3 focused docs<br/>protocol, product, contracts]
  L3 --> L4[L4 extensions<br/>only when relevant]
  L4 --> L5[L5 deep history<br/>explicit reason only]
```

## Storage Principle

```mermaid
flowchart LR
  Source[files<br/>source of truth] --> Registries[CSV registries<br/>portable indexes]
  Source --> Contracts[JSON contracts<br/>validated policy]
  Registries --> SQLite[SQLite<br/>lookup accelerator]
  Registries --> DuckDB[DuckDB<br/>analytical accelerator]
  Registries --> Vector[vector index<br/>semantic accelerator]
  Registries --> Graph[graph index<br/>relationship accelerator]
  SQLite --> Rebuild[rebuildable]
  DuckDB --> Rebuild
  Vector --> Rebuild
  Graph --> Rebuild
```

## Rule

Ordinary users should not need this map before they get value.

Agents and contributors use the map to keep the product simple, the kernel strict, context small, generated stores rebuildable, and future continuation reliable.
