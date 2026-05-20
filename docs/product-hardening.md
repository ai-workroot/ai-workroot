# Product Hardening Rules

This document defines product hardening rules for AI Workroot.

It does not change the philosophy or the Workroot system architecture. It tightens the product boundary so ordinary users can begin, continue, and trust the Workroot without learning internal mechanics.

## Problem Statement

The architecture can support many personal scenarios, including writing, learning, executive work, and long-term projects. The main product risk is not system capability. The risk is ordinary-user trust.

AI Workroot must prevent four common product failures:

1. The first visible path still contains too much system language before the user sees what to say first.
2. Work can have reports, decisions, or knowledge while its summaries still look untouched.
3. Internal relationship records can model links, but ordinary users need a plain-language continuation view.
4. Release validation proves structure, but does not yet catch enough product-state drift.

## Design Goals

- Let a new user start with one natural sentence.
- Keep the full architecture available, but after the first useful action.
- Make continuation visible in plain language.
- Keep relationship, retrieval, and work state synchronized enough that users can trust handoff.
- Let users see relationship maps without reading registry files.
- Strengthen release validation without making the daily user experience heavier.

## Non-Goals

- Do not add a heavy UI.
- Do not force users to run scripts.
- Do not require a database for normal operation.
- Do not add domain-specific folders to the user directory by default.
- Do not expose registries, schemas, or managed state internals to ordinary users unless they ask for internal details.

## First-Use Design

The first user action should be a single sentence:

```text
I want this Workroot to help me with [area]. Please set it up with me, then help me start my first real task.
```

This sentence is the primary product entry. Longer prompts are reliability helpers for advanced agents, not the default user-facing experience.

The first-run agent flow is:

1. Use the active Native Agent Entry or CLI context package when available.
2. Check whether usage direction is clear enough.
3. Ask only the missing guidance needed to preserve durable work responsibly.
4. Save the guidance in managed Workroot state.
5. Start the first real task.
6. Preserve the first useful result.
7. Update the human continuation view.
8. Leave a concise handoff.

The user should not need to read architecture documents, understand internal state, or choose folders.

## Human Continuation View

AI Workroot should maintain a user-facing continuation view when useful work exists.

This view is for humans. It should answer:

- What were we doing?
- What was finished?
- What matters now?
- What needs a decision?
- What should happen next?

It may be rendered in conversation, generated as an authorized user-facing asset, or stored in managed state for future context packages. The user should not need to edit it.

The managed handoff remains useful for agents. The human continuation view is the product-facing equivalent.

## Collaboration Map

For delegated or multi-part work, the continuation view should include a plain-language map:

- parent work
- delegated work
- findings
- outputs
- decisions
- promoted knowledge
- next human decision

Relationship records remain the machine-readable relationship layer. They should not be the only way a user understands the work.

Agents may maintain a richer relationship map when useful, but the system does not require a domain-specific collaboration folder in the user directory.

## State Synchronization Invariant

When an AI agent creates or updates a meaningful result, decision, or knowledge entry for a task, it must also update the task state enough for the next session to continue.

Task-local state must stay aligned:

- task brief
- task todo
- task handoff
- task index
- task metadata
- related run, action, asset, retrieval, checkpoint, invalidation, decision, knowledge, and relationship records

Session/global continuation must stay aligned when a session is summarized or rebuilt:

- human-facing continuation view
- managed handoff
- current or selected work records

Use `session summarize` for explicit multi-task continuation. Use `continue rebuild` to regenerate the human continuation view from managed work and relationship records.

Task-local updates must not overwrite global continuation just because one task changed.

The user should never see meaningful output while the related task still says:

- `Task created; no work completed yet.`
- `Nothing yet.`
- `Short continuation status.`
- `What should happen next?`

Those phrases are allowed only in templates or genuinely untouched tasks.

## Release Validation Hardening

Release validation should reject product-state drift that would damage user trust.

The release gate must catch:

- referenced paths that do not exist
- active tasks with related output but no user-visible output path or summary
- task records that still contain template placeholders after related output, decisions, knowledge entries, or relationships exist
- global handoff that remains empty while active tasks exist
- future UTC timestamps beyond a small tolerance
- generated runtime stores or local metadata committed by accident
- stale legacy terminology

This keeps product quality enforceable without asking users to understand the protocol.

## Agent Behavior Hardening

Agents must not expose internal files as user instructions.

Bad ordinary-user handoff:

```text
Use the relationship registry to understand delegated work.
```

Good ordinary-user handoff:

```text
The payment retry finding is linked internally to the release review. Next, confirm it with product and engineering.
```

Agents may still update managed records behind the scenes.

## Product Success Criteria

AI Workroot meets the product hardening bar when:

- a new user can find the first sentence within seconds
- the first useful result can be preserved without architecture reading
- the continuation view gives a plain next step when useful work exists
- release validation catches stale task state
- ordinary handoffs avoid internal vocabulary
- all existing tests and release validation pass
