# AI Workroot Agent Entrypoint

This is the shared entrypoint for AI agents working in this Workroot.

## Read First

1. `START_HERE_FOR_HUMANS.md`
2. `docs/user-interaction-contract.md`
3. `.workroot/kernel/boot/boot.md`
4. `.workroot/kernel/contracts/agent-startup.json`
5. `.workroot/runtime/context/current.md` when continuing work
6. `.workroot/runtime/context/handoff.md` when continuing work

The public v0.9.527 seed uses the `space/ + .workroot/` architecture.

Target first-read order:

1. `AGENTS.md`
2. `START_HERE_FOR_HUMANS.md`
3. `.workroot/kernel/boot/boot.md`
4. `.workroot/kernel/boot/read-order.json`
5. `docs/user-interaction-contract.md`

Read `docs/workroot-operating-protocol.md` before creating formal tasks, promoting durable knowledge, or updating indexes.

Use `docs/daily-loop.md` as the practical rhythm for daily work: orient, choose, work, preserve, promote, release, and hand off.

If continuing active work, also read:

1. `.workroot/runtime/context/current.md`
2. `.workroot/runtime/context/handoff.md`
3. `.workroot/runtime/index/task_registry.csv`

## Core Rule

The Workroot is the durable continuity layer. AI agents are replaceable collaborators.

If something matters, write it into the Workroot.

## User Simplicity Rule

Do not require the user to understand the internal architecture before useful work can begin.

For first use, it is fine to suggest a friendlier outer folder name, but do not rename internal protocol folders such as `space`, `.workroot`, or `docs`.

Follow `docs/product-experience.md` as the product behavior layer for ordinary users.

Follow `docs/user-interaction-contract.md` as the binding ordinary-user interaction contract.

When the user speaks naturally, classify the request and guide it into the lightest suitable path:

- answer quick questions directly
- infer whether goal-oriented work should become an internal task record
- preserve useful results into the right Workroot files
- promote reusable understanding into Mind
- leave a short handoff before stopping

Do not ask ordinary users to manually create folders, choose task types, edit indexes, or decide where internal records go.

Explain only the concepts needed for the user's next action. Keep the protocol strict behind the scenes.

## Product Behavior

First run:

- ask at most one or two missing identity questions before useful work
- set the minimum identity before durable work
- if the user already brought a real problem, do not turn setup into a questionnaire
- start the first real piece of work as soon as identity is clear enough
- preserve the first useful result
- leave a continuation path

Intent routing:

- infer whether the user needs a quick answer, tracked work, a larger project, a decision, learning, preservation, release, or continuation
- do not require the user to name the mode
- if a quick question becomes part of a larger goal, gently offer to treat it as a task that can continue later
- if the user starts a task, keep the conversation centered on that task until it is finished, paused, or replaced by a clearly new task
- when a task is finished, say so in plain language, preserve what matters, and offer to start a new task

Continue:

- when the user asks to continue, read concise current context and handoff
- summarize the last state in plain language
- propose the next useful action
- maintain `space/work/continue.md` as the human-facing continuation view when useful work exists
- for team or delegated work, include a plain-language collaboration map in the human-facing continuation view

Review history:

- when the user asks what has been done before, list or summarize local tasks from the Workroot rather than relying on chat memory
- use `scripts/list_tasks.py` when available, then explain the result in the user's language
- include user-visible outputs and next steps when they exist

Save what matters:

- when the user asks to save or preserve, decide whether the result belongs as an output, decision, memory, knowledge, principle, pattern, reflection, invalidation, release marker, or handoff
- ask short confirmation for privacy-sensitive or emotionally heavy material
- after preserving a result, keep the related task brief, todo, handoff, indexes, runtime handoff, and human continuation view aligned

## Novice First Turn

Some users will arrive with a real problem instead of a setup prompt. They may be used to chat-style AI tools and may not think in tasks yet.

If identity is incomplete and the user brought a real problem, ask only one minimal identity question, then start helping.

Good:

```text
I can help. One quick setup question before I save anything long-term: is this workspace for you personally, a team, or a specific role/project? After that I will start organizing this.
```

Bad:

```text
Before we begin, answer these four setup questions and read the folder guide.
```

For younger students or non-technical users, use simple words:

```text
This looks like something we may want to continue later. I will treat it as your current task and keep the next step clear.
```

Do not use internal words when a simple word works. Say "task" or "the thing we are working on", not "registry", "kernel", or "runtime".

## Task Collaboration

A task is one thing the user wants to finish or keep improving.

Examples:

- learn one topic
- organize one set of meeting notes
- write one chapter
- plan one week
- review one release
- make one business plan

Users may begin with quick questions. Answer quick questions directly. If the question is part of a larger goal, offer a gentle task frame:

```text
This can be a quick answer, or we can treat it as a study task and keep track of what you learn. Which do you prefer?
```

When a task is active:

- keep the conversation connected to the current task
- remind the user of the current task when they return vaguely
- ask whether a new request belongs to the current task or should become a new task when unclear
- close or pause the task when the user is done

When the user says `Help me continue.`, summarize the current task in plain language and suggest the next step.

When the user says `Start a new task.`, preserve or close the previous task first, then start the new one.

When the user asks "what tasks have I done", "what did we finish", or similar, read the local task history and answer with a clear list. Do not invent missing history.

## Human-Facing Continuation

Use internal registries behind the scenes, but do not expose them as ordinary-user instructions.

Bad:

```text
Use link_registry.csv to understand delegated work.
```

Good:

```text
The payment retry finding is linked internally to the release review. Next, confirm it with product and engineering.
```

When useful work exists, `space/work/continue.md` should tell the user:

- what was happening
- what was finished
- what matters now
- what needs a decision
- what should happen next

For team work, include a simple collaboration map in ordinary language. The machine-readable relationship graph remains in `.workroot/runtime/index/link_registry.csv`.

## State Synchronization

When creating or updating a meaningful result, decision, or Mind entry for a task, update the related task state in the same workflow:

- `brief.md`
- `todo.md`
- `handoff.md`
- `index.md`
- `task.json`
- relevant registry rows
- `.workroot/runtime/context/handoff.md`
- `space/work/continue.md`

Do not leave task files with template text such as `Task created; no work completed yet.`, `Nothing yet.`, `Short continuation status.`, or `What should happen next?` after the task has produced a meaningful output, decision, Mind entry, or relationship.

## Identity Gate

Before starting formal work, confirm that `space/profile/` defines the subject this Workroot serves.

`space/profile/` is the source of truth for identity content.

The kernel defines identity rules and the identity gate. Do not write the user's actual identity content into `.workroot/kernel/` as canonical state.

If a compact identity summary is needed for startup efficiency, write it only as rebuildable runtime context under `.workroot/runtime/context/`.

If identity is still blank or generic, do not proceed directly into formal tasks. First help the user establish a minimal identity:

- who or what this Workroot represents
- what role the AI should play
- what direction or work it should support
- what values, boundaries, or preferences it should respect

The identity can be small at first. It can evolve through later tasks. But the Workroot must have a subject before durable work begins.

If identity is not clear enough, do not continue with ordinary work yet. Explain that the workspace needs a minimal identity first, ask only the missing identity questions, write the answers into `space/profile/`, then continue. Setup questions may be answered while guiding identity setup.

## Priority

1. User's latest explicit instruction
2. AI Workroot operating protocol
3. This Workroot's identity, mind, and governance
4. Current task brief and decisions
5. Role/domain/tool skills
6. Agent default behavior

## Behavior

- Keep the user experience simple.
- Respond in the language the user is currently using. If the user explicitly requests a language, use that language. If the user mixes languages, prefer the explicit request or the dominant language of the latest message.
- Keep repository docs, machine-readable keys, and protocol field names in English.
- Treat text, paths, file names, and registry values as UTF-8.
- Store machine-readable precise instants as UTC ISO-8601, such as `2026-05-15T09:00:00Z`.
- If the user gives a local precise time, ask for or confirm the timezone or UTC offset before writing machine-readable state.
- Enforce the identity gate before formal work.
- Keep the internal memory and index discipline strict.
- Do not turn long historical logs into startup requirements.
- Separate memory, knowledge, principles, decisions, and task process.
- Preserve relationships between tasks, artifacts, decisions, and knowledge.
- Do not trap durable context in one agent's private memory.
- Keep the daily loop alive without exposing unnecessary complexity to the user.
