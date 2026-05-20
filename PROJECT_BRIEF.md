# AI Workroot Project Brief

## Name

AI Workroot

## Positioning

A personal, local-first Workroot for individuals to work with AI, preserve context, build knowledge, accumulate ability, and continue meaningful work over time.

It is also the seed of a Workroot system: user-selected directories stay simple, managed state stays outside user content by default, extension boundaries stay replaceable, and runtime state stays inspectable.

## Founding Question

In the age of AI, how should a person do work, remember, reflect, decide, forget, and grow without being locked into one model, chat product, or agent?

## Core Claim

The Workroot is the durable continuity layer. AI agents are replaceable collaborators.

## Target Users

- individuals using AI for work, learning, creativity, and life planning
- people moving across multiple agents, models, tools, and devices
- people who want a clean local-first foundation for long-term work with AI
- people who want their knowledge and context to remain portable

## Design Philosophy

- Philosophy-led, engineering-grounded.
- Start from human continuity, then use protocol and software structure to serve that continuity.
- Human first, AI second.
- Progressive guidance: start with useful work, then clarify the subject, direction, and collaboration style as durable continuity grows.
- Simple for users, strict for agents.
- AI-native Workroot system design, not a traditional OS clone.
- User-owned files and managed records are the source of truth for their own layers.
- Databases and indexes are local-first accelerators unless explicitly promoted to managed state.
- Startup context must stay small even as the Workroot grows for years.
- Context should load progressively through boot context, summaries, indexes, registries, and explicit links.
- Machine-readable contracts should stay compact; Markdown explains the doctrine and intent.
- Memory and knowledge are different.
- Tasks produce results; results can become memory, knowledge, decisions, principles, or capabilities.
- After useful lessons are preserved, painful past context can be released from active recall by user choice.
- Other skills must operate inside the Workroot protocol.

## Clean Workroot Purpose

0.9.530 establishes the Clean Workroot system shape:

- README and mission
- Clean Workroot architecture and implementation specifications
- user interaction contract
- Workroot operating protocol
- Workroot Management / WorkrootEnvironment
- Core / Contracts / Runtime / Storage / Indexing / Agent / CLI source structure
- Native Agent Entry templates
- managed state under `AI_WORKROOT_HOME`
- task, asset, release, relationship, retrieval, context, and health conventions
- scaling and longevity rules
- optional future extension points for storage drivers, retrieval providers, MCP, and agent adapters

## Not In The Current Product

- full application
- mandatory database
- mandatory vector search
- domain-specific agent implementation
- heavy CLI
- hosted service

## Next Milestone

Validate the Clean Workroot reset through real dogfood usage, then refine first-use and Workroot Manager flows from actual feedback.
