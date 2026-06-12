# Spec 048 - Model-First Protocol Teaching And Owner Recovery

Status: planned for the 0.9.531 hotfix line
Depends on:

- `042-agent-protocol-context-strategy.spec.md`
- `045-sync-owner-binding-and-lease-guard.spec.md`
- `046-protocol-context-hardening-followup.spec.md`
- `047-compact-packet-focus-guard-sync-trace.spec.md`

## Purpose

This spec closes the failures found by the 20-round live mixed-complexity E2E
run after Spec 047.

The stable Agent loop remains:

```text
sync -> commit
```

`context` remains read-only auxiliary behavior for startup, recovery, manual
inspection, and debugging. It must not return to the ordinary per-turn loop.

This spec does not introduce new domain entities. It hardens the protocol
teaching surface, sync packet reminders, ambiguous owner recovery, asset owner
binding, server-side focus guards, and E2E assertions.

## Failure Evidence

The live run failed with product-level continuity problems:

- Active normal root tasks reached 4, above the scenario threshold.
- Unexpected start-work appeared in rounds 03, 10, 15, 16, and 20.
- Quick-answer rounds created durable inbox tasks.
- Handoff and checkpoint rounds were misread as separate work.
- One expected asset existed in the user directory but had no task owner.
- Ambiguous recovery did not converge. The model tried `--format json`,
  `--help`, and `workroot context --debug` before continuing.
- Packet size was acceptable after Spec 047, so the primary issue is not token
  budget. The issue is protocol semantics and owner binding.

Representative bad WorkSignals:

```json
{"phase":"starting","work_kind":"task","intended_action":"plan","boundary":"separate_work","focus":"why should durable task summaries stay concise?"}
```

```json
{"phase":"switching","work_kind":"inbox","intended_action":"plan","boundary":"separate_work","focus":"Preserve a handoff..."}
```

```json
{"phase":"starting","work_kind":"task","intended_action":"plan","boundary":"separate_work","focus":"Founder operating handoff"}
```

## Design Principles

1. Model-facing protocol teaching is the first line of quality.
2. WorkSignal is stable structured semantics. User language is content.
3. Workroot fallback is a guardrail, not the primary intent engine.
4. `boundary=separate_work` is valid only for a separate long-running work
   item, not for a quick answer, handoff, checkpoint, current-task decision, or
   current-task asset.
5. Workroot must never create a new durable task only because the model sent a
   bad boundary hint.
6. Ambiguity is non-blocking. The Agent continues helping the user while
   Workroot withholds durable task writes.
7. Ambiguous recovery must be executable. The packet should provide candidate
   refs and a copyable resync template.
8. Assets that clearly belong to current work should be owner-bound. Ownerless
   Workroot-scoped asset capture is allowed only when owner uncertainty is real
   or explicitly signaled.
9. Normal packets remain compact Markdown. Internal classifications, leases,
   refs, and JSON are private and must not appear in user-visible output.
10. The protocol contract is transport-neutral. CLI examples are one renderer;
    MCP and other adapters must use the same semantic packet data.

## Model-First WorkSignal Teaching

Native Agent Entry must include a small routing table. The table is private
model guidance, not user-facing product text.

Required routing rows:

```text
User wants a direct explanation or quick answer:
  work_kind=quick, intended_action=answer.
  Do not use boundary=separate_work. Do not commit unless the packet asks.

User continues the same work, asks for a checkpoint, or asks for a handoff:
  work_kind=continuation.
  Use intended_action=preserve for checkpoint or handoff.
  Use intended_action=summarize only when summarizing.
  Prefer known_state or refs when available. Do not use boundary=separate_work.

User makes a stable choice inside current work:
  work_kind=decision, intended_action=decide.
  Do not use boundary=separate_work unless the user clearly starts a separate
  long-running decision-review work item.

User asks for a user-visible file for current work:
  work_kind=authoring, intended_action=preserve.
  Create the file first, then commit asset if the packet asks.
  Do not use boundary=separate_work unless the file starts a separate
  long-running work item.

User starts a clearly separate long-running work item:
  phase=starting, work_kind=task, intended_action=plan,
  boundary=separate_work.

User raises a loose side thought that may be useful later:
  phase=switching, work_kind=inbox, intended_action=plan.
  Use temporary persistence only if the packet asks for start-work.
```

The wording must avoid internal owner terms such as `owner_kind`,
`FocusBinding`, root task internals, database details, or disclosure-layer
names.

## Sync Packet Reminder Contract

Default `--format packet` output remains compact. It must not repeat the full
Agent Entry routing table on every turn.

`accepted_shapes` is the set of commit shapes allowed by the current lease; it
is not necessarily the shape the Agent should call first. When the focus
resolver has a clear primary fact for this turn, `commit_contract.preferred_shape`
selects the packet call template. For example, a current-work decision can allow
`continuation` before stop but still prefer `decision` first, with
`continuation_before_stop` rendered as a follow-up requirement.

It should add only shape-specific reminders:

- For `start_work`: remind that start-work is only for a separate long-running
  work item or temporary side thread.
- For quick/no-call: remind that the Agent should answer directly and not
  commit.
- For continuation/handoff: remind to bind to current work and preserve current
  state plus next action before stopping or switching.
- For asset: remind to create or update the file first, then commit asset with
  the relative path.
- For decision: remind to capture only stable decision and reason.
- For ambiguous sync: show candidate refs and exact resync template.

The default packet should discourage normal-loop debug detours:

```text
Do not use --help, --format json, or workroot context in the normal loop unless
debugging or recovering from a tool error.
```

This line is private protocol guidance and must stay out of user-visible final
answers.

## Ambiguous Owner Recovery Contract

When sync returns an ambiguous focus, the packet must include up to three
candidate refs:

```text
Candidates:
- task:task-founder - founder operating cadence
  Use when: this turn continues the founder operating work.
- task:task-engineering - protocol continuity hardening
  Use when: this turn continues implementation or test hardening.
```

The packet must also include a copyable resync template:

```text
workroot agent sync --agent <agent> --transport <transport> --cwd . --reason continue --format packet --query "<current user request or short intent>" --work-signal '{"focus":"<same user-language focus>","intended_action":"inspect","phase":"orienting","refs":["task:<chosen-task-id>"],"work_kind":"continuation"}'
```

Rules:

- The template may include a placeholder for the chosen ref, but it must not
  silently choose a candidate when Workroot is not confident.
- Candidate refs are private protocol refs. They are not shown to the user.
- The Agent may keep helping the user without persistence if it cannot choose a
  ref.

## Server-Side Focus Guard Contract

Workroot treats WorkSignal as a hint. It must repair or withhold persistence
when the hint conflicts with safer continuity evidence.

Guard rules:

- `work_kind=quick` or `intended_action=answer` wins over durable query words
  unless refs or known state explicitly request persistence.
- A quick-like request with `boundary=separate_work` must not receive a
  start-work lease.
- Handoff, checkpoint, preservation, and continuation signals must prefer the
  current owner when reliable.
- Current-task asset and decision signals must prefer current or ref-bound
  owner when reliable.
- `work_kind=inbox` creates temporary work only when it is a loose side thread,
  not a handoff/checkpoint for current work.
- `boundary=separate_work` may create a new durable task only when the signal
  is explicitly startable and no current-work fact shape is detected.
- If multiple owners remain plausible, sync returns ambiguous non-blocking
  recovery instead of issuing a write lease.

The fallback should avoid language-specific command dictionaries. It may use
language-neutral protocol fields, refs, known state, path presence, current
owner count, and generic shape evidence. Text similarity remains only a weak
owner ranking aid.

## Asset Owner Binding Contract

Asset commits must not silently lose owner binding when the preceding sync has
a reliable owner.

Required behavior:

- If sync returns task/run refs and an asset lease, the asset commit is bound to
  that task/run through the lease.
- If the asset request includes an existing asset/candidate/chunk ref, Workroot
  resolves the related task owner before issuing an asset lease.
- If the request has an explicit path and exactly one active normal task is a
  safe current owner, Workroot issues a task-bound asset lease.
- If the request has an explicit path and several owners are plausible, Workroot
  returns either candidate resync or Workroot-scoped asset capture only when the
  signal explicitly admits uncertain boundary.
- The packet must make the outcome clear: task-bound asset, Workroot-scoped
  asset, or resync required.

## E2E Contract

The live harness must verify protocol learning, not only backend resilience.

Required assertions:

- A quick-answer round must not create task, task run, progress, handoff, asset,
  or decision facts unless the scenario explicitly expects capture.
- A handoff/checkpoint/current-task decision/current-task asset round must not
  create unexpected start-work.
- Expected assets must exist and must be owner-bound when the scenario declares
  an expected owner substring.
- Ambiguous recovery must not lead to normal-loop `--help`, `--format json`, or
  `workroot context` unless the round is marked as recovery/debug.
- Start-work is allowed only in rounds that explicitly expect it.
- Active normal root task count must stay within the scenario threshold.
- User-visible final output must not leak Workroot packets, refs, leases, JSON,
  internal owner terms, or disclosure-layer names.

## Implementation Plan

1. Update Native Agent Entry templates and tests with the routing table.
2. Add packet tests for quick/no-call reminders, start-work negative
   reminders, ambiguous candidate rendering, resync templates with refs, and
   no normal-loop debug detours.
3. Add focus tests for false `separate_work` on quick, handoff, checkpoint,
   decision, and asset requests.
4. Add focus tests for legitimate separate work to ensure the guard does not
   over-collapse real new tasks.
5. Add asset-owner tests for task-bound asset leases and explicit uncertain
   Workroot-scoped asset capture.
6. Implement the smallest code changes in packet rendering and focus
   resolution to satisfy tests.
7. Harden the live E2E prompt and assertions so the model receives the same
   protocol teaching as Agent Entry and failures are caught per round.
8. Run focused tests, then the broader local suite and release validation.
9. Run the live 20-round mixed-complexity E2E and preserve all artifacts for
   analysis.

## Acceptance Criteria

- Native Agent Entry teaches both positive and negative WorkSignal routing.
- The default packet stays compact and does not expose internal owner or
  disclosure terms.
- Ambiguous packets provide candidate refs plus a concrete resync template.
- The model has less reason to call `--help`, `--format json`, or
  `workroot context` during the normal loop.
- False separate-work signals do not create new tasks for quick answers,
  handoffs, checkpoints, current decisions, or current assets.
- Legitimate separate long-running work can still start a new durable task.
- Expected user-visible assets are owner-bound when the scenario implies a
  current task owner.
- Local tests and the live 20-round E2E verify the behavior.
