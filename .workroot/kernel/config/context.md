# Context Policy

AI Workroot must keep startup context small even when the Workroot becomes large.

## Default Startup Context

Agents may read:

- `AGENTS.md`
- `START_HERE_FOR_HUMANS.md`
- `.workroot/kernel/boot/boot.md`
- concise profile files under `space/profile/`
- `.workroot/runtime/context/current.md`
- `.workroot/runtime/context/handoff.md`
- relevant registry rows

Agents should not read long historical logs, old task archives, raw data, generated databases, or released material by default.

## Active Task Context

For active tasks, prefer:

- `task.md`
- `brief.md`
- `handoff.md`
- `index.md`
- `todo.md`
- recent decisions

Use `scratch.md`, `archive/`, and large outputs only when a concrete question requires them.

## Retrieval Temperature

Use retrieval temperature to decide what enters context:

- `hot`: default candidate for startup and active work
- `warm`: retrieve when relevant
- `cold`: retrieve only through explicit search or links
- `archived`: retrieve only for review or audit
- `released`: do not retrieve by default
- `tombstone`: retrieve only for intentional remembrance
- `deleted`: do not retrieve

## Context Hygiene

Before ending long work:

- summarize current state
- update handoff
- move noisy process material out of active context
- promote durable lessons into Mind
- update indexes

The next agent should not need to read the whole past to continue.
