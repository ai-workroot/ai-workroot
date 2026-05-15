# AI Workroot Project Brief

## Name

AI Workroot

## Positioning

A human-centered AI workspace protocol for ordinary people, teams, and roles to work with AI, preserve context, build knowledge, accumulate ability, and grow over time.

It is also the seed of an AI Workspace Operating System: user space stays simple, kernel rules stay rigorous, extensions stay replaceable, and runtime state stays rebuildable.

## Founding Question

In the age of AI, how should a person or team do work, remember, reflect, decide, and grow without being locked into one model, chat product, or agent?

## Core Claim

The Workroot is the durable continuity layer. AI agents are replaceable collaborators.

## Target Users

- ordinary people using AI for work and life
- teams building shared AI workspaces
- role-based agents such as testing, product, operations, finance, research, writing, design, and coding
- people who want their knowledge and context to remain portable

## Design Philosophy

- Philosophy-led, engineering-grounded.
- Start from human continuity, then use protocol and software structure to serve that continuity.
- Human first, AI second.
- Identity first: define the subject before durable work begins.
- Simple for users, strict for agents.
- AI-native operating system design, not a traditional OS clone.
- Files are the source of truth.
- Databases and indexes are optional accelerators.
- Startup context must stay small even as the Workroot grows for years.
- Context should load progressively through boot context, summaries, indexes, registries, and explicit links.
- Machine-readable contracts should stay compact; Markdown explains the doctrine and intent.
- Memory and knowledge are different.
- Tasks produce results; results can become memory, knowledge, decisions, principles, or capabilities.
- After useful lessons are preserved, painful past context can be released from active recall by user choice.
- Other skills must operate inside the Workroot protocol.

## Public Seed Purpose

The public seed establishes the AI Workspace Operating System shape:

- README and mission
- upgraded `space/ + .workroot/` architecture
- architecture and kernel implementation specifications
- user interaction contract
- Workroot operating protocol
- Codex and Claude Code entrypoints
- `space/profile`, `space/work`, `space/mind`, `space/inbox`, and `space/files`
- `.workroot/kernel`, `.workroot/extensions`, and `.workroot/runtime`
- task lifecycle and index conventions
- scaling and longevity rules
- optional future extension points for databases, vector indexes, and graph indexes

## Not In The Public Seed

- full application
- mandatory database
- mandatory vector search
- domain-specific agent implementation
- heavy CLI
- hosted service

## Next Milestone

Validate the public seed through real personal, team, and role usage, then refine the first-use flow from actual feedback.
