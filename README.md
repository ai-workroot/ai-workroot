# AI Workroot

AI Workroot is a personal, local-first Workroot for individuals.

It gives each person a clean, private, user-owned place where AI agents can understand context, continue progress, and help manage meaningful work over time without tying that continuity to any single AI tool.

AI agents may come and go. Your Workroot stays with you.

If you only want to start using AI Workroot, begin with [Start Here for Humans](START_HERE_FOR_HUMANS.md).

## Why AI Workroot Exists

Most AI work still disappears into sessions.

A model answers.
An agent edits files.
A tool completes a task.
A conversation ends.

Some outputs remain, but the work itself often loses continuity:

- What was the goal?
- What changed?
- Which decision was made, and why?
- What should happen next?
- What should become reusable knowledge?
- What should be remembered, released, or corrected?
- Can another AI agent continue later without reading the whole past?

Current AI systems are increasingly strong at execution. They can write code, browse, operate tools, run workflows, and remember some context.

But execution is not the same as durable continuity.

AI Workroot exists because a person's long-term work with AI needs a stable home that does not belong to any one agent, model, provider, or chat product.

## Core Idea

The person remains the subject.

The Workroot is the durable continuity layer.

AI agents are replaceable collaborators.

In practical terms, AI Workroot gives agents a shared, user-owned foundation for:

- Workroot Management
- Work
- Assets
- Release Control
- Relationship Network
- Retrieval & Index Control
- Context Control
- Handoff
- Agent Interface
- System Health

The folders, registries, schemas, and validation scripts are implementation details. They exist to make continuity reliable, portable, and inspectable.

The deeper principle is simple:

> the user's continuity should remain owned, understandable, portable, and under the user's control.

## AI Workroot And Agents

AI Workroot does not try to become the agent.

It gives agents a stable, user-owned continuity layer to work around.

```text
Agents execute.
Tools operate.
Models reason.
Workflows coordinate.
AI Workroot preserves continuity.
```

Strong agents may have memory, skills, tools, MCP, gateways, automation, and long-running behavior. That is valuable.

AI Workroot is different because its primary object is not the agent. Its primary object is the person's continuity.

An agent may work inside a Workroot.

But the Workroot belongs to the person.

The best relationship is complementary:

- agents do the work
- Workroot preserves the meaning, state, and handoff of the work
- the user owns the foundation

## Personal First

AI Workroot is designed for individuals first.

Its current shape is a private, user-owned foundation for one person's long-term work with AI: Work records, Assets, Release Control, Relationship Network, Retrieval & Index Control, Context Control, Handoff, Agent Interface, and System Health.

The heart of this project is one person with many unfinished things, many tools, changing contexts, and a real need to continue.

That person should be able to work with ChatGPT, Codex, Claude Code, Cursor, Hermes, OpenClaw, local agents, or future AI tools without surrendering long-term continuity to any one of them.

Team collaboration may become a separate direction one day, but it is not the core product now.

## Local First, User Owned

AI Workroot is local-first because ownership matters.

A person's important context should not be trapped entirely inside a remote product.

Their progress should not depend completely on one platform's memory.

Their decisions, knowledge, source files, and handoffs should remain accessible, portable, inspectable, and understandable.

Local-first does not mean isolated.

AI Workroot can still connect with agents, models, clients, services, indexes, and future cloud layers. The point is that the foundation belongs to the user first.

Everything else is a visitor.

## Release Control And Continuity

AI Workroot is not only about remembering more.

Continuity is not only accumulation. People also forget, release, quiet, archive, redact, and move forward.

AI Workroot should help preserve what matters without forcing every old event, obsolete belief, mistake, or painful context back into every future session.

The useful lesson can remain.
The raw context can become quiet.
A tombstone can preserve responsibility without keeping the past alive in active recall.

The goal is not to turn a person into a permanent machine-readable profile.

The goal is to help a person continue without losing the freedom to change.

## Current Architecture

AI Workroot is currently in the 0.9.531 Agent Protocol and Task Continuity line, built on the 0.9.530 Clean Workroot architecture reset.

Clean Workroot means the user-selected directory is treated as user asset space. AI Workroot does not create managed runtime folders, indexes, logs, control files, or context stores inside that directory by default.

Managed state belongs under `AI_WORKROOT_HOME` by default, represented by `WorkrootEnvironment`. Per-Workroot SQLite, context packages, indexes, diagnostics, handoffs, release records, Relationship Network projections, and cache files live there unless the user explicitly chooses another mode.

The active source implementation is organized as:

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

The source rule is: docs are domain-language-first; code is entrypoint-adapted, command-first, capability-owned, and shared-minimal. The old layer-first package names and old top-level capability packages are not part of the active source tree.

Root `AGENTS.md`, root `CLAUDE.md`, `space/`, and `.workroot/` are not active tracked architecture. Native Agent Entry files may be generated locally only with explicit authorization, and bootstrap-dev keeps local staging under ignored `.ai-workroot-local/`.

Public Seed is historical. Its preserved files live under `docs/history/public-seed/` for compatibility review and old capability tests.

`src/ai_workroot/` is the active product implementation path. The `scripts/` tree is support-only: `scripts/dev/` holds developer, release validation, and review export helpers. Runnable legacy Public Seed compatibility has been removed from active paths; historical source snapshots are inspectable under `docs/history/public-seed/code-archive/`. New Clean Workroot behavior belongs in the package, not in `scripts/`.

The core principle should remain stable: the user's continuity should stay inspectable, portable, and owned by the user.

For the full current architecture, see:

- [Workroot System Design](docs/workroot-system-design.md)
- [Architecture Map](docs/architecture-map.md)
- [0.9.531 Workroot Agent Protocol Bridge Design](docs/superpowers/specs/2026-06-01-workroot-agent-protocol-bridge-design.md)
- [0.9.531 Release Notes](docs/releases/0.9.531.md)
- [0.9.530 Release Notes](docs/releases/0.9.530.md)

## Start Here

For direct use:

- [Start Here for Humans](START_HERE_FOR_HUMANS.md)
- [User SOP](docs/user-sop.md)

You can start with one sentence:

```text
Help me start this Workroot.
```

Later, you can say:

```text
Help me continue.
```

A task is just the thing you are working on now. AI Workroot keeps the next step clear so you can return later without reconstructing the whole past.

## Read More

For philosophy and positioning:

- [Project Philosophy](docs/project-philosophy.md)
- [Positioning Q&A](docs/positioning-qna.md)

For architecture and protocol:

- [Project Brief](PROJECT_BRIEF.md)
- [Workroot System Design](docs/workroot-system-design.md)
- [Architecture Map](docs/architecture-map.md)
- [Workroot Operating Protocol](docs/workroot-operating-protocol.md)
- [User Interaction Contract](docs/user-interaction-contract.md)

For contribution:

- [Contributing](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Author](AUTHOR.md)

## Website

https://aiworkroot.com

## License

AI Workroot is licensed under the Apache License, Version 2.0.

You may use, modify, distribute, and build commercial projects from it under the license terms.

The license does not grant trademark rights to the project name, domain, future logos, or brand identity. See [TRADEMARKS.md](TRADEMARKS.md) and [NOTICE](NOTICE).

Contributions follow the lightweight [DCO.md](DCO.md) contribution rule.
