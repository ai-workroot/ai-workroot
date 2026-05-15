# AI Workroot

AI Workroot is the missing continuity layer for AI-era work.

It is a human-owned, file-first workspace protocol that gives humans, teams, roles, and projects sovereignty over their working context: tasks, process, artifacts, decisions, knowledge, memory, handoff, invalidation, release, and forgetting live in their own filesystem, not inside one agent, model, tool, or chat session.

AI Workroot is not an agent.
It is the workspace protocol agents operate inside.

AI Workroot is not a memory feature.
It is a continuity layer owned by the subject it serves.

If you only want to use the workspace directly, start with [START_HERE_FOR_HUMANS.md](START_HERE_FOR_HUMANS.md). This README is for people evaluating AI Workroot as an architecture, protocol, or foundation for serious long-term human-AI work.

## The Missing Layer In AI Work

Most AI work still disappears into sessions.

A model answers.
An agent edits files.
A tool completes a task.
A conversation ends.

Some outputs remain, but the work itself often loses continuity:

- What was the task?
- What state is it in?
- Where is the result?
- What should happen next?
- Which decision was made, and why?
- Which conclusion has become invalid?
- Which output should become reusable knowledge?
- Which old context should stop returning to active memory?
- Can a different agent continue without reading the whole past?

Current AI systems are increasingly good at execution. They can write code, browse, operate tools, run workflows, and remember some context.

But execution is not the same as durable work continuity.

AI Workroot exists because long-term human-AI work needs a stable home that does not belong to any single agent, model, provider, or chat session.

## Core Claim

The Workroot is the durable continuity layer.

AI agents are replaceable collaborators.

The human, team, role, project, or organization remains the subject. The workspace preserves what matters so future work can continue without being trapped inside one model's memory, one agent's runtime, or one conversation's history.

## Core Capabilities

AI Workroot is built around four capabilities:

1. Context sovereignty
2. Work lifecycle management
3. Cross-agent continuity
4. Layered memory and intentional forgetting

These are the reasons the protocol exists. The folders, registries, schemas, and validation scripts are implementation details that serve these four capabilities.

## What It Is / What It Is Not

| It is not... | It is... |
| --- | --- |
| an agent runtime | the workspace protocol agents operate inside |
| a model memory feature | a human-owned filesystem for durable context |
| a workflow engine | the lifecycle layer that preserves what work means over time |
| a flat memory store | a layered mind system with forgetting and tombstones |
| a prompt pack | a protocol with files, contracts, registries, runtime state, and validation |
| a replacement for Codex, Claude Code, OpenClaw, Hermes, or future agents | the continuity substrate across them |

AI Workroot is intentionally thin.

The protocol layer defines the durable workspace, lifecycle structure, memory taxonomy, handoff rules, registries, release semantics, and validation boundaries.

Execution can be done by agents.
Automation can be done by workflow engines.
Retrieval can be accelerated by databases or indexes.
Reasoning can be done by models.

AI Workroot defines the shared home where those systems work.

## Context Sovereignty

Context that matters should belong to the human, team, role, or project, not to an agent runtime.

AI Workroot puts important context into the user's own filesystem.

The user can see it.
The user can edit it.
The user can version it.
The user can move it.
The user can audit it.

Agents can change.
Models can change.
Tools can change.
Conversations can disappear.

The Workroot remains.

This is the first principle of AI Workroot: durable context should not be locked inside an agent's private memory, a model provider's session, or an opaque product database.

AI Workroot makes durable context human-owned and file-visible by default.

## Work Lifecycle Management

Many agents are strong at doing work. They are weaker at managing the full lifecycle of work.

A serious task is not just a prompt.
It is not just a todo item.
It is not just a final output.

A task has state, process, artifacts, decisions, invalidations, handoffs, and possible knowledge promotion.

AI Workroot turns this into protocol structure:

- `Task`: what is being done
- `Run`: a bounded execution attempt
- `Action`: a meaningful operation or step
- `Artifact`: a saved output or evidence object
- `Decision`: a choice that should remain traceable
- `Handoff`: what the next agent or future session needs
- `Registry`: a lightweight index for finding work without loading everything
- `Mind`: durable memory, knowledge, principles, patterns, reflections, and release markers
- `Invalidation`: a record that something should no longer be trusted
- `Release`: a mechanism for moving old context out of active recall

This is the work lifecycle layer.

It answers questions that ordinary execution agents often leave implicit:

- What is the current status?
- What was produced?
- Where is the result?
- What is the next action?
- What has become obsolete?
- What should be promoted into durable knowledge?
- What should be released from active context?

AI Workroot does not only preserve outputs. It preserves the meaning and state of the work.

## Cross-Agent Continuity

Agent memory helps an agent remember.

AI Workroot helps a human, team, role, or project continue.

Today you may use Codex.
Tomorrow you may use Claude Code.
Later you may use OpenClaw, Hermes, a local agent, a team agent, or a future tool that does not exist yet.

The Workroot should still make the work understandable and continuable.

This is possible because the workspace does not depend on one agent's internal memory. It stores durable context, task state, outputs, decisions, handoffs, and knowledge in a shared file-first protocol.

AI Workroot is not a multi-agent platform in the narrow sense. It is a lower-level continuity substrate:

```text
agent is replaceable
model is replaceable
tool is replaceable
workspace remains
```

Strong agents become more useful when they share a durable workspace that is not owned by any one of them.

## Layered Memory And Intentional Forgetting

Many AI memory systems are flat.

They remember user preferences, project facts, and historical summaries in one broad layer.

AI Workroot treats memory as structured and governed.

It separates:

- `memory`: what happened
- `knowledge`: reusable understanding
- `decision`: what was chosen and why
- `principle`: a durable rule or value
- `pattern`: something that repeats over time
- `reflection`: deeper review of experience
- `invalidation`: what should no longer be believed
- `release`: what should leave active context
- `tombstone`: a minimal marker that something existed without bringing back the full raw context

This matters because human life is not only memory accumulation.

People, teams, and organizations must also forget, release, quiet, archive, redact, and move forward.

AI Workroot is grounded in a human-centered philosophy of continuity, growth, and release. It should not force every old event, mistake, obsolete belief, or painful context back into every future session.

The useful lesson can remain.
The raw context can become quiet.
A tombstone can preserve responsibility without keeping the past alive in active recall.

This is not just data management. It is a life-oriented view of context.

## Remembering, Forgetting, And Moving Forward

AI Workroot treats forgetting as a first-class operation.

The goal is not infinite recall.
The goal is future-oriented continuity.

A human life is not a database append log.

A team also cannot carry every old discussion, mistake, emotion, and obsolete assumption into every future decision.

After the useful lesson is preserved, the original context may be:

- kept active
- quieted
- archived
- tombstoned
- redacted
- deleted by explicit choice

A tombstone is not active memory.

It is a minimal marker that acknowledges something existed without forcing the full raw context back into future sessions.

This allows a Workroot to preserve responsibility without trapping the subject in the past.

The goal is not to remember everything.

The goal is to preserve what helps future action, growth, judgment, and continuity.

## Architecture

AI Workroot uses a simple public architecture:

```text
space/       user-owned workspace
.workroot/   kernel, runtime, indexes, and protocol state
```

### `space/`

`space/` is where human-owned durable content lives.

It includes:

```text
space/profile/   who or what this Workroot serves
space/work/      user-visible outputs and continuation views
space/mind/      memory, knowledge, decisions, principles, patterns, release
space/inbox/     raw incoming material
space/files/     user-provided source files
```

The user owns this space.

Agents should make it useful without forcing the user to understand the internal protocol.

### `.workroot/`

`.workroot/` is the protocol and runtime layer.

It includes:

```text
.workroot/kernel/      rules, contracts, schemas, boot policy
.workroot/runtime/     task process state, indexes, context, logs
.workroot/extensions/  optional capabilities, skills, adapters, drivers
```

The kernel defines the operating law of the workspace.

Runtime state is rebuildable where possible. Indexes and registries help agents find the right context without loading the entire history.

## Work Process Layer

AI Workroot treats task process as a first-class protocol layer.

Tasks can operate at different process levels:

```text
L0  simple task state
L1  process task with plans, runs, retrieval cards, checkpoints
L2  evidence task with actions, recipes, validation, invalidations
```

This keeps small work light while allowing serious work to be auditable.

A small task should not create unnecessary ceremony.
A risky task should not hide its process in chat history.

The Work Process Layer is designed to answer:

- what work is active
- what has been tried
- what evidence exists
- what output was produced
- what is still valid
- what has been invalidated
- what the next agent needs to know

This is one of the core differences between AI Workroot and ordinary agent memory.

## Mind Layer

The Mind layer is where useful experience becomes durable.

AI Workroot separates short-term task process from long-term reusable meaning.

A task may produce:

- a report
- a decision
- a reusable insight
- a principle
- a pattern
- an invalidation
- a release marker
- a tombstone

These should not all be stored as the same kind of memory.

The Mind layer gives them different homes and different retrieval expectations.

Some entries should be hot and active.
Some should be cold.
Some should be released.
Some should never return to startup context unless explicitly requested.

This is how AI Workroot avoids turning long-term memory into context noise.

## How It Relates To Agents And Frameworks

AI Workroot does not compete with agents that execute, remember, or self-improve.

It gives them a shared workspace protocol.

```text
Agents execute.
Tools operate.
Models reason.
Workflows coordinate.
AI Workroot preserves continuity.
```

Workflow systems can orchestrate steps.
AI Workroot preserves what those steps mean over time.

Coding agents can edit repositories.
AI Workroot preserves the larger task, decision, and handoff context around those edits.

Self-improving agents can generate skills and learn from experience.
AI Workroot gives that learning a human-owned structure, including boundaries for invalidation and release.

## Why File-First

AI Workroot is file-first because durable human-AI work should be inspectable, portable, recoverable, and tool-independent.

Files can be read by humans.
Files can be versioned by Git.
Files can be edited by different agents.
Files can be moved across machines.
Files can survive product changes.
Files can be indexed later.

Databases, vector indexes, graph stores, and local caches can be useful accelerators, but they should not become the canonical truth by default.

The source of truth should remain simple enough to inspect and strong enough to validate.

## Validation And Trust

A workspace protocol only matters if agents can be held to it.

AI Workroot includes lightweight validation for:

- required layout
- kernel contracts
- registry headers
- task state consistency
- path validity
- future timestamp rejection
- release surface checks
- stale placeholder detection
- generated store exclusion
- public seed boundaries

This keeps the protocol from becoming only documentation.

The goal is not heavy bureaucracy.
The goal is enough structure that future agents can trust the workspace.

## Current Status

AI Workroot is currently a public file-first seed for the AI Workspace Operating System direction.

Current kernel version:

```text
0.9.528
```

The current implementation includes:

- `space/ + .workroot/` architecture
- agent entrypoints
- kernel contracts and schemas
- task process layer
- CSV registries
- Mind taxonomy
- release and tombstone concepts
- validation scripts
- ordinary-user start documents
- operating protocol for AI agents

It is intentionally not a full hosted product, not a mandatory database system, and not a complete agent runtime.

The next stage is to validate the protocol through real personal, team, and role-based work, then harden the lifecycle, memory, forgetting, extension, and cross-agent continuation layers.

## Repository Structure

```text
ai-workroot/
  README.md
  START_HERE_FOR_HUMANS.md
  AGENTS.md
  CLAUDE.md
  PROJECT_BRIEF.md
  AUTHOR.md
  LICENSE
  NOTICE
  TRADEMARKS.md
  CONTRIBUTING.md
  DCO.md
  ROADMAP.md

  space/
    profile/
    work/
    mind/
    inbox/
    files/

  .workroot/
    kernel/
    runtime/
    extensions/

  docs/
  scripts/
  tests/
```

## Read Next

For direct use:

- [START_HERE_FOR_HUMANS.md](START_HERE_FOR_HUMANS.md)
- [docs/user-sop.md](docs/user-sop.md)

For agent behavior:

- [AGENTS.md](AGENTS.md)
- [CLAUDE.md](CLAUDE.md)
- [docs/workroot-operating-protocol.md](docs/workroot-operating-protocol.md)
- [docs/user-interaction-contract.md](docs/user-interaction-contract.md)

For architecture:

- [PROJECT_BRIEF.md](PROJECT_BRIEF.md)
- [docs/ai-workspace-operating-system-design.md](docs/ai-workspace-operating-system-design.md)
- [docs/kernel-implementation-specification.md](docs/kernel-implementation-specification.md)
- [docs/architecture-map.md](docs/architecture-map.md)

For product philosophy and long-term context:

- [docs/founding-intention.md](docs/founding-intention.md)
- [docs/product-hardening.md](docs/product-hardening.md)
- [docs/scaling-and-longevity.md](docs/scaling-and-longevity.md)

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
