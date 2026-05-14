# AI Workroot

AI Workroot helps you use AI to do real work and continue later.

You do not need to understand this project first.

## Start In 2 Minutes

1. Download or clone this folder.
2. Rename only the outer folder if you want, such as `my-study-helper`, `my-workspace`, or `team-release-helper`.
3. Open the folder with an AI agent such as Codex or Claude Code.
4. Say one sentence:

```text
I want this workspace to help me with [area]. Please set it up with me, then help me start my first real task.
```

That is enough.

The AI should ask at most one or two simple setup questions, then help you do one real thing.

If you already have a messy problem, say it directly:

```text
I have meeting notes and many follow-ups. Help me organize them.
```

```text
I am in grade 7. Help me learn fractions, give me practice questions, and remember what I often get wrong.
```

```text
I want to write a novel, but I only have scattered ideas. Help me start.
```

```text
Our team needs to check a release. Help us start.
```

## How Work Feels

Think of one task as one thing you want to finish or keep improving.

You can still ask quick questions. If a question becomes part of a bigger goal, the AI should help turn it into a task so you can continue later.

When you come back, say:

```text
Help me continue.
```

To review previous work, ask:

```text
What tasks have I done before?
```

When one task is finished and you want a new one, say:

```text
This task is finished. Save what matters and help me start a new task.
```

You do not need to organize files, choose categories, or learn special words.

## What AI Should Do

The AI should:

1. understand what you want
2. ask only the missing question
3. help you do the work
4. save the useful result
5. answer in your language
6. remind you how to continue next time
7. summarize your local task history when you ask

For the simplest guide, read [Start Here](START_HERE_FOR_HUMANS.md).

## For AI Agents

If the agent needs a more explicit first-use instruction, the user may paste:

```text
Read AGENTS.md and START_HERE_FOR_HUMANS.md.
I am a new user.
Help me turn this folder into my own AI workspace.
Ask at most one or two missing setup questions.
If I already gave you a real problem, start helping me with it after the minimum setup.
Do not explain internal folders or ask me to manage files.
Help me save what matters and leave a clear next step.
```

## Project Overview

AI Workroot is an open-source AI workspace protocol and starter structure for people, teams, and roles.

Current release: `v0.9.527`.

It is designed to grow into an AI Workspace Operating System: simple for ordinary users, rigorous for AI agents, portable across models and tools, and durable over long-term human work.

It gives your AI work a durable home: tasks, memory, knowledge, decisions, handoffs, and reusable context that stay portable across AI agents, models, tools, and operating systems.

The simple idea:

```text
define who you are -> work with AI -> keep what matters -> grow over time
```

The daily rhythm:

```text
orient -> choose -> work -> preserve -> promote -> release -> handoff
```

For a practical operating manual, read [User SOP](docs/user-sop.md).

## Deeper Reading

If you want to understand why this project exists:

- [Founding Intention](docs/founding-intention.md): the philosophy, values, human-centered purpose, and the problem AI Workroot tries to solve

If you want to understand how it is designed:

- [Product Hardening](docs/product-hardening.md): release hardening rules for first-use simplicity, state trust, continuation views, and product-quality validation
- [AI Workspace Operating System Design](docs/ai-workspace-operating-system-design.md): the v0.9.527 user-space/kernel-space architecture and product blueprint
- [Kernel Implementation Specification](docs/kernel-implementation-specification.md): the concrete kernel versioning, contract, validation, testing, and release-gate specification for implementing the OS design
- [User Interaction Contract](docs/user-interaction-contract.md): the user-facing behavior contract that keeps ordinary use simple while the kernel remains rigorous
- [Product Experience](docs/product-experience.md): how ordinary users should start, work, save, and continue without learning the framework first
- [Architecture Map](docs/architecture-map.md): a visual map of user space, kernel space, extensions, runtime, indexes, and handoff
- [Architecture](docs/architecture.md): the overall structure, layers, responsibilities, and design principles
- [Workroot Operating Protocol](docs/workroot-operating-protocol.md): the rules AI agents should follow inside a Workroot
- [Extension Contract](docs/extension-contract.md): how role capabilities, tools, indexes, and local runtimes can extend the core without breaking it
- [Scaling And Longevity](docs/scaling-and-longevity.md): how the workspace can grow for years without becoming unreadable

## What Happens First

Before formal work begins, AI Workroot asks one simple question:

```text
Who or what does this Workroot represent?
```

The answer can be small:

```text
This Workroot represents me.
The AI should act as my long-term work and life collaborator.
It should help me clarify goals, finish tasks, preserve useful knowledge, and grow over time.
```

It can also represent a team, role, project, or organization.

Identity is not a rigid persona. It is the first anchor that lets AI understand who it is serving.

Identity content belongs in `space/profile/`, where the user can see and change it. The kernel defines the identity rules and identity gate; it does not own the user's actual identity content.

## Daily Use

Use AI Workroot naturally:

```text
This is a quick question. Answer it directly.
```

```text
Help me finish this work and preserve the useful result.
```

```text
Review this result and preserve anything useful for the future.
```

The AI should keep the user experience simple. Behind the scenes, it follows stricter rules for tasks, memory, handoff, indexes, privacy, and long-term context.

## Common Use Cases

- personal AI workspace
- team AI workspace
- role-based AI agent workspace
- portable AI memory and context management
- task and decision tracking with AI agents
- personal knowledge base for long-term work
- team knowledge base for product, testing, operations, finance, research, writing, design, or coding
- context engineering across Codex, Claude Code, and future AI agents

## What It Gives You

AI Workroot gives durable places for:

- identity: who this workspace serves
- tasks: what you are doing
- memory: what happened
- knowledge: what can be reused
- decisions: what was chosen and why
- principles: what should guide future work
- patterns: what repeats over time
- handoff: where to continue next time

It also supports forgetting and release: after a lesson is preserved, painful context can become quiet, archived, tombstoned, redacted, or deleted by user choice. A tombstone is an intentional marker for remembrance without carrying the full raw pain forward.

## Why It Exists

Most AI work disappears into chat history.

AI Workroot gives that work a durable home.

It is built from a human-centered belief:

> AI should not only help people finish more tasks.
>
> It should help people remember, understand, and grow from the things they do.

The human, team, or role remains the subject. AI is a collaborator. Models, agents, and tools are replaceable. The Workroot is the continuity layer that remains.

## Design Principles

- Philosophy-led, engineering-grounded.
- Human first, AI second.
- Identity first, then work.
- Simple for users, strict for agents.
- Global by default: users may work in any language, text stays UTF-8, and machine-readable precise time uses UTC ISO-8601.
- AI-native operating system thinking, not a clone of traditional OS concepts.
- Files are the source of truth.
- Databases and indexes are optional accelerators.
- Startup context stays small even as memory grows.
- Context is loaded progressively through summaries, indexes, and explicit links.
- Useful results should become durable knowledge.
- Old pain can be released after lessons are preserved.
- The workspace should remain portable across agents and models.

## What This Is

AI Workroot is:

- a starter workspace
- a file-first protocol
- a long-term context structure
- a shared operating method for AI agents
- a foundation for personal, team, and role-based AI work

It is not:

- a model provider
- a hosted service
- a closed memory product
- a programmer-only workflow
- a mandatory database architecture
- a replacement for human judgment

## Repository Structure

```text
ai-workroot/
  START_HERE_FOR_HUMANS.md          # Simplest first-use guide
  AGENTS.md                         # Shared entrypoint for AI agents
  CLAUDE.md                         # Thin adapter for Claude Code
  README.md                         # Project overview
  PROJECT_BRIEF.md                  # Short positioning
  AUTHOR.md                         # Creator perspective and values
  LICENSE                           # Apache-2.0 open-source license
  NOTICE                            # Attribution and brand boundary notice
  TRADEMARKS.md                     # Project name and brand usage policy
  DCO.md                            # Lightweight contribution rights rule
  space/                            # User-visible workspace
  .workroot/                        # Kernel, extensions, and rebuildable runtime state
  assets/                           # Brand direction; no final visual assets in v0.9.527
  docs/                             # Deeper architecture and operating protocol
  scripts/                          # Helper scripts
  tests/                            # Validation and compatibility tests
```

## Read Next

For normal use:

- `START_HERE_FOR_HUMANS.md`
- `docs/user-sop.md`
- `AGENTS.md`
- `docs/user-interaction-contract.md`

For deeper understanding:

- `docs/founding-intention.md`
- `docs/ai-workspace-operating-system-design.md`
- `docs/product-experience.md`
- `docs/architecture-map.md`
- `docs/architecture.md`
- `docs/daily-loop.md`
- `docs/workroot-operating-protocol.md`
- `docs/extension-contract.md`
- `docs/scaling-and-longevity.md`
- `docs/instantiate-workroot.md`
- `docs/release-checklist.md`
- `docs/launch-and-discovery.md`

For contribution:

- `CONTRIBUTING.md`
- `docs/good-first-issues.md`
- `docs/who-we-are-looking-for.md`
- `ROADMAP.md`
- `AUTHOR.md`

AI Workroot welcomes exceptional individual contributors with philosophical depth, AI engineering excellence, and strong consumer AI product judgment. For long-term contributor conversations, see `CONTRIBUTING.md`.

## Current Status

AI Workroot is at `v0.9.527`.

The current focus is to keep the first-use experience simple while preserving a rigorous protocol underneath for long-term AI-assisted work.

## Website

https://aiworkroot.com

## License

AI Workroot is licensed under the Apache License, Version 2.0.

You may use, modify, distribute, and build commercial projects from it under the license terms.

The license does not grant trademark rights to the project name, domain, future logos, or brand identity. See `TRADEMARKS.md` and `NOTICE`.

Contributions follow the lightweight `DCO.md` contribution rule.
