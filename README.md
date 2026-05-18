# AI Workroot

AI Workroot is a personal, local-first Workroot for individuals.

It gives each person a clean, private, user-owned place where AI agents can understand context, continue progress, and help manage meaningful work over time without tying that continuity to any single AI tool.

AI agents may come and go. Your Workroot stays with you.

If you only want to start using AI Workroot, begin with [START_HERE_FOR_HUMANS.md](START_HERE_FOR_HUMANS.md). This README is for people evaluating AI Workroot as a product direction, protocol, and foundation for long-term human-AI work.

## Why AI Workroot Exists

Most AI work still disappears into sessions.

A model answers. An agent edits files. A tool completes a task. A conversation ends.

Some outputs remain, but the work itself often loses continuity:

- What was the task?
- What state is it in?
- Where is the result?
- What should happen next?
- Which decision was made, and why?
- Which conclusion has become invalid?
- Which output should become reusable knowledge?
- Which old context should leave active recall?
- Can a different agent continue without reading the whole past?

Current AI systems are increasingly strong at execution. They can write code, browse, operate tools, run workflows, and remember some context.

But execution is not the same as durable continuity.

AI Workroot exists because a person's long-term work with AI needs a stable home that does not belong to any one agent, model, provider, or chat product.

## Core Idea

The Workroot is the durable continuity layer.

AI agents are replaceable collaborators.

The person remains the subject. The Workroot preserves what matters so future work can continue without being trapped inside one model's memory, one agent's runtime, or one conversation's history.

In practical terms, AI Workroot gives agents a shared, user-owned foundation for:

- context
- task state
- decisions
- artifacts
- handoff
- memory
- knowledge
- invalidation
- release and intentional forgetting

The folders, registries, schemas, and validation scripts are implementation details. They exist to make continuity reliable, portable, and inspectable.

## How It Differs From Agents

AI Workroot does not try to become the agent.

It gives agents a stable, user-owned continuity layer to work around.

```text
Agents execute.
Tools operate.
Models reason.
Workflows coordinate.
AI Workroot preserves continuity.
```

Coding agents such as Codex, Claude Code, Cursor, and future tools can edit repositories, run commands, and complete engineering tasks. AI Workroot preserves the larger context around that work: what the person is trying to continue, what has already happened, what decisions were made, what should be remembered, what should be released, and what the next agent needs to know.

Assistant products and long-running agents may have their own memory, tools, and automation. AI Workroot is different because its primary object is not the agent. Its primary object is the person's continuity.

The best relationship is complementary:

- agents do the work
- Workroot preserves the meaning, state, and handoff of the work
- the user owns the foundation

## Personal First

AI Workroot is designed for individuals first.

Its current shape is a private, user-owned foundation for one person's long-term work with AI: personal context, files, tasks, decisions, knowledge, handoff, memory, and intentional forgetting.

The heart of this project is one person with many unfinished things, many tools, many changing contexts, and a real need to continue.

That person should be able to work with ChatGPT, Codex, Claude Code, Cursor, Hermes, OpenClaw, local agents, or future AI tools without surrendering their long-term context to any one of them.

## Local First, User Owned

AI Workroot is local-first because ownership matters.

A person's important context should not be trapped entirely inside a remote product. Their progress should not depend completely on one platform's memory. Their decisions, knowledge, source files, and handoffs should remain accessible, portable, inspectable, and understandable.

Local-first does not mean isolated.

AI Workroot can still connect with agents, models, clients, services, indexes, and future cloud layers. The point is that the foundation belongs to the user first.

Everything else is a visitor.

## What AI Workroot Preserves

AI Workroot is built around four capabilities:

1. Personal context sovereignty
2. Work lifecycle management
3. Cross-agent continuity
4. Layered memory and intentional forgetting

It preserves not only outputs, but the meaning and state around the work:

- current tasks and next actions
- visible outputs and artifacts
- important decisions and why they were made
- reusable knowledge
- invalidated conclusions
- handoff context for the next agent or future session
- memory that should remain useful
- old context that should become quiet, released, or tombstoned

This matters because human life is not only memory accumulation. People also forget, release, quiet, archive, redact, and move forward. AI Workroot should not force every old event, mistake, obsolete belief, or painful context back into every future session.

The useful lesson can remain. The raw context can become quiet. A tombstone can preserve responsibility without keeping the past alive in active recall.

## Current Public Seed

AI Workroot is currently an early public seed for a personal, local-first Workroot.

The current seed is file-first. Markdown, JSON, CSV, and user-owned source files remain the durable substrate. Databases, vector indexes, graph stores, and local caches can be useful accelerators, but they should not become the canonical truth by default.

The current public seed uses this implementation shape:

```text
space/       user-owned space
.workroot/   kernel, runtime, indexes, and protocol state
```

This layout is the current seed architecture, not a promise that every future Workroot implementation will look exactly the same. The project may evolve toward cleaner user-facing clients, managed storage modes, richer local services, or larger architectural changes while preserving the core principle: the user's continuity should remain inspectable, portable, and owned by the user.

For the full current architecture, see [docs/workroot-system-design.md](docs/workroot-system-design.md) and [docs/architecture-map.md](docs/architecture-map.md).

## Start Here

For direct use:

- [START_HERE_FOR_HUMANS.md](START_HERE_FOR_HUMANS.md)
- [docs/user-sop.md](docs/user-sop.md)

A task is just the thing you are working on now.

AI Workroot keeps the next step clear so you can return later and say:

```text
Help me continue.
```

When a task is finished, you can say:

```text
This task is finished. Save what matters and help me start a new task.
```

You can also ask:

```text
What tasks have I done before?
```

AI agents should answer in the language you are currently using unless you ask for another language.

## Read More

For philosophy and positioning:

- [Project Philosophy](docs/project-philosophy.md)
- [Positioning Q&A](docs/positioning-qna.md)
- [Founding Intention](docs/founding-intention.md)

For architecture and protocol:

- [PROJECT_BRIEF.md](PROJECT_BRIEF.md)
- [docs/workroot-system-design.md](docs/workroot-system-design.md)
- [docs/kernel-implementation-specification.md](docs/kernel-implementation-specification.md)
- [docs/architecture-map.md](docs/architecture-map.md)
- [docs/workroot-operating-protocol.md](docs/workroot-operating-protocol.md)
- [docs/user-interaction-contract.md](docs/user-interaction-contract.md)

For contribution:

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [ROADMAP.md](ROADMAP.md)
- [AUTHOR.md](AUTHOR.md)

AI Workroot welcomes exceptional individual contributors with philosophical depth, AI engineering excellence, and strong consumer AI product judgment. For long-term contributor conversations, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Website

https://aiworkroot.com

## License

AI Workroot is licensed under the Apache License, Version 2.0.

You may use, modify, distribute, and build commercial projects from it under the license terms.

The license does not grant trademark rights to the project name, domain, future logos, or brand identity. See [TRADEMARKS.md](TRADEMARKS.md) and [NOTICE](NOTICE).

Contributions follow the lightweight [DCO.md](DCO.md) contribution rule.
