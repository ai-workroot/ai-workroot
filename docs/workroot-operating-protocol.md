# Workroot Operating Protocol

This is the core operating protocol for AI agents working inside AI Workroot.

It is the foundational protocol of the project. Domain skills, tool skills, MCP integrations, and agent-specific plugins must work inside this protocol.

For ordinary user experience, also follow:

- `docs/product-experience.md`
- `docs/user-interaction-contract.md`
- `docs/kernel-implementation-specification.md`

The public seed uses the Workroot system architecture:

```text
space/       user-visible space
.workroot/   kernel, extensions, and rebuildable runtime state
```

## Space Boundary Rule

`space/` is user-owned and protocol-governed.

The user owns the durable content. The kernel owns the rules. Runtime owns rebuildable derived state.

Protocol anchors under `space/` must keep stable names and meanings:

```text
space/profile/
space/work/
space/mind/
space/inbox/
space/files/
```

Users may add other folders under `space/` for their own work.

Agents should not treat those folders as errors. When their content should become durable identity, work, knowledge, memory, source material, or continuation context, agents should connect it back to the protocol anchors through links, summaries, indexes, or preservation actions.

Agents must not create competing canonical folders for the same meanings.

## 0. Establish Subject Identity

AI Workroot must know who or what it serves before formal durable work begins.

The user may rename the outer folder to make the Workroot feel personal. Agents should not ask ordinary users to rename internal protocol folders such as `space`, `.workroot`, or `docs`.

Before creating formal internal work records or promoting durable knowledge, confirm that `space/profile/` defines the subject. In the current product direction, this should normally be:

- a person

The protocol still has room for future team, role, project, or organization subject boundaries, but those are not the default public positioning.

If identity is blank or still generic, guide the user through a minimal setup:

1. Who or what does this Workroot represent?
2. What role should the AI play?
3. What direction, work, or life area should it support?
4. What values, boundaries, or preferences should it respect?

Write the result into `space/profile/` as appropriate.

The identity can be small at first. It can be broad or specialized. It should evolve over time, but durable work should not begin without a subject.

If identity is not clear enough, do not continue with ordinary work yet. Ask only the missing identity questions, write the answers into `space/profile/`, then continue. Setup questions may be answered while guiding identity setup.

Identity content belongs to `space/profile/`.

The kernel defines identity rules, startup checks, and the identity gate. It must not store the user's actual identity content as canonical kernel state.

Runtime may keep compact identity summaries for context efficiency, but those summaries are rebuildable and subordinate to `space/profile/`.

## 1. Startup

Every agent should start with:

1. `AGENTS.md`
2. `START_HERE_FOR_HUMANS.md`
3. `.workroot/kernel/boot/boot.md` when available
4. `.workroot/kernel/boot/read-order.json` when available
5. `docs/user-interaction-contract.md`

If continuing active work, read concise continuation context:

1. `.workroot/runtime/context/current.md`
2. `.workroot/runtime/context/handoff.md`
3. relevant rows from `.workroot/runtime/index/`

Do not start by reading long historical logs.

Follow `.workroot/kernel/contracts/context-policy.json` and `docs/scaling-and-longevity.md` when choosing what enters context.

Use `docs/daily-loop.md` as the practical operating rhythm:

```text
orient -> choose -> work -> preserve -> promote -> release -> handoff
```

## 2. Classify The Work

Classify the user's request into the lightest suitable path:

- quick question
- capture or inbox item
- goal-oriented work
- recurring work
- larger project
- decision
- learning
- preservation
- continuation
- release or forgetting
- capability or workflow design

If the user is just exploring, keep it lightweight.

If the work has a goal, expected result, or future value, create or update the appropriate internal work record behind the scenes.

Do not ask ordinary users to manually create folders, choose task types, edit indexes, or decide where internal records go. Infer the right structure from intent and keep the user focused on the work.

Use the intent routing table in `docs/user-interaction-contract.md` for ordinary user requests.

## 3. Work With The User

The user should not need to understand the full architecture.

Guide them with simple language:

- "This can stay as a quick answer."
- "This has enough shape to track; I will keep it organized for you."
- "This result may be useful later; I can preserve it."
- "This looks reusable; I will save it for future work."
- "The lesson is preserved; this painful context can be released from active recall if you choose."
- "Release does not erase responsibility; it keeps the lesson while letting the raw pain become quiet."
- "If you want, we can keep only a small tombstone: a quiet marker for remembrance, without carrying the full pain forward."

Avoid exposing internal mechanics unless the user asks.

For first run, continuation, and "save what matters" behavior, follow `docs/user-interaction-contract.md`.

## 4. Maintain Internal Work State

For formal work, internal task records live under:

```text
.workroot/runtime/work/tasks/<task-id>/
```

Task status lives in `task.json` and `.workroot/runtime/index/task_registry.csv`, not in directory names.

Use the lightest process level that preserves continuity:

- `L0`: simple task state
- `L1`: process records with plans, runs, retrieval cards, and checkpoints
- `L2`: evidence records with actions, recipes, validation, and invalidations

Older Workroots may contain `.workroot/runtime/work/active/` or `closed/`. Agents may read those legacy paths, but new tasks use `tasks/<task-id>/`.

Common internal files:

```text
task.json
task.md
brief.md
decisions.md
todo.md
scratch.md
index.md
outputs/
archive/
handoff.md
```

Keep `brief.md` current.

Keep `todo.md` limited to remaining work.

Do not make long scratch history a startup requirement.

Use `handoff.md` for task-level continuation context.

Before closing a task, compress the task into a small effective record: final `brief.md`, decisions, outputs, related links, promoted Mind entries, and a short handoff. Move noisy process material out of default context.

User-facing outputs, summaries, and reports belong in:

```text
space/work/
```

## 5. Promote What Matters

After work produces value, decide what to do:

| Output type | Destination |
| --- | --- |
| user-facing task result | `space/work/` |
| internal task state | `.workroot/runtime/work/` |
| meaningful experience | `space/mind/memory/` |
| reusable understanding | `space/mind/knowledge/` |
| operating principle | `space/mind/principles/` |
| important choice | `space/mind/decisions/` |
| repeated pattern | `space/mind/patterns/` |
| reflection | `space/mind/reflections/` |
| wrong or obsolete belief | `space/mind/invalidated/` |
| past context the user chooses not to actively carry forward | `space/mind/released/` |
| external source | `space/files/` |
| repeatable workflow | `.workroot/extensions/capabilities/` |

Ask confirmation before preserving sensitive, private, emotionally heavy, or team-visible material.

## 6. Update Indexes

Important objects should be findable without full-text search.

Maintain registries under:

```text
.workroot/runtime/index/
```

Core registries should cover:

- task registry
- run registry
- action registry
- artifact registry
- decision registry
- retrieval card registry
- checkpoint registry
- invalidation registry
- mind registry
- link registry

The public seed can use Markdown, JSON, and CSV.

Future local databases or vector/graph indexes are accelerators only.

Core registries should stay stable and role-independent. Domain capabilities may add their own registries, but those registries belong to the capability and should not redefine the core protocol.

Role, domain, tool, runtime, database, and index extensions should follow `docs/extension-contract.md`.

When using SQLite, rebuild it from CSV registries when tooling is available.

Use validation scripts when available to check registry paths, work records, relationships, contracts, and generated store integrity.

For released context, default to `quiet` unless the user explicitly chooses archival, tombstone, redaction, or deletion. Deletion must be explicit and should not leave a detailed hidden archive.

For long-lived entries, maintain lifecycle metadata when available: status, temperature, confidence, last used date, review date, and replacement links.

## 7. Preserve Relationships

Important files should link to related objects:

- source work
- source memory
- source artifact
- related decision
- related principle
- related capability
- invalidated or replacement record

The Workroot should become a knowledge network over time.

## 8. Handoff

Before ending a long session or when context may be lost:

1. update active work `brief.md`
2. update `decisions.md`
3. update `todo.md`
4. write or update active work `handoff.md`
5. write or update `.workroot/runtime/context/handoff.md`
6. update relevant registries

The next agent should not need to reconstruct state from chat history.

## 9. Respect Portability

Never trap durable context in one agent's private memory.

If something matters, write it into the Workroot.

Agents can change. Models can change. The Workroot remains.

## 10. Respect The Human

AI Workroot is not a productivity whip.

It should help people work, remember, understand, decide, release what no longer needs to stay active, and grow with more clarity and steadiness.
