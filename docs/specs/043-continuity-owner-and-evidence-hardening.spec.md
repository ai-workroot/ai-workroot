# Spec 043 - Continuity Owner And Evidence Hardening

Status: accepted for the 0.9.531 hardening line
Depends on: `042-agent-protocol-context-strategy.spec.md`

## Purpose

Define the hardening design for the task continuity and context recall issues
found by the 20-round live novice Chinese E2E run on 2026-06-08.

The run proved that the protocol loop, temporary inbox creation, commit
idempotency, runtime views, and user asset placement are mostly working. It
also exposed two delivery-blocking gaps:

1. A final continuation/handoff can be attached to a recent temporary inbox
   even when the user-visible content belongs to the main task.
2. Evidence-oriented questions can remain shallow when the first
   `workroot agent sync` call does not carry stable evidence semantics.

This spec keeps the existing domain model. It must not add new Task,
TaskRun, Handoff, Asset, Decision, Relationship, or disclosure-layer entities.

## Goals

- Prevent durable writes from binding to the wrong task owner.
- Preserve non-blocking Agent behavior when task focus is ambiguous.
- Make evidence recall reliable through stable protocol semantics rather than
  user-language keyword matching.
- Improve local indexed-chunk recall without introducing embeddings or remote
  services.
- Add validation that catches current-owner drift and missing evidence recall
  in realistic E2E runs.

## Non-Goals

- No new Agent Protocol action beyond `sync` and `commit`.
- No Workroot-side LLM classification.
- No multilingual keyword dictionaries as protocol control logic.
- No new durable storage tables for L1/L2/L3 disclosure.
- No broad raw-history recall followed by trimming.
- No blocking user-visible work when Workroot cannot safely persist facts.

## Current Failure Model

### Owner Drift

The failed live behavior:

1. A long-running normal task exists.
2. A temporary inbox task is created for a side thought.
3. The user later returns to normal work and finally says a natural stop
   request such as "next time remind me which results to check".
4. `workroot agent sync` returns multiple candidate task refs. The recent inbox
   can appear first because it has the latest handoff.
5. The Agent passes candidate refs back without clearly selecting one owner.
6. Unsafe focus resolution accepts a candidate ref as the owner and issues a
   lease for the inbox.
7. A continuation commit stores the main-task handoff under the inbox.
8. Runtime views then report the inbox as current, which damages the next
   session's handoff.

The bug is not that temporary inbox exists. The bug is accepting an unsafe
owner when the protocol only supplied a candidate list.

### Evidence Miss

The failed live behavior:

1. The user asks why a prior recommendation was made and asks for existing
   information behind it.
2. The first `workroot agent sync` call carries `work_kind=continuation` and a
   natural-language focus, but it does not carry `concerns=["needs_evidence"]`
   or an evidence action alias.
3. The compact sync context remains shallow.
4. A later retry may include `intended_action=inspect`, but it is too late to
   affect the already-rendered context for that turn.

The bug is not that the context strategy ignores evidence semantics. The
strategy handles them. The bug is that the first sync call is not reliably
guided to send the stable evidence signal.

## Design Principles

1. Explicit owner beats inferred owner.
   `known_state` and a single selected ref can bind durable writes. A candidate
   list alone must not.

2. Ambiguity is safe and non-blocking.
   Workroot may return no lease and ask for a clearer sync. The Agent should
   still answer the user from available context.

3. Multiple refs are recall scope, not owner binding.
   Passing multiple refs can help context retrieval. It must not silently pick
   one durable owner unless all valid refs resolve to the same task/run.

4. Evidence intent is protocol-semantic.
   Workroot does not inspect Chinese, English, Japanese, or other user-language
   phrases to decide whether to do deep recall. The Agent/LLM normalizes user
   intent into WorkSignal.

5. Query is content, not control plane.
   `--query` can rank or search within already-allowed sources. It must not
   decide task ownership, work creation, or disclosure depth by language
   keywords.

6. Deep recall follows a drill-down chain.
   Map and summary refs identify promising sources first. Deep evidence
   fetches scoped indexed chunks only after explicit refs are present. Task
   focus may rank summaries, but it must not open broad raw evidence by
   itself.

## Architecture Overview

```text
Agent/LLM
  -> workroot agent sync --query + optional WorkSignal + optional selected ref
      -> focus boundary
      -> owner resolution
      -> compact context
      -> lease only when durable owner is reliable
      -> RecallPlan
      -> plan-constrained retrieval
  -> workroot agent commit --lease + shape payload
      -> lease guard
      -> projection
      -> runtime views
```

Owner resolution and RecallPlan are separate. Context Builder executes a
RecallPlan; it does not decide the durable owner for commits.

## Owner Resolution Contract

### Binding Inputs

The following inputs may bind a durable owner:

- `known_state.task_id` with an accepted task.
- `known_state.run_id` with an accepted run.
- exactly one valid `WorkSignal.refs` item that resolves to one task/run.
- multiple valid refs only when every ref resolves to the same task/run.
- a high-confidence local focus match with a clear score gap.

The following inputs must not bind a durable owner:

- a packet-provided candidate list passed back unchanged;
- multiple refs that resolve to different tasks;
- latest handoff recency alone when another active task is close;
- temporary inbox recency when `work_kind` is not `inbox`;
- a handoff continuation that is still ambiguous after candidate scoring.

### Multiple Ref Semantics

`WorkSignal.refs` may contain multiple refs. They mean "these are relevant
retrieval scopes" unless they resolve to exactly one owner.

Resolution rules:

```text
0 valid owner refs
  -> continue normal focus scoring

1 valid owner ref
  -> bind to that owner

2+ valid refs, all same task/run
  -> bind to that shared owner

2+ valid refs, different owners
  -> ambiguous; no lease; return candidate refs
```

This rule prevents the first item in a candidate list from becoming a durable
owner by accident.

### Handoff Continuation Rule

Continuation/handoff commits are high-impact because they drive the next
session's runtime current view.

If continuation focus is ambiguous, handoff resolution must not pick the first
candidate. It must return the ambiguous resolution and withhold a lease.

The Agent can still answer the user. To preserve the handoff durably, it must
sync again with a single selected task/run ref or known state.

### Normal Task Bias

Temporary inbox is for side work. A non-inbox WorkSignal must not prefer inbox
just because the inbox has the latest handoff.

When focus is otherwise close:

- `work_kind=inbox` may prefer inbox candidates.
- `work_kind=task`, `work_kind=continuation`, `work_kind=decision`, or an empty
  work kind must not prefer inbox unless the query/focus clearly names the
  inbox or an explicit inbox ref is selected.

This is a bias, not a language parser. It uses task role and protocol fields,
not user-language keywords.

## Packet Guidance Contract

Private packet refs have two different roles:

- `refs.candidates`: choices the Agent may inspect and choose from.
- `refs.task` / `refs.run`: the selected durable owner, if already known.

Inbox refs are not enough to bind the durable owner by themselves. A ref that
points at an inbox task may become the owner only when WorkSignal explicitly
uses `work_kind="inbox"`. Otherwise, mixed normal/inbox refs are treated as
recall scope and the active normal task remains the default continuity owner.

When a continuation sync would otherwise be ambiguous only because normal and
inbox candidates are close, and there is exactly one active normal root task,
Workroot should issue the continuation lease for that normal task unless
WorkSignal explicitly asks for inbox work.

When focus is ambiguous and only candidate refs exist, the generated next sync
command must not include all candidate refs as if they were a selected owner.

Bad:

```bash
workroot agent sync ... --work-signal '{"refs":["task:a","task:b","task:c"]}'
```

Good:

```bash
workroot agent sync ... --work-signal '{"focus":"current user request summary","refs":["task:<one selected ref>"]}'
```

If no candidate is clearly relevant, omit `refs` and continue without durable
persistence.

Packet text must keep this private and concise. It must not expose internal
disclosure labels such as L1/L2/L3 in LLM-visible context packages or ordinary
user-facing output. Those labels are strategy internals and belong only in
machine-readable traces or developer documentation.

## Evidence Recall Contract

### Agent Entry Requirement

Agent Entry must teach the LLM that before calling `workroot agent sync`, it
should pass a WorkSignal when it can infer stable semantics.

For evidence-oriented user intent, the stable signal is:

```json
{
  "intended_action": "inspect",
  "concerns": ["needs_evidence"]
}
```

Equivalent shorthand values such as `explain`, `rationale`, `evidence`,
`source`, `proof`, or `justify` may be passed as `intended_action`. Workroot
normalizes them to `inspect` plus `needs_evidence`.

These are protocol enum aliases, not user-language keyword rules.

### First-Hop Requirement

The first `workroot agent sync` call for a meaningful turn is the
context-building point. Evidence semantics must arrive there. A later retry
cannot repair context that was already rendered shallow for the current turn.

Therefore:

- native Agent templates must include a compact instruction for evidence
  WorkSignal;
- `workroot agent sync` examples should show evidence WorkSignal when relevant;
- E2E prompts must validate that real LLMs pass evidence semantics on the
  first sync call.

### Context Strategy Requirement

The context strategy keeps the existing rule:

```text
needs_evidence + explicit ref -> allow scoped evidence chunks
needs_evidence without explicit ref -> return summaries and refs only
ambiguous or conflicting focus -> return summaries and refs only
```

Explicit refs may be:

- a source ref such as `asset:...` or `decision:...`;
- a selected candidate ref that resolves to a safe source;
- multiple refs that remain safe after release filtering.

Current task/run focus is still useful for ranking and continuity, but it is
not enough to fetch raw or near-raw evidence chunks. If refs are missing,
Workroot should provide candidate refs and summaries rather than loading raw
evidence broadly.

## Indexed Evidence Retrieval

FTS must remain local, bounded, and non-blocking.

### Query Compiler

`search_fts` should not pass arbitrary user text directly as a SQLite FTS
MATCH expression.

It should compile a safe query:

1. extract bounded alphanumeric terms;
2. preserve quoted or short phrase fallback only when SQLite accepts it;
3. for CJK or low-token queries, use a bounded fallback scan rather than a
   brittle MATCH expression;
4. return no matches and an error reason rather than raising.

The compiler is retrieval infrastructure, not protocol intent detection. It
does not decide whether evidence recall is allowed.

### Drill-Down Retrieval

When scoped evidence is allowed, retrieval should prefer this order:

```text
explicit refs -> chunks by refs
selected candidate source refs -> chunks by refs
optional bounded knowledge lookup -> indexed chunk matches
```

The selected candidate source refs step is important. It makes the chain:

```text
candidate ref -> source asset/decision -> indexed chunk
```

clear and stable without requiring natural-language query matching to be
perfect.

### Rendering

Evidence rendering stays concise:

```text
- <relative path>: <reason>; Ref: chunk:<chunk_id>
```

It should not dump large raw file contents. The chunk body may contribute to
token-budget calculations and debug traces, but final rendering must remain
bounded.

## Runtime Views

Runtime views remain rebuildable projections. SQLite remains the canonical
fact store.

`state/current.json`, `tasks/current.json`, and `handoffs/current.json` should
only move to a task when that task received a valid committed event with a
safe owner.

After this hardening:

- a wrong-owner handoff should not be committed;
- an ambiguous handoff should leave the prior current owner intact;
- diagnostics should expose rejected/ambiguous protocol friction without
  interrupting user work.

No new runtime directories are required.

## Test Plan

### Unit Tests

Add owner-resolution tests:

- multiple refs resolving to different tasks returns ambiguous focus and no
  lease;
- multiple refs resolving to the same task binds that task;
- handoff continuation with ambiguous focus does not choose the first
  candidate;
- non-inbox continuation does not bind to recent inbox by recency alone;
- explicit single inbox ref still resumes inbox correctly;
- explicit single normal-task ref resumes normal task correctly.

Add packet tests:

- ambiguous packet exposes candidate refs but generated command does not pass
  all candidate refs as selected refs;
- selected owner packet keeps `known_state` or a single selected ref.

Add context strategy tests:

- evidence alias in WorkSignal requests evidence semantics;
- missing evidence signal remains shallow and non-blocking;
- explicit refs can fetch scoped evidence chunks through selected candidate
  source refs;
- unscoped evidence does not fetch broad chunks.

Add FTS tests:

- natural-language queries with punctuation do not raise;
- CJK user queries do not raise;
- ref-scoped chunk retrieval works without FTS MATCH;
- fallback scan is bounded and respects safety/release filters.

### Integration Tests

Add a regression flow:

1. create normal task;
2. create temporary inbox;
3. return to normal task;
4. issue final stop/handoff without explicit known state;
5. verify Workroot withholds durable handoff if owner is ambiguous, or binds
   to normal task only when a single selected normal ref is supplied;
6. verify runtime current views do not drift to the inbox.

### Live E2E Gates

The live novice Chinese role must validate:

- final current/handoff owner contains the expected main-task title;
- temporary inbox tasks remain separate;
- no rejected commit batches;
- evidence round sync/recall diagnostics show evidence-oriented intent and
  either summaries-with-refs or scoped evidence;
- context token usage remains under the hard limit;
- user directory contains only expected user-visible assets and starter guide.

The E2E harness should fail when current owner is wrong, even if all protocol
events are applied.

## Acceptance Criteria

This hardening is accepted when:

- all unit and integration tests pass;
- release validation passes in a dev environment with `ruff`;
- a 20-round live novice Chinese E2E passes with correct final owner;
- evidence without refs returns summaries and refs without broad chunks;
- evidence with explicit refs reaches scoped evidence retrieval;
- no runtime pollution appears in user directories;
- protocol events and commit batches have no rejected or quarantined records
  introduced by the run;
- context package size stays within configured hard token limits.

## Open Design Decisions

### Cross-Task Final Handoff

Some future user turns may intentionally ask for a cross-task handoff. The
current model has task-scoped handoffs. For this hardening, Workroot should not
invent a workroot-level handoff entity. If the owner is ambiguous, return
candidate refs and continue without durable handoff persistence.

If cross-task handoffs become a product requirement later, they should be
designed explicitly as a separate capability.

### Evidence Without WorkSignal

This spec does not add user-language keyword detection inside Workroot. If the
Agent/LLM fails to send evidence semantics, Workroot remains shallow and
non-blocking. The fix is stronger Agent Entry guidance and E2E validation that
real Agents follow it.

Adding Workroot-side language classifiers would be a separate design decision.

## Implementation Notes

Likely files:

- `src/ai_workroot/protocol/focus.py`
- `src/ai_workroot/protocol/packet.py`
- `src/ai_workroot/capabilities/context/builder.py`
- `src/ai_workroot/capabilities/retrieval/providers/sqlite_fts.py`
- `src/ai_workroot/entrypoints/native_agent/templates/AGENTS.md.template`
- `src/ai_workroot/entrypoints/native_agent/templates/CLAUDE.md.template`
- `tests/unit/test_protocol_sync_focus_v2.py`
- `tests/unit/test_protocol_packet.py`
- `tests/unit/test_context_wrapper_v2.py`
- `tests/integration/test_runtime_views.py`
- `tests/e2e/live_task_continuity.py`
- `tests/e2e/live_task_continuity_cases.py`

Implementation must be TDD-first because the live E2E failure is a regression
that current automated tests did not catch.
