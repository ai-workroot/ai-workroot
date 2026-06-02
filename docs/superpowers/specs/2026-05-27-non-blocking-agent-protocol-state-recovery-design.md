# Non-blocking Agent Protocol, Work Signal, and State Recovery Design

Status: approved detailed design for implementation
Target version: 0.9.531 follow-up
Date: 2026-05-27
Branch: `feat/0.9.531-agent-protocol-task-continuity`

## Purpose

This document refines the Workroot Agent Protocol beyond the minimal P0 loop. The goal is to make Workroot a durable continuity layer that can cooperate with unreliable agent and model runtimes without blocking the user.

The key shift is:

```text
Workroot is correctness-oriented for its stored facts,
but non-blocking for the Agent's user work.
```

Workroot should help the Agent preserve intent, progress, state, and handoff when practical. If protocol information is missing, stale, swallowed by the Agent adapter, or not understood by the remote model, Workroot should degrade and recover later rather than interrupt the user's work.

## Design Goals

1. Let the Agent keep serving the user in all ordinary cases.
2. Keep the protocol loop self-sustaining across model turns.
3. Keep Agent-facing semantics abstract and stable across Codex, Claude Code, ChatGPT, MCP, and future clients.
4. Avoid exposing internal retrieval depth, storage details, or ContextStrategy mechanics to the model.
5. Separate Workroot control guidance from task context so protocol text does not pollute user-facing work.
6. Treat incomplete, partial, missing, stale, or interrupted state as normal recoverable conditions.
7. Reuse existing fact/domain tables; do not add new persistent domain models for this step.

## Non-goals

1. Do not implement L1/L2/L3 progressive context disclosure in this design.
2. Do not add Project, Initiative, SubTask, TemporaryTask, or Inbox domain entities.
3. Do not require the Agent to know Workroot internal recall, disclosure, budget, or safety strategies.
4. Do not block user work just because Workroot protocol state is incomplete.
5. Do not define the final set of user-facing interruption prompts here. Keep a small future extension point.

## Settled Decisions

The following decisions are part of this design:

1. If Workroot cannot be located, do not write persistent data. Return `not_recorded` with `agent_may_continue=true`.
2. Degraded commit may write only after Workroot is strongly or weakly located.
3. Malformed events are persisted as `invalid` or `quarantined` only when they are minimally identifiable and a Workroot is located.
4. `task_runs.completed` does not require a handoff. Handoff affects continuity quality, not completion.
5. Stale state is derived at runtime, not persisted as a primary status.
6. Default stale derivation starts with 6 hours for active runs without progress/handoff and 7 days for incomplete run recall downgrade.
7. `context` command output should include a short isolated Control Context because existing Agent entries already call `workroot context`.
8. `work_signal` is optional and is never a fact source. It is a strategy input only.
9. `invalid` and `quarantined` protocol events never enter ordinary context recall.

## Current Baseline

The current 0.9.531 branch already has the protocol foundation:

- `sync` and `commit` actions.
- `directive + lease + context + contract` response shape.
- `sync` does not create semantic task facts.
- `commit` appends `protocol_events` and applies deterministic projections.
- `commit(intent)` creates or attaches `Task` and `TaskRun`.
- `commit(progress)` creates task summaries and task items.
- `commit(handoff)` creates the current handoff view.
- `sync(continue)` can load task summary, handoff, open task items, and recent done items.

The missing pieces are:

- model-readable per-turn protocol guidance;
- abstract high-level work semantics from the Agent/model;
- non-blocking degraded commit behavior;
- first-class incomplete and recovery semantics;
- status-aware context validity;
- clear separation between control context and task context.

## Core Principles

### 1. Non-blocking by default

Workroot should never stop the Agent from helping the user in ordinary cases.

Workroot may:

- decline to store untrusted facts;
- quarantine an event;
- mark a run incomplete;
- lower context confidence;
- ask the Agent to resync later;
- return warnings.

Workroot should not:

- block the Agent's answer;
- force the Agent into a repair loop before user work continues;
- require a perfect handoff before the user can move on;
- expose internal protocol failure details as user-facing noise.

Every ordinary response should include:

```json
"agent_may_continue": true
```

### 2. Strict only for stored fact integrity

Workroot can be strict about what it records as durable fact. If an event is incomplete or unsafe, it should not be projected into canonical facts.

Strictness applies to storage integrity, not to user workflow.

### 3. Boot helps, but correctness cannot depend on Boot memory

The remote model may not remember the Boot contract. The Agent adapter may not pass the Boot contract. Therefore every Workroot output that is intended to drive ongoing agent behavior must be self-continuing.

Each turn should include a short model-facing protocol capsule.

### 4. Agent-facing protocol is work semantics, not retrieval mechanics

The model should communicate high-level work semantics:

- where it is in the work;
- what kind of work it is doing;
- what action it intends next;
- what the current focus is;
- whether there are material concerns.

The model should not communicate:

- L1/L2/L3;
- recall source names;
- budget allocation;
- storage paths;
- relationship traversal depth;
- internal strategy decisions.

### 5. Control context must not contaminate task context

Workroot output should separate:

```text
Control Context: tells the model how and when to call Workroot.
Task Context: helps the model do the user's work.
```

The control section should be short, stable, and explicitly marked as not user-facing.

## Participants

### Remote model

The model reasons over the user's request and the Workroot context package. It may generate tool calls through the host Agent.

The model should receive concise natural-language control guidance each turn.

### Agent adapter

The Agent adapter exposes Workroot tools to the model. It may be CLI, MCP, SDK, or a native integration.

The adapter should pass Workroot control context to the model, but Workroot must tolerate cases where it does not.

### Workroot protocol controller

The controller accepts `sync` and `commit`, validates machine contracts, appends protocol events, and applies projections when safe.

### Workroot context system

The context system turns stored facts, summaries, handoffs, task items, indexes, release state, and relationship signals into task context.

This design does not implement the later ContextStrategy depth model, but prepares state semantics that ContextStrategy can use.

## Protocol Surfaces

### Actions

The externally visible action set remains small:

```text
sync
commit
```

Future MCP/client surfaces may expose them as:

```text
workroot.sync
workroot.commit
```

The model should not learn many low-level Workroot commands.

### Sync

`sync` is used when the Agent needs context, continuity, recovery guidance, or the next Workroot call instruction.

`sync` should accept optional high-level work semantics.

`sync` should not create semantic facts.

### Commit

`commit` is used when the Agent has something useful to preserve:

- intent;
- progress;
- task items;
- decision;
- asset metadata;
- state transition;
- handoff;
- correction.

`commit` should be best-effort and non-blocking from the user's perspective.

## Work Signal

`work_signal` is the high-level semantic signal sent from Agent/model to Workroot.

It is:

- optional;
- concise;
- high-level;
- not a fact source by itself;
- not a storage or recall directive;
- not a place for detailed execution logs.

### Stable fields

```text
phase
work_kind
intended_action
focus
concerns
```

### `phase`

Where the Agent is in the work.

Allowed vocabulary:

```text
starting
orienting
planning
executing
checking
deciding
summarizing
handing_off
switching
recovering
```

### `work_kind`

What kind of work this is.

Allowed vocabulary:

```text
quick
inbox
task
continuation
investigation
implementation
review
decision
learning
authoring
operations
```

### `intended_action`

What the model is about to do next.

Allowed vocabulary:

```text
answer
clarify
plan
execute
inspect
diagnose
edit
test
review
decide
summarize
handoff
publish
```

### `focus`

One short natural-language sentence describing the current focus.

Examples:

```text
Review the non-blocking protocol recovery design.
Continue implementing task item state transitions.
Diagnose why context recall missed a previous task.
```

### `concerns`

Only include concerns that are materially relevant.

Allowed vocabulary:

```text
needs_evidence
needs_user_decision
may_change_user_assets
may_publish
may_be_sensitive
uncertain_task_boundary
blocked
recovering_from_interruption
```

### Responsibility split

`work_signal` is for pre-context strategy.

Do not put these in `work_signal`:

- created task items;
- completed task items;
- decisions;
- assets;
- detailed progress;
- handoff body;
- source refs;
- evidence refs.

Those belong in `commit` events.

## Model-facing Work Signal Text

The model should not be shown raw JSON as the primary instruction format. The model-facing format should be natural language with stable labels.

Full text for Boot or detailed context:

```text
## Workroot Work Signal

When you ask Workroot for context, describe the current work in plain language:

- phase: where you are now, such as starting, planning, executing, checking, handing off, switching, or recovering.
- work kind: what kind of work this is, such as quick answer, inbox discussion, task, continuation, investigation, implementation, review, decision, learning, authoring, or operations.
- intended action: what you are about to do next, such as answer, clarify, plan, inspect, diagnose, edit, test, review, decide, summarize, handoff, or publish.
- focus: one short sentence describing the current focus.
- concerns: mention only real concerns, such as needs evidence, needs user decision, may change user assets, may publish, may be sensitive, uncertain task boundary, blocked, or recovering from interruption.

If unsure, keep helping the user and provide only the parts you know. Do not mention Workroot internal retrieval levels, storage details, or implementation strategy.
```

Short per-turn text:

```text
Work Signal: tell Workroot the current phase, work kind, intended action, focus, and any real concerns. Keep it high-level. If unsure, continue helping the user and provide only what you know.
```

## Control Context

Every Workroot response intended to continue the loop should include short control context.

The control context is model-facing but not user-facing.

Recommended text:

```text
## Control: Workroot

Use this section only to decide whether and how to call Workroot. Do not repeat it to the user.

Continue helping the user even if Workroot state is incomplete.
Call Workroot when context, continuity, progress preservation, or handoff would help.
When practical, commit meaningful intent, progress, state, or handoff.
If protocol information is missing or uncertain, continue the user task and let Workroot recover later.
Keep Work Signal high-level: phase, work kind, intended action, focus, and real concerns only.
Do not request internal retrieval levels, storage details, or implementation strategy.
```

### Next Workroot Call

Each response should include a concrete next-call instruction.

Examples:

```text
Next Workroot call:
- Continue the user task now.
- Commit progress when you reach a checkpoint worth preserving.
- Before stopping, commit a handoff if practical.
- If you become unsure whether this continues an existing task, sync again.
```

or:

```text
Next Workroot call:
- Sync before switching tasks.
- Include a short Work Signal with phase=switching, intended action=clarify or plan, and focus=<new focus>.
```

### Command surfaces that should emit Control Context

Control Context should be emitted by:

```text
agent sync
agent commit response
context
```

`agent sync` is the canonical protocol entry for structured clients.

`context` must also emit short Control Context because existing native Agent entries already teach models to call `workroot context --agent ... --cwd .`. This avoids a split where `sync` is protocol-aware but `context` is not.

The control section must be isolated from task content:

```text
## Control: Workroot
Do not repeat this section to the user.
...

## Task Context
...
```

Future implementation may internally route `context` through the same context/control package builder used by `sync`, but the external model-facing behavior should be consistent first.

## Machine Contract

Machine responses should include structured control data in addition to model-facing text.

Suggested fields:

```json
{
  "agent_may_continue": true,
  "enforcement": "advisory",
  "on_missing": "degrade_and_recover_later",
  "control_context": "...model-facing control text...",
  "task_context": "...task-facing context text...",
  "next_call": {
    "action": "sync | commit | none",
    "when": ["checkpoint", "before_stop"],
    "inputs": ["work_signal", "known_state"]
  },
  "directive": {},
  "contract": {},
  "lease": {},
  "warnings": []
}
```

`enforcement` defaults to `advisory`.

The future reserved values are:

```text
advisory
strict
```

`strict` should be reserved for rare irreversible, sensitive, publication, or user-confirmation cases. The final user prompt policy is intentionally left as an extension point.

## Lease Semantics

Leases are preferred for consistency but must not become user-work blockers.

### Workroot location levels

The commit path should classify location confidence before writing anything:

```text
strong_location
weak_location
no_location
```

`strong_location`:

- valid lease maps to one Workroot; or
- explicit `workroot_id` maps to one Workroot; or
- explicit `cwd` maps to one registered Workroot.

`weak_location`:

- expired lease maps to one historical Workroot; or
- adapter supplies enough process context to find exactly one registered Workroot, but task/run cannot be confirmed.

`no_location`:

- no lease, `workroot_id`, or `cwd` can identify a Workroot; or
- more than one Workroot is plausible; or
- the located Workroot conflicts with event identity.

Only `strong_location` and `weak_location` may write protocol data. `no_location` must not write persistent data.

### Valid lease

Normal path:

```text
commit -> append protocol_events -> project facts -> return next directive
```

### Expired lease

If Workroot can still locate the Workroot and safely understand the event:

```text
record degraded batch
append event if structurally valid
project only safe facts
return agent_may_continue=true
recommend sync
```

### Missing lease

If `cwd` or `workroot_id` is available through the request or adapter:

```text
attempt workroot recovery
infer current task/run only when confidence is high
otherwise quarantine or ignore non-projectable facts
return agent_may_continue=true
```

If Workroot cannot locate the Workroot:

```text
do not write facts
do not write orphan protocol events
do not create a global fallback event pool
return not_recorded
return agent_may_continue=true
```

## Commit Degradation

Current P0 treats many validation failures as request-level failures. This design changes the target behavior:

```text
bad event should not necessarily poison the whole batch.
```

A batch can be:

```text
completed
degraded
partial
not_recorded
idempotency_conflict
```

An event can be:

```text
received
applied
partially_applied
quarantined
ignored
superseded
invalid
```

### Event status definitions

`received`:
The event was accepted structurally but has not been projected yet.

`applied`:
The event was projected into durable domain facts.

`partially_applied`:
Some safe facts were projected, while unsafe or incomplete parts were skipped.

`quarantined`:
The event was recorded for audit/recovery but did not affect canonical facts.

`ignored`:
The event was intentionally not persisted or not used because it was too incomplete or not useful.

`superseded`:
The event has been replaced by a later event.

`invalid`:
The event failed structural or semantic validation and is not a fact.

### Minimal event identifiability

A malformed event can be persisted for protocol audit only when all of these are true:

```text
Workroot is strongly or weakly located.
event_id exists and is non-empty.
kind exists and is non-empty.
payload is an object, even if semantically invalid.
```

If these conditions are not met, the event should not be written to `protocol_events`. The response may include a batch warning, but Workroot should not create durable noise.

### Event handling matrix

```text
Valid event + valid lease
  -> protocol_events.status=applied
  -> project canonical facts
  -> batch.status=completed

Valid event + expired lease + strong/weak Workroot location
  -> protocol_events.status=applied or partially_applied
  -> project only safe facts
  -> batch.status=degraded

Minimally identifiable malformed event + located Workroot
  -> protocol_events.status=invalid or quarantined
  -> do not project facts
  -> batch.status=partial or degraded

Unidentifiable malformed event + located Workroot
  -> do not write protocol_events
  -> batch.status=partial or degraded
  -> response warning only

Any event + no Workroot location
  -> do not write protocol_events
  -> batch.status=not_recorded if a response object is produced
  -> agent_may_continue=true
```

### Context recall exclusion

These event states must not enter ordinary context recall:

```text
invalid
quarantined
ignored
```

They may be visible only to diagnostics, debug traces, or explicit repair flows.

## State Model

No new persistent domain models are required for this design. Existing tables should gain clearer status semantics.

### `tasks`

`tasks` are durable work containers. They should not be frequently moved to error states because one Agent run was interrupted.

Existing task states can remain focused on durable lifecycle:

```text
active
paused
blocked
closed
archived
released
```

### `task_runs`

`task_runs` represent a specific Agent execution attempt for a task.

Recommended statuses:

```text
active
completed
incomplete
abandoned
recovered
```

`active`:
The Agent is currently or recently working.

`completed`:
The run produced a sufficient progress summary, task state update, or useful result. A handoff is not required.

`incomplete`:
The run stopped without enough summary or handoff.

`abandoned`:
The run should not be used as current continuity except for historical trace.

`recovered`:
A later sync/commit recovered enough continuity from this run.

Do not persist `stale` as a primary state. Compute stale at runtime from age and missing handoff/summary.

Initial derived thresholds:

```text
active run older than 6 hours with no progress summary or handoff
  -> stale_active_run

incomplete run older than 7 days
  -> old_incomplete_run
```

These thresholds should be configuration-ready but can start as constants. They affect recall priority and recovery guidance only. They should not mutate `task_runs.status` by themselves.

### `handoffs`

Recommended statuses:

```text
current
superseded
incomplete
```

`current`:
The active handoff for continuing the task.

`superseded`:
Replaced by a newer handoff.

`incomplete`:
Best-effort handoff with insufficient detail.

Missing handoff is not an error. It lowers continuity confidence.

### Completion and handoff

Completion and handoff are related but separate:

```text
completed run
  means this execution produced a useful result or summary.

current handoff
  means future continuation has a high-quality transfer view.
```

A run can be `completed` without a handoff. In that case, future context may mark continuity as degraded, but the run result remains valid.

A run should be `incomplete` when it has neither:

- sufficient progress summary;
- useful task item result;
- meaningful state transition;
- handoff.

### `exchange_leases`

Lease status can remain operational. Expired or missing lease should trigger recovery guidance, not user-work blocking.

## Recovery Semantics

Recovery should be lazy and triggered by `sync` or context build, not by mandatory background jobs.

### Recovery detection

On `sync`, Workroot should inspect:

- latest active task;
- latest active or incomplete task run;
- latest current handoff;
- latest task summary;
- open task items;
- stale lease conditions;
- protocol events that were partial or quarantined.

### Recovery response

If recovery is needed, Workroot returns:

```json
{
  "directive": {
    "type": "recover_or_continue",
    "next_action": "Continue if this is the same work, or commit a handoff/progress summary when practical."
  },
  "agent_may_continue": true,
  "continuity_status": "degraded",
  "warnings": ["previous run has no current handoff"]
}
```

The model-facing control context should say:

```text
Workroot found incomplete continuity. Continue helping the user. If practical, preserve a short progress summary or handoff later.
```

## Context Validity and State-aware Recall

Future ContextStrategy should treat state as part of context validity.

The following validity priority should guide recall:

```text
current handoff / current summary
active task / open task items
recent completed items
incomplete run recovery clues
stale active run clues
abandoned run historical index
superseded state only for history
invalidated/redacted/deleted governed state
```

### Suggested behavior

`current summary`:
High-priority context.

`current handoff`:
High-priority continuity view.

`active run`:
Useful context. If stale, label or trace uncertainty.

`incomplete run`:
Use as recovery clue, not as stable conclusion.

`abandoned run`:
Default to low-priority index metadata only.

`superseded summary/handoff`:
Exclude from ordinary context unless history is requested.

`invalidated record`:
Do not present as current truth.

`redacted/deleted`:
Do not expand. Use placeholders or omit according to Release Control.

`tombstone`:
May appear as symbolic stale-truth marker, never as current truth.

## User Prompt Policy Extension Point

This design intentionally does not finalize user prompt conditions.

Default behavior:

```text
do not interrupt the user.
```

Reserved future prompt cases:

- irreversible user asset deletion or overwrite;
- external publication or release;
- sensitive data exposure;
- explicit user decision required;
- Workroot cannot safely determine action boundaries.

These cases should remain rare and explicit.

## Scenario Walkthroughs

### Scenario 1: Quick answer

User asks a small question.

Agent calls `sync` with:

```text
phase=starting
work_kind=quick
intended_action=answer
focus=<question>
```

Workroot:

- returns minimal control context;
- returns little or no task context;
- does not require task creation;
- returns `agent_may_continue=true`.

Agent answers user. No commit is required.

Closed-loop result:

```text
User work is not blocked. No unnecessary task is created.
```

### Scenario 2: New tracked task

User asks for meaningful work.

Agent calls `sync` with:

```text
phase=starting
work_kind=task
intended_action=plan
focus=<task focus>
```

Workroot:

- returns context if related history exists;
- returns directive recommending `commit(intent)` if tracked work should begin;
- returns concise next call guidance.

Agent may start helping immediately. When practical, Agent commits intent.

Closed-loop result:

```text
Task tracking is encouraged but not user-blocking.
```

### Scenario 3: Continue current task with good state

Agent knows `task_id` and `run_id`.

Agent calls `sync` with:

```text
phase=continuing
work_kind=continuation
intended_action=execute
focus=<current step>
known_state={task_id, run_id}
```

Workroot:

- loads task summary;
- loads current handoff;
- loads open and recently done task items;
- returns `continue_task` directive.

Closed-loop result:

```text
Continuity is strong and low-noise.
```

### Scenario 4: Agent misses `work_signal`

Agent calls `sync` with only query/reason.

Workroot:

- infers from `reason`, `query`, and `known_state`;
- returns context with lower confidence if needed;
- includes Work Signal capsule again;
- does not block.

Closed-loop result:

```text
Context quality may degrade, but user work continues.
```

### Scenario 5: Agent adapter does not pass capsule to the remote model

The model does not know the protocol guidance.

Likely outcomes:

- no commit happens;
- commit lacks work signal;
- handoff is missing.

Workroot:

- does not block;
- marks run incomplete when detected;
- next sync returns recovery guidance and capsule again.

Closed-loop result:

```text
Protocol loop degrades and later recovers.
```

### Scenario 6: Expired lease during commit

Agent has meaningful progress but the lease expired.

Workroot:

- accepts the request as degraded if Workroot and task can be located;
- appends structurally valid event if safe;
- projects safe progress;
- returns `agent_may_continue=true`;
- returns next sync guidance.

Closed-loop result:

```text
Useful facts are preserved when safe. Expired lease is not fatal.
```

### Scenario 7: Partial progress commit

Agent sends progress summary but task item updates are malformed.

Workroot:

- stores the summary if valid;
- skips or quarantines malformed item updates;
- marks event `partially_applied`;
- returns warnings for Agent, not user-facing interruption.

Closed-loop result:

```text
Continuity improves even though some details are missing.
```

### Scenario 8: Agent stops without handoff

Agent never commits handoff.

Workroot:

- later sees active run without current handoff;
- derives stale/incomplete condition;
- next sync returns degraded continuity and asks for recovery when practical.

Closed-loop result:

```text
Missing handoff lowers continuity quality but does not break the task.
```

### Scenario 9: Long stale active run

A run remains active for a long time.

Workroot:

- derives staleness at sync/context time;
- does not necessarily mutate task state immediately;
- recalls last summary and open items with lower confidence;
- recommends `recover_or_continue`.

Closed-loop result:

```text
Old state remains useful as a clue, not as current truth.
```

### Scenario 10: Task switching

User changes topic.

Agent calls `sync` with:

```text
phase=switching
work_kind=task
intended_action=clarify or plan
focus=<new focus>
concerns=uncertain_task_boundary
```

Workroot:

- returns possible related tasks if found;
- does not force a decision;
- lets Agent continue;
- suggests committing intent or handoff when practical.

Closed-loop result:

```text
Task boundary uncertainty becomes recoverable context, not a hard fork decision.
```

### Scenario 11: Agent decomposes work into steps

Agent receives a larger implementation task.

Correct flow:

```text
sync(work_signal: planning/executing)
Agent decomposes steps
commit(progress: items_created=[...])
```

Workroot:

- does not expect step details in `work_signal`;
- stores steps through task item projection;
- later recalls open and recently completed items.

Closed-loop result:

```text
Work Signal stays abstract. Task items remain durable process facts.
```

### Scenario 12: High-risk publish or external release

Agent intends to publish or release.

Agent calls `sync` with:

```text
intended_action=publish
concerns=may_publish, may_be_sensitive
```

Workroot:

- applies stricter safety strategy internally;
- may return advisory warnings;
- reserves the right to require user confirmation in future policy;
- still avoids blocking ordinary user work by default.

Closed-loop result:

```text
The prompt policy hook exists, but ordinary protocol flow remains non-blocking.
```

## Design Coverage Assessment

This draft covers:

- model-readable protocol guidance;
- stable high-level Work Signal;
- non-blocking sync/commit;
- lease degradation;
- partial commit;
- task run intermediate states;
- handoff missing state;
- recovery on next sync;
- state-aware context validity;
- separation of control context and task context;
- future prompt-policy extension point.

This draft intentionally defers:

- exact ContextStrategy L1/L2/L3 depth implementation;
- final user interruption policy;
- exact degraded commit projection rules per event kind;
- final CLI/MCP rendering formats.

## Implementation Decisions

1. Degraded commit requires a located Workroot. If Workroot cannot be located, Workroot must not write persistent protocol or domain data.
2. Expired lease can identify Workroot only when it maps to exactly one historical Workroot and does not conflict with explicit `cwd` or `workroot_id`.
3. Malformed events are stored as `invalid` or `quarantined` only when minimally identifiable and Workroot is located.
4. Unidentifiable malformed events produce response warnings but are not written to `protocol_events`.
5. `task_runs.completed` does not require handoff. Handoff controls continuity quality, not result completion.
6. `stale` is runtime-derived. It is not a persisted `task_runs.status`.
7. Initial stale thresholds are 6 hours for active runs with no progress/handoff and 7 days for incomplete run recall downgrade.
8. `context` command should emit short isolated Control Context in addition to `agent sync`.
9. `invalid`, `quarantined`, and `ignored` events are excluded from ordinary context recall.

## Detailed Implementation Spec

### External protocol compatibility

The only stable external protocol actions are:

```text
sync
commit
```

`sync` may be surfaced through CLI, MCP, SDK, or native adapters, but those adapters must all carry the same semantic contract:

```text
Agent/model asks Workroot for continuity and next-call guidance.
Workroot returns advisory control context, task context, directive, lease, and contract.
No durable task fact is created by sync.
```

`commit` carries durable semantic events:

```text
intent
progress
handoff
state
decision
asset
correction
guidance
```

Only implemented event kinds are projected. Unsupported but structurally valid event kinds remain protocol events only if safe to persist; they do not become canonical task facts.

### Sync response contract

Every successful `sync` response must include:

```json
{
  "ok": true,
  "agent_may_continue": true,
  "enforcement": "advisory",
  "on_missing": "degrade_and_recover_later",
  "control_context": "...",
  "task_context": {},
  "context": {},
  "next_call": {},
  "directive": {},
  "lease": {},
  "contract": {},
  "warnings": []
}
```

`context` is kept for the existing P0 contract. `task_context` is an alias to the same semantic task package so new clients can separate it from `control_context`.

### Error response contract

Ordinary protocol errors are advisory and non-blocking:

```json
{
  "ok": false,
  "agent_may_continue": true,
  "enforcement": "advisory",
  "on_missing": "degrade_and_recover_later",
  "control_context": "...",
  "next_call": {
    "action": "sync",
    "when": ["if continuing this work is still useful"],
    "inputs": ["work_signal", "known_state"]
  }
}
```

This does not make invalid data acceptable. It means the Agent should continue helping the user and let Workroot recover later.

### Work Signal contract

`work_signal` is accepted on `sync` and command adapters. It is runtime-only:

```json
{
  "phase": "executing",
  "work_kind": "implementation",
  "intended_action": "edit",
  "focus": "Implement non-blocking protocol state recovery.",
  "concerns": ["may_change_user_assets"]
}
```

Unknown vocabulary values are dropped, not rejected. Missing `work_signal` is equivalent to an empty signal. Workroot does not persist `work_signal` as a protocol event, task fact, context candidate, or recall hint.

### Commit location contract

Before writing, `commit` derives one location confidence:

```text
strong_location
weak_location
no_location
```

`no_location` is a hard storage boundary:

```text
no protocol_commit_batches row
no protocol_events row
no domain projections
response.batch_status=not_recorded
response.agent_may_continue=true
```

`strong_location` and `weak_location` may write protocol data. Weak location can degrade projection confidence, but it must not create orphan facts.

### Commit idempotency contract

Idempotency remains batch-scoped:

```text
same workroot_id + same idempotency_key + same request_hash
  -> return original response_json

same workroot_id + same idempotency_key + different request_hash
  -> return idempotency_key_conflict
```

`not_recorded` no-location commits do not write a batch row because they cannot be assigned to a Workroot.

### Commit status contract

Batch status values:

```text
completed
degraded
partial
not_recorded
idempotency_conflict
```

Event status values:

```text
received
applied
partially_applied
quarantined
ignored
superseded
invalid
```

Only `applied` and `partially_applied` may create or update canonical domain facts. `quarantined`, `invalid`, and `ignored` never enter ordinary context recall.

### Projection tolerance contract

Projection tolerance is event-kind specific:

```text
intent:
  task/run creation stays strict because bad intent can create durable wrong work boundaries.

progress:
  valid task/run identity and summary may be preserved even if individual item updates are invalid.
  invalid item updates are skipped or quarantined; they must not delete a valid summary.

handoff:
  handoff creation stays strict enough to avoid corrupting the current handoff view.

state:
  task lifecycle transitions stay strict because they change durable task truth.
```

### Task run and handoff contract

`task_runs.completed` means the run produced a useful result or summary. It does not require a handoff.

Missing handoff changes continuity quality:

```text
completed run + no current handoff
  -> valid run result
  -> sync/context warning that continuity may be degraded
```

Derived stale states are runtime-only and must not mutate `task_runs.status`:

```text
active run older than 6h with no summary/handoff -> stale_active_run
incomplete run older than 7d -> old_incomplete_run
```

### Context command contract

`workroot context` emits two isolated sections:

```text
## Control: Workroot
...

## Task Context
...
```

Control text is model-facing and explicitly not user-facing. It must remain short enough to be included every turn without dominating task context.

### Dependency contract

The implementation must preserve package boundaries:

```text
cli -> commands
commands -> protocol/context/state
protocol -> context/state
context -> relationships/release/retrieval/state
state -> no higher-level package
```

No compatibility layer, legacy namespace, or new domain model bucket is allowed.

## Test Case Matrix

The implementation must include tests for:

```text
sync response includes agent_may_continue=true
sync response includes model-facing Control Context
context output includes isolated Control Context before Task Context
context output marks Control Context as not user-facing
work_signal is optional
missing work_signal degrades without failing sync
work_signal does not create protocol_events or task facts
commit with no located Workroot returns not_recorded and writes nothing
commit with expired lease and located Workroot can degrade
commit with expired lease and conflicting cwd/workroot_id does not write
minimally identifiable malformed event becomes invalid/quarantined
unidentifiable malformed event is not written
partial batch applies safe progress and quarantines unsafe event
completed run does not require handoff
missing handoff yields degraded continuity on next sync
active run older than 6 hours derives stale_active_run
incomplete run older than 7 days is downgraded for recall
invalid/quarantined/ignored protocol events are absent from ordinary context
diagnostics can see invalid/quarantined protocol events
```

### Concrete test targets

Unit tests:

```text
tests/unit/test_protocol_models.py
  WorkSignal accepts stable fields.
  WorkSignal drops unknown vocabulary without failing.
  SyncRequest accepts optional work_signal.
  CommitRequest accepts cwd/workroot_id locators and does not eagerly validate every event.

tests/unit/test_protocol_controller.py
  sync returns advisory non-blocking fields.
  protocol errors return advisory non-blocking fields.
  no-location commit returns not_recorded and writes nothing.
  minimally identifiable malformed events are quarantined.
  unidentifiable malformed events are ignored and not persisted.

tests/unit/test_protocol_projections.py
  progress can complete a run without handoff.
  progress summary survives invalid item update.
  terminal item reopen remains rejected when it is the actual requested fact.

tests/unit/test_context_continuity.py
  stale_active_run is derived at runtime.
  old_incomplete_run is derived at runtime.
```

Integration tests:

```text
tests/integration/test_agent_protocol_loop.py
  next sync can continue after handoff.
  next sync warns when completed run has no handoff.
  missing work_signal does not break the loop.

tests/integration/test_context_budget_trace.py
  rendered context includes isolated Control Context.
  compact debug/fallback context keeps control/task section separation where possible.
  quarantined protocol event payload does not render in ordinary context.

tests/unit/test_import_boundaries.py
  new modules preserve the declared dependency graph.
```

E2E tests:

```text
tests/e2e/longrun_cases.py
  user directories do not receive Workroot process fixtures.
```

## Proposed Next Review Method

Before implementation, validate this design against these scenario classes:

```text
quick answer
new tracked task
continue task
missing work_signal
model forgot protocol
adapter swallowed capsule
expired lease
partial progress
missing handoff
stale active run
task switching
step decomposition
high-risk publish
```

If all scenarios close without blocking the Agent and without corrupting durable facts, this draft can become the final implementation design.
