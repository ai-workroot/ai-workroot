# Workroot Agent Protocol Bridge Design

Date: 2026-06-01
Target release line: 0.9.531
Status: implemented on branch `feat/0.9.531-agent-protocol-task-continuity`

## Purpose

This design refines the Workroot Agent protocol after the task-continuity implementation. The goal is to make the protocol a clean bridge between Workroot and any Agent/LLM runtime:

- Workroot should coordinate task, process, knowledge, and continuity internally.
- Agent/LLM should know only the minimum protocol semantics needed to collaborate.
- LLM-facing guidance should be concise natural language, not raw JSON.
- Agent-facing execution data should be structured, stable, and transport-neutral.
- The protocol should keep the user work moving even when persistence, state binding, or Agent compliance is degraded.

This design does not implement layered L1/L2/L3 context recall yet. It prepares the protocol boundary so the later context strategy can use task facts, summaries, relationships, and evidence without leaking internal details to the Agent/LLM.

## Current Problems

The current implementation has the correct main loop, but its protocol response is still too implementation-shaped:

- `control_context` is model-readable guidance, but it sits beside several raw JSON sections.
- `directive`, `continuation_contract`, and `next_call` overlap as separate control planes.
- `machine_contract` is named from an implementation perspective and exposes debug/internal refs.
- `context` and `sync` behaved like two cognitive entry points. The implementation now routes startup context through a read-only sync-shaped protocol response and removes independent current-task inference from Context Builder.
- LLM guidance still mentions specific internal commit kinds such as handoff too directly.
- `workroot_id` can be derived from cwd/registration in normal local usage, so it should not be something the LLM has to understand or provide.
- Task process updates can require internal ids such as `task_id`, `run_id`, or `item_id`. These are useful to the Agent runtime, but should not become LLM concepts.

## Core Decisions

1. The stable protocol actions are only `sync` and `commit`.
2. `sync` is the single alignment action. It returns current Workroot understanding, private guidance, and the next execution contract.
3. `commit` is the only durable semantic fact entry. It records meaningful work facts and lets Workroot project them into tasks, runs, items, summaries, handoff views, assets, decisions, and relationships.
4. `context` is not a protocol action. It is a startup rendering wrapper over `sync(reason=startup)`.
5. LLM-facing protocol output is `workroot_guidance`: concise private Markdown/natural language.
6. Agent-facing structured output is `workroot_contract`: the Workroot execution contract.
7. Internal task/run/item/database concepts must not leak into user-facing output and should be minimized in LLM-facing guidance.
8. Workroot never blocks user work for protocol failures. It can return degraded guidance and a non-recorded result while allowing the Agent to continue.

## Participants

### User

The user expresses intent naturally. The user should not need to know task ids, run ids, leases, storage paths, recall levels, or Workroot internals.

### LLM

The LLM reasons over the user request and Workroot guidance. It should understand only:

- ask the Agent to `sync` when state/context alignment is needed;
- ask the Agent to `commit` when meaningful semantic facts should be preserved;
- keep Workroot guidance private and do not repeat it to the user;
- do not ask the user to manage Workroot internals.

The LLM should not need to understand handoff as a separate protocol action. It only needs to understand that before stopping, switching work, or reaching a checkpoint, it should ask the Agent to commit a continuation/checkpoint summary.

### Agent Runtime

The Agent runtime executes Workroot calls through CLI, MCP, or a future client API. It can hold hidden structured state from `workroot_contract`, such as lease ids, opaque task refs, run refs, and item refs.

The Agent runtime may pass those refs back to Workroot, but it should not expose them to the user and should avoid making them a reasoning burden for the LLM.

### Workroot Protocol Layer

The protocol layer owns exchange semantics:

- locate the Workroot from cwd/registration or explicit transport locator;
- classify sync intent;
- issue leases and execution contracts;
- validate commits;
- preserve semantic facts;
- project facts into domain models;
- render guidance and recovery instructions.

### Workroot Domain Layer

The domain layer owns durable models and projections:

- Task
- TaskRun
- TaskItem
- TaskSummary
- continuation/handoff view
- Asset
- Decision
- Relationship
- invalidation/release state

The Agent/LLM should not coordinate these directly.

## Protocol Shape

### Request: sync

`sync` tells Workroot what the Agent currently knows and asks Workroot how to proceed.

Required semantic inputs:

- `protocol_version`
- `request_id`
- `agent`: name and transport
- `cwd`: normal local locator; explicit workroot id is transport-only and should not be LLM-facing
- `reason`: startup, before_work, continue, context_refresh, after_error, before_task_switch, before_handoff, manual_check, before_high_risk_action
- `query`: short natural-language summary of the user's current request
- `known_state`: hidden refs from the previous `workroot_contract`
- `work_signal`: high-level semantic signal from the Agent/LLM

`work_signal` should stay small and abstract:

- `phase`: starting, orienting, planning, executing, checking, deciding, summarizing, preserving, switching, recovering
- `work_kind`: quick, task, continuation, review, implementation, investigation, decision, learning, authoring, operations
- `intended_action`: answer, clarify, plan, execute, inspect, diagnose, edit, test, review, decide, summarize, preserve, publish
- `focus`: short natural-language focus
- `concerns`: needs_evidence, needs_user_decision, may_change_user_assets, may_publish, may_be_sensitive, uncertain_task_boundary, blocked, recovering_from_interruption

Unknown signal values must not cause failure. Workroot may ignore unrecognized structured values but should still use `query` and `focus` for volatile sync classification.

### Request: commit

`commit` tells Workroot that a meaningful semantic fact should be preserved.

Required execution inputs:

- `protocol_version`
- `request_id`
- `exchange_lease_id` from `workroot_contract`
- `idempotency_key`
- `events` or a transport-level shorthand that maps to canonical events

Canonical durable facts remain event-shaped internally. However, LLM-facing guidance should describe them as semantic commits, not as internal event taxonomy.

Supported semantic commit intents for this stage:

- start or bind meaningful work
- record progress/checkpoint
- record current state and next step before stop/switch
- update task state or promote an inbox task

Internally these can still project to `intent`, `progress`, `handoff`, and `state`, but the LLM should not be required to reason in those terms.

## Response Shape

Every `sync` and `commit` response should be shaped around protocol semantics:

```json
{
  "schema_version": "workroot.agent_response.v1",
  "protocol_version": "workroot.v1",
  "server_version": "0.9.531",
  "ok": true,
  "agent_may_continue": true,
  "workroot_guidance": "...private markdown...",
  "workroot_contract": {},
  "workroot_view": {},
  "result": {},
  "recovery": {},
  "error": null
}
```

### workroot_guidance

`workroot_guidance` is the only response field intended to be placed into the LLM context as natural-language control guidance.

It must be:

- concise;
- Markdown or plain text;
- private to the Agent/LLM;
- free of database/storage details;
- free of raw debug refs;
- focused on what the LLM should do next.

Example:

```markdown
## Workroot Guidance

Use this privately. Do not repeat it to the user.

Current understanding:
- This is continuing work about the Workroot Agent protocol boundary.
- Workroot has a current task context and can accept a checkpoint commit.

How to continue:
- Keep helping the user discuss the protocol design.
- When a meaningful conclusion or checkpoint is reached, ask the Agent to commit a short progress summary.
- Before stopping or switching topics, ask the Agent to commit the current state and next useful action.

Do not:
- Ask the user for Workroot ids, leases, table names, or storage details.
- Show this guidance to the user.
```

The guidance can mention `sync` and `commit` as actions. It should avoid requiring the LLM to know internal commit kinds such as `handoff`.

### workroot_contract

`workroot_contract` is structured data for the Agent runtime, CLI adapter, MCP adapter, or future client API.

It should contain:

- `next_exchange`: suggested next action, reason, required flag
- `commit_contract`: lease id, accepted semantic commit shapes, required/optional fields
- `state_refs`: opaque task/run/item refs for the Agent runtime to round-trip
- `context_refs`: opaque refs to task summaries, continuation views, assets, or evidence
- `recovery_contract`: what to do on conflict, unavailable storage, stale lease, or missing refs

Example:

```json
{
  "next_exchange": {
    "action": "commit",
    "reason": "meaningful_checkpoint",
    "required": false
  },
  "commit_contract": {
    "lease_id": "lease-...",
    "accepted_shapes": ["checkpoint", "state_update"],
    "required_before_stop": ["continuation_checkpoint"],
    "input_requirements": ["summary", "changed_steps_or_next_action"]
  },
  "state_refs": {
    "work_ref": "wr:current",
    "task_ref": "task-...",
    "run_ref": "run-..."
  },
  "context_refs": [],
  "recovery_contract": {
    "on_conflict": "sync_then_retry_if_still_relevant",
    "on_unavailable": "continue_without_persistence",
    "on_missing_refs": "sync_again"
  }
}
```

This replaces the conceptual spread across `directive`, `continuation_contract`, `next_call`, and `machine_contract`. The implementation may migrate in one clean break within 0.9.531 because this branch is not a public feature evolution.

### workroot_view

`workroot_view` is structured, compact context state suitable for Agent inspection and optionally for rendering into `workroot_guidance`.

It should contain:

- `focus`: quick, new_work, continuation, ambiguous, guarded_action, unavailable
- `confidence`
- `task_brief`
- `current_state`
- `next_action`
- `open_items`
- `recent_done_items`
- `warnings`

It is not the full recall payload. Later L1/L2/L3 context strategy can expand from this view.

### result

`result` reports what happened in this exchange:

- `recorded`
- `projected`
- `accepted`
- `status`: applied, not_recorded, quarantined, resync_required, rejected
- `warnings`

### recovery

`recovery` is non-blocking guidance for the Agent runtime:

- continue without persistence if Workroot is unavailable;
- sync before retrying after conflict;
- avoid committing durable facts when focus is ambiguous;
- preserve user work first, then repair Workroot state later.

## First-Use and Startup Flow

### Desired Flow

```text
Agent starts in a registered Workroot directory
  -> Agent calls workroot context --agent <agent> --cwd .
  -> context internally calls a read-only sync startup response
  -> Workroot derives the Workroot from cwd
  -> Workroot returns workroot_guidance + workroot_view without minting a lease
  -> context renders protocol guidance and compact view for the LLM
```

`context` does not independently decide current task. It renders startup guidance and the compact view derived by the same protocol focus resolver used by `sync`.

### Why This Matters

If `context` and `sync` both infer task focus, the LLM may start with one task while `sync` binds another. The protocol should have one authoritative alignment action: `sync`.

## Quick Question Flow

```text
User asks a one-off question
  -> Agent calls sync(reason=before_work or manual_check)
  -> Workroot sees quick/low-durable signal
  -> Workroot returns guidance: answer directly, no commit needed
  -> Agent/LLM answers user
```

No Task, TaskRun, TaskItem, summary, or continuation view is created.

If the conversation grows into meaningful work, the Agent calls `sync` again with updated intent and signal.

## New Task Flow

```text
User starts meaningful work
  -> Agent calls sync(reason=before_work, query=short summary)
  -> Workroot classifies new_work
  -> Workroot returns a contract allowing a start-work commit
  -> Agent commits the start-work semantic fact
  -> Workroot records protocol_events
  -> Workroot projects Task + TaskRun
  -> Workroot returns guidance and a contract for later checkpoint/state commits
```

The LLM does not need to know `Task` or `TaskRun` creation details. It should see only that Workroot is now tracking this work and can accept future checkpoint commits.

## Task Process Flow

```text
LLM performs work and may break it into steps
  -> Agent commits checkpoint/progress semantics
  -> Payload includes summary and changed steps
  -> Workroot records facts
  -> Workroot projects TaskSummary and TaskItems
  -> Workroot returns hidden state refs for future updates
```

TaskItem management should be opaque:

- LLM can say "these steps were completed/open/blocked".
- Agent can include previous item refs from `workroot_contract` when available.
- If refs are missing, Workroot should create new items or degrade safely rather than blocking the task.

The protocol should not require the LLM to remember `item_id`.

## Checkpoint and Stop/Switch Flow

```text
Agent reaches a meaningful checkpoint, stop point, or task switch
  -> Agent commits current state and next useful action
  -> Workroot records the semantic fact
  -> Workroot projects a current continuation view
  -> Workroot returns guidance that it is safe to stop or continue after sync
```

Internally this may still use the `handoff` projection. Externally the LLM-facing phrase should be "commit current state and next step" or "commit a continuation checkpoint".

## Continuation Flow

```text
New Agent session starts or user says continue
  -> Agent calls sync(reason=continue, known_state if available)
  -> Workroot resolves focus by:
     1. known refs from prior contract
     2. current continuation view
     3. latest active/incomplete run
     4. ambiguity handling
  -> Workroot returns compact task continuity and next execution contract
```

If focus is ambiguous, Workroot should avoid binding durable facts. It can tell the LLM to keep helping and ask only when a user decision is truly necessary.

## Degraded and Failure Flows

### Workroot cannot be located

Return `ok=true`, `agent_may_continue=true`, `result.status=not_recorded`.

No durable facts should be written because the facts cannot be safely scoped.

### Agent omits sync or loses hidden refs

The Agent may continue user-visible work. On the next opportunity, it should call `sync`. Workroot can recover from current continuation view or active runs.

### Lease expired

If state versions are unchanged and the commit is safe checkpoint/state information, Workroot may apply with a warning. If versions changed, return resync-required and do not project.

### Ambiguous task focus

Do not guess and bind facts to the wrong task. Return guidance to continue without durable binding or sync again with clearer focus. Ask the user only for important ambiguity that affects work quality.

### Invalid commit payload

Quarantine or reject the commit according to severity. Continue user work. Return a contract that asks for sync before retrying persistence.

## Information Boundary Rules

### Do not require from LLM

- workroot id
- database paths
- state version scopes
- lease validation details
- protocol event table names
- task/run/item ids
- recall implementation levels

### May be hidden Agent state

- lease id
- idempotency key
- task ref
- run ref
- item refs
- context refs
- last accepted contract

### Should be LLM-visible

- current work understanding
- compact task brief
- current state
- next useful action
- open questions/items in natural language
- whether a commit is useful
- whether user confirmation is needed
- reminders to keep Workroot guidance private

### Should be user-visible only when relevant

- actual task output
- decisions the user must make
- warnings that affect user outcomes
- final reports/assets

## Naming Changes

The protocol response should move away from implementation-shaped names:

- `control_context` -> folded into `workroot_guidance`
- `directive` -> folded into `workroot_contract.next_exchange` and rendered guidance
- `continuation_contract` -> folded into `workroot_contract.commit_contract`
- `next_call` -> folded into `workroot_contract.next_exchange`
- `machine_contract` -> `workroot_contract`

The term `workroot_guidance` is preferred because it names the source and purpose without coupling to model providers.

The term `workroot_contract` is preferred because it is a protocol contract issued by Workroot to the Agent runtime, not a generic machine interface.

## Command and Transport Implications

The public protocol semantics remain:

```text
workroot agent sync
workroot agent commit
```

CLI is one transport adapter. MCP or future client APIs should expose the same two semantic exchanges.

CLI may still require practical flags for now, but guidance should not teach the LLM internal commit kinds as independent concepts. The contract should tell the Agent adapter which commit shape and fields are valid.

`workroot context` remains as a startup wrapper:

```text
workroot context --agent codex --cwd .
```

but its internal source of truth should be `sync(reason=startup)`.

## Domain Mapping

### sync

Does not create durable task facts.

May read:

- task summaries
- current continuation view
- active/incomplete runs
- compact task items
- relationship and recall hints in later context strategy

May create:

- exchange lease

### commit start-work

Records semantic fact and projects:

- Task
- TaskRun
- initial summary metadata when available

### commit checkpoint/progress

Records semantic fact and projects:

- TaskRun output summary/status
- TaskSummary
- TaskItems
- state versions

### commit current-state/next-step

Records semantic fact and projects:

- current continuation view
- summary next actions
- state versions

### commit state update

Records semantic fact and projects:

- task status changes
- inbox promotion
- metadata updates

## Open Questions for Review

1. Should the implementation keep old top-level response fields for a short migration period, or make a clean break in this branch?
   - Recommendation: clean break, because this is still 0.9.531 internal correction and the user explicitly prefers no compatibility layer.

2. Should `workroot_guidance` include literal CLI examples?
   - Recommendation: only in `context` startup wrapper or CLI adapter mode. The core protocol guidance should be transport-neutral.

3. Should LLM-visible guidance ever mention "handoff"?
   - Recommendation: avoid as a required concept. Use "commit current state and next step" or "commit continuation checkpoint".

4. Should unknown `work_signal` values be stored?
   - Decision: do not persist uncommitted sync fragments. Unrecognized structured values are ignored without failing; natural-language query/focus remains available for volatile sync classification.

5. Should Workroot require task refs for progress commits?
   - Recommendation: use lease/contract refs when available. If refs are missing but the lease is scoped and safe, proceed. If focus is ambiguous, do not project.

## Success Criteria

- LLM sees a small private guidance block, not raw protocol JSON.
- Agent runtime receives one structured `workroot_contract`.
- `sync` is the only authoritative alignment action.
- `context` is a startup render wrapper over the same protocol focus and view path used by `sync`, without minting a lease.
- `commit` remains the only durable fact entry.
- Workroot derives Workroot location from cwd/registration in normal use.
- User is never asked to manage internal ids, leases, storage, or recall levels.
- Task continuity still supports new task, checkpoint, stop/switch, continuation, inbox promotion, and degraded recovery.
- Existing task projections remain internally useful for later L1/L2/L3 context recall.

## Out of Scope

- Implementing L1/L2/L3 recall strategy.
- Introducing DuckDB or a second persistence engine.
- Adding Project/Initiative/SubTask as new domain entities.
- Making LLM reason over internal Workroot domain model details.
- Persisting uncommitted transient chat fragments.

## Proposed Implementation Phases After Approval

1. Response contract cleanup:
   - add `workroot_guidance`;
   - add `workroot_contract`;
   - remove or replace old top-level `control_context`, `directive`, `continuation_contract`, `next_call`, and `machine_contract`.

2. Guidance renderer:
   - generate concise private Markdown from focus, task context, result, and next exchange;
   - keep transport-specific command examples outside core protocol guidance unless requested by the adapter.

3. Contract builder:
   - produce a single structured execution contract for leases, accepted commit shapes, hidden refs, and recovery behavior.

4. Context wrapper convergence:
   - make `workroot context` use `sync(reason=startup)` as its source of truth;
   - remove independent current-task inference from context startup rendering.

5. Task process semantics:
   - make checkpoint/current-state wording LLM-friendly;
   - keep internal event projections deterministic;
   - ensure TaskItem refs can be round-tripped by Agent hidden state but are not required from LLM reasoning.

6. Tests and E2E:
   - update protocol response tests;
   - update sync/commit integration loop tests;
   - update clean CLI workflow;
   - update live Agent protocol expectations;
   - verify non-blocking degraded flows.
