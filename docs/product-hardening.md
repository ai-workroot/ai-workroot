# Product Hardening Rules

This document defines product hardening rules for AI Workroot v0.9.527.

It does not change the philosophy or the operating-system architecture. It tightens the product boundary so ordinary users can begin, continue, and trust the workspace without learning internal mechanics.

## Problem Statement

The architecture can support personal, team, role, writing, and executive scenarios. The main product risk is not kernel capability. The risk is ordinary-user trust.

AI Workroot must prevent four common product failures:

1. The first visible path still contains too much system language before the user sees what to say first.
2. Tasks can have reports, decisions, or knowledge while their task summaries still look untouched.
3. Internal registries can model relationships, but ordinary users need a plain-language continuation view.
4. Release validation proves structure, but does not yet catch enough product-state drift.

## Design Goals

- Let a new user start with one natural sentence.
- Keep the full architecture available, but after the first useful action.
- Make continuation visible in plain language.
- Keep registry and task state synchronized enough that users can trust handoff.
- Let teams see relationship maps without reading registry files.
- Strengthen release validation without making the daily user experience heavier.

## Non-Goals

- Do not add a heavy UI.
- Do not force users to run scripts.
- Do not require a database for normal operation.
- Do not add domain-specific folders to the kernel.
- Do not expose registries, schemas, or kernel files to ordinary users unless they ask for internal details.

## First-Use Design

The first user action should be a single sentence:

```text
I want this workspace to help me with [area]. Please set it up with me, then help me start my first real task.
```

This sentence is the primary product entry. Longer prompts are reliability helpers for advanced agents, not the default user-facing experience.

The first-run agent flow is:

1. Read the minimal agent entry files.
2. Check whether identity is clear enough.
3. Ask only missing identity questions.
4. Save identity in `space/profile/`.
5. Start the first real task.
6. Preserve the first useful result.
7. Update the human continuation view.
8. Leave a concise handoff.

The user should not need to read architecture documents, understand the kernel, or choose folders.

## Human Continuation View

AI Workroot should maintain a user-facing continuation view at:

```text
space/work/continue.md
```

This file is for humans. It should answer:

- What were we doing?
- What was finished?
- What matters now?
- What needs a decision?
- What should happen next?

It may be generated or manually maintained by the AI agent. The user should not need to edit it.

The internal handoff under `.workroot/runtime/context/handoff.md` remains useful for agents. The human continuation view is the product-facing equivalent.

## Team Collaboration Map

For team or delegated work, the continuation view should include a plain-language map:

- parent work
- delegated work
- findings
- outputs
- decisions
- promoted knowledge
- next human decision

`link_registry.csv` remains the machine-readable relationship layer. It should not be the only way a team lead understands the work.

Agents may maintain a richer team map under `space/work/` when useful, but the kernel does not require a domain-specific team folder.

## State Synchronization Invariant

When an AI agent creates or updates a meaningful result, decision, or Mind entry for a task, it must also update the task state enough for the next session to continue.

At minimum, keep these aligned:

- task `brief.md`
- task `todo.md`
- task `handoff.md`
- task `index.md`
- task `task.json`
- `task_registry.csv`
- related artifact, decision, Mind, and link registry rows
- `space/work/continue.md`
- `.workroot/runtime/context/handoff.md`

The user should never see meaningful output while the related task still says:

- `Task created; no work completed yet.`
- `Nothing yet.`
- `Short continuation status.`
- `What should happen next?`

Those phrases are allowed only in templates or genuinely untouched tasks.

## Release Validation Hardening

Release validation should reject product-state drift that would damage user trust.

The release gate must catch:

- registry paths that do not exist
- active tasks with related output but no user-visible output path
- task files that still contain template placeholders after related output, decisions, Mind entries, or links exist
- global handoff that remains empty while active tasks exist
- future UTC timestamps beyond a small tolerance
- generated runtime stores or local metadata
- stale legacy terminology

This keeps product quality enforceable without asking users to understand the protocol.

## Agent Behavior Hardening

Agents must not expose internal files as user instructions.

Bad ordinary-user handoff:

```text
Use link_registry.csv to understand delegated work.
```

Good ordinary-user handoff:

```text
The payment retry finding is linked internally to the release review. Next, confirm it with product and engineering.
```

Agents may still update registries behind the scenes.

## Product Success Criteria

AI Workroot v0.9.527 meets the product hardening bar when:

- a new user can find the first sentence within seconds
- the first useful result can be preserved without architecture reading
- `space/work/continue.md` gives a plain next step when useful work exists
- release validation catches stale task state
- ordinary handoffs avoid kernel and registry vocabulary
- all existing kernel tests and release validation pass
